import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from backend.database import (
    log_operation, mark_operation_undone, get_operation_by_id,
    update_suggestion_status, get_suggestion_by_id, get_scan_session
)
from backend.models import ActionItem, ExecutedActionResult, UndoResponse

def is_safe_contained_path(target_path: Path, root_path: Path) -> bool:
    """
    Checks that target_path resolves strictly to a location inside root_path.
    Prevents path traversal, '../' escapes, and symlink redirection.
    """
    try:
        if target_path.is_symlink():
            return False
        resolved_root = root_path.resolve()
        resolved_target = target_path.resolve()
        return resolved_target == resolved_root or resolved_root in resolved_target.parents
    except Exception:
        return False

def get_unique_destination_path(desired_path: Path, root_path: Path) -> Path:
    """
    If desired_path already exists, adds a numbered suffix (_1, _2) before extension
    to strictly prevent overwriting existing files.
    """
    if not desired_path.exists():
        return desired_path

    parent = desired_path.parent
    stem = desired_path.stem
    suffix = desired_path.suffix
    counter = 1

    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
        if counter > 999:
            raise RuntimeError("Exceeded maximum duplicate filename conflict resolution attempts.")

def execute_single_action(action: ActionItem, root_dir: Path) -> ExecutedActionResult:
    """
    Validates and executes a single file move/rename safely.
    Enforces server-side suggestion validation, explicit server approval,
    root binding, pre-resolution symlink checks, file integrity, and non-destructive moves.
    """
    op_id = f"op_{uuid.uuid4().hex[:12]}"
    resolved_root = root_dir.resolve()

    # Security check 1: Suggestion must exist in persisted database (prevents forged action IDs)
    sug = get_suggestion_by_id(action.id)
    if not sug:
        err = f"Security violation: Action ID '{action.id}' does not correspond to a valid persisted suggestion."
        log_operation(op_id, action.id, action.original_path, "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=action.original_path,
            destination_path="",
            success=False,
            error=err
        )

    # Security check 2: Require explicit server-side approval before execution
    if not action.approved:
        err = f"Action '{action.id}' was marked unapproved in request."
        log_operation(op_id, action.id, sug["original_path"], "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=sug["original_path"],
            destination_path="",
            success=False,
            error=err
        )

    if sug["status"] != "approved":
        if sug["status"] == "pending":
            err = f"Action '{action.id}' has not been approved for execution (server status: pending). Server-side approval is required."
        elif sug["status"] == "executed":
            err = f"Action '{action.id}' has already been executed."
        elif sug["status"] == "rejected":
            err = f"Action '{action.id}' was rejected."
        else:
            err = f"Action '{action.id}' has invalid status '{sug['status']}'."
        log_operation(op_id, action.id, sug["original_path"], "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=sug["original_path"],
            destination_path="",
            success=False,
            error=err
        )

    # Security check 3: Action must be bound to the scan root session
    session = get_scan_session(sug["session_id"])
    if not session:
        err = f"Security violation: Scan session '{sug['session_id']}' for suggestion '{action.id}' not found."
        log_operation(op_id, action.id, sug["original_path"], "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=sug["original_path"],
            destination_path="",
            success=False,
            error=err
        )

    session_root = Path(session["root_dir"]).resolve()
    if session_root != resolved_root:
        err = f"Security violation: Action bound to scan root '{session_root}' cannot be executed under root '{resolved_root}'."
        log_operation(op_id, action.id, sug["original_path"], "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=sug["original_path"],
            destination_path="",
            success=False,
            error=err
        )

    # Use the persisted original_path rather than trusting client-supplied paths
    raw_src_path = Path(sug["original_path"])

    # Security check 4: Check original source path and its components for symlinks BEFORE resolving
    if raw_src_path.is_symlink():
        err = f"Security violation: Source path '{raw_src_path}' is a symlink. Operations on symlinks are blocked for safety."
        log_operation(op_id, action.id, str(raw_src_path), "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(raw_src_path),
            destination_path="",
            success=False,
            error=err
        )

    curr_p = raw_src_path
    while curr_p != curr_p.parent and curr_p != resolved_root:
        if curr_p.is_symlink():
            err = f"Security violation: Parent path component '{curr_p}' is a symlink. Blocked for safety."
            log_operation(op_id, action.id, str(raw_src_path), "", 0, status="failed", error_message=err)
            return ExecutedActionResult(
                action_id=action.id,
                operation_id=op_id,
                original_path=str(raw_src_path),
                destination_path="",
                success=False,
                error=err
            )
        curr_p = curr_p.parent

    src_path = raw_src_path.resolve()

    # Security check 5: Source must be strictly under root
    if not is_safe_contained_path(src_path, resolved_root):
        err = f"Security violation: Source file '{src_path}' is outside approved root '{resolved_root}'"
        log_operation(op_id, action.id, str(src_path), "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(src_path),
            destination_path="",
            success=False,
            error=err
        )

    # Security check 6: Source file must exist and be a regular file
    if not src_path.exists():
        err = f"Source file does not exist: {src_path}"
        log_operation(op_id, action.id, str(src_path), "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(src_path),
            destination_path="",
            success=False,
            error=err
        )

    if not src_path.is_file():
        err = f"Source path is not a regular file: {src_path}"
        log_operation(op_id, action.id, str(src_path), "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(src_path),
            destination_path="",
            success=False,
            error=err
        )

    # Security check 7: Check if source file changed since suggestion was created
    stat = src_path.stat()
    if sug.get("source_size_bytes") and stat.st_size != sug["source_size_bytes"]:
        err = f"Source file '{src_path.name}' has changed since suggestion was generated (size mismatch: current {stat.st_size} vs recorded {sug['source_size_bytes']}). Operation rejected."
        log_operation(op_id, action.id, str(src_path), "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(src_path),
            destination_path="",
            success=False,
            error=err
        )

    if sug.get("source_mtime") and abs(stat.st_mtime - sug["source_mtime"]) > 1.0:
        err = f"Source file '{src_path.name}' has changed since suggestion was generated (mtime mismatch). Operation rejected."
        log_operation(op_id, action.id, str(src_path), "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(src_path),
            destination_path="",
            success=False,
            error=err
        )

    # Determine destination strictly using persisted suggestion
    rel_path_str = sug["proposed_rel_path"].strip("/\\")
    clean_parts = [p for p in Path(rel_path_str).parts if p not in ("..", ".", "/", "\\")]
    if not clean_parts:
        clean_parts = [sug["proposed_filename"]]

    raw_dest = resolved_root / Path(*clean_parts)

    # Check destination path for symlinks before resolving
    curr_dest = raw_dest
    while curr_dest != resolved_root and curr_dest != curr_dest.parent:
        if curr_dest.is_symlink():
            err = f"Security violation: Destination path component '{curr_dest}' is a symlink. Symlinks are blocked."
            log_operation(op_id, action.id, str(src_path), str(raw_dest), 0, status="failed", error_message=err)
            return ExecutedActionResult(
                action_id=action.id,
                operation_id=op_id,
                original_path=str(src_path),
                destination_path=str(raw_dest),
                success=False,
                error=err
            )
        curr_dest = curr_dest.parent

    dest_path = raw_dest.resolve()

    # Security check 8: Destination must be under root
    if not is_safe_contained_path(dest_path, resolved_root):
        err = f"Security violation: Target destination '{dest_path}' escapes approved root directory."
        log_operation(op_id, action.id, str(src_path), str(dest_path), 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(src_path),
            destination_path=str(dest_path),
            success=False,
            error=err
        )

    # Resolve conflicts safely without overwriting
    try:
        final_dest_path = get_unique_destination_path(dest_path, resolved_root)
        final_dest_path.parent.mkdir(parents=True, exist_ok=True)

        file_size = stat.st_size

        # Perform atomic move/rename
        shutil.move(str(src_path), str(final_dest_path))

        # Verify on filesystem
        if not final_dest_path.exists() or src_path.exists():
            raise IOError("Filesystem verification failed after move operation.")

        log_operation(op_id, action.id, str(src_path), str(final_dest_path), file_size, status="executed")
        update_suggestion_status(action.id, "executed")

        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(src_path),
            destination_path=str(final_dest_path),
            success=True,
            error=None
        )

    except Exception as e:
        err = f"Move operation failed: {str(e)}"
        log_operation(op_id, action.id, str(src_path), str(dest_path), 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(src_path),
            destination_path=str(dest_path),
            success=False,
            error=err
        )

def execute_batch_actions(actions: list[ActionItem], root_dir_str: str) -> tuple[int, int, list[ExecutedActionResult]]:
    """
    Executes an approved list of actions.
    """
    root_dir = Path(root_dir_str).resolve()
    results: list[ExecutedActionResult] = []
    succeeded = 0
    failed = 0

    for action in actions:
        res = execute_single_action(action, root_dir)
        results.append(res)
        if res.success:
            succeeded += 1
        else:
            failed += 1

    return succeeded, failed, results

def undo_operation(operation_id: str) -> UndoResponse:
    """
    Reverses an executed file move safely after verifying filesystem integrity.
    Validates regular file status, symlink avoidance, file size match, and conflict prevention.
    """
    op = get_operation_by_id(operation_id)
    if not op:
        return UndoResponse(operation_id=operation_id, success=False, message="Operation record not found.")

    if op["status"] == "undone":
        return UndoResponse(operation_id=operation_id, success=False, message="Operation has already been undone.")

    if op["status"] != "executed":
        return UndoResponse(operation_id=operation_id, success=False, message=f"Cannot undo operation with status '{op['status']}'.")

    current_path = Path(op["destination_path"])
    orig_path = Path(op["original_path"])

    # Check symlinks before resolving
    if current_path.is_symlink():
        return UndoResponse(operation_id=operation_id, success=False, message="Destination path is a symlink. Undo blocked for safety.")
    if orig_path.is_symlink():
        return UndoResponse(operation_id=operation_id, success=False, message="Target restore path is a symlink. Undo blocked for safety.")

    resolved_current = current_path.resolve()
    resolved_orig = orig_path.resolve()

    # Verification: Current path must exist and be a regular file
    if not resolved_current.exists():
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=f"Current file no longer exists at '{resolved_current}'. Cannot safely undo."
        )

    if not resolved_current.is_file():
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=f"Current path is not a regular file at '{resolved_current}'. Cannot safely undo."
        )

    # Verification: Current file size must match original logged file size
    if resolved_current.stat().st_size != op["file_size"]:
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=f"File at '{resolved_current}' has been modified since execution (size mismatch). Cannot safely undo."
        )

    # Verification: Target original path must not conflict with an existing file
    target_restore_path = resolved_orig
    if target_restore_path.exists():
        # Avoid overwriting whatever is at original path
        target_restore_path = get_unique_destination_path(target_restore_path, target_restore_path.parent)

    try:
        target_restore_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(resolved_current), str(target_restore_path))

        # Confirm on filesystem
        if not target_restore_path.exists() or resolved_current.exists():
            return UndoResponse(
                operation_id=operation_id,
                success=False,
                message="Filesystem verification failed after reversal attempt."
            )

        mark_operation_undone(operation_id)
        if op.get("suggestion_id"):
            update_suggestion_status(op["suggestion_id"], "pending")

        return UndoResponse(
            operation_id=operation_id,
            success=True,
            restored_path=str(target_restore_path),
            message=f"Successfully restored file to '{target_restore_path.name}'"
        )
    except Exception as e:
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=f"Undo failed: {str(e)}"
        )
