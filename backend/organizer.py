import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from backend.database import log_operation, mark_operation_undone, get_operation_by_id, update_suggestion_status
from backend.models import ActionItem, ExecutedActionResult, UndoResponse

def is_safe_contained_path(target_path: Path, root_path: Path) -> bool:
    """
    Checks that target_path resolves strictly to a location inside root_path.
    Prevents path traversal, '../' escapes, and symlink redirection.
    """
    try:
        resolved_root = root_path.resolve()
        resolved_target = target_path.resolve()
        # Must be equal or child of root
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
    """
    op_id = f"op_{uuid.uuid4().hex[:12]}"
    src_path = Path(action.original_path).resolve()
    resolved_root = root_dir.resolve()

    # Security check 1: Source must be under root
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

    # Security check 2: Source must exist and be a regular file
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

    if src_path.is_symlink() or not src_path.is_file():
        err = f"Source file is a symlink or directory; operations on symlinks are blocked for safety."
        log_operation(op_id, action.id, str(src_path), "", 0, status="failed", error_message=err)
        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(src_path),
            destination_path="",
            success=False,
            error=err
        )

    # Determine destination
    rel_path_str = action.proposed_rel_path.strip("/\\")
    # Clean out any sneaky path traversal in relative path
    clean_parts = [p for p in Path(rel_path_str).parts if p not in ("..", ".", "/")]
    if not clean_parts:
        clean_parts = [action.proposed_filename]

    dest_path = (resolved_root / Path(*clean_parts)).resolve()

    # Security check 3: Destination must be under root
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

        file_size = src_path.stat().st_size

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
        if not action.approved:
            continue
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
    """
    op = get_operation_by_id(operation_id)
    if not op:
        return UndoResponse(operation_id=operation_id, success=False, message="Operation record not found.")

    if op["status"] == "undone":
        return UndoResponse(operation_id=operation_id, success=False, message="Operation has already been undone.")

    if op["status"] != "executed":
        return UndoResponse(operation_id=operation_id, success=False, message=f"Cannot undo operation with status '{op['status']}'.")

    current_path = Path(op["destination_path"]).resolve()
    orig_path = Path(op["original_path"]).resolve()

    # Verification: Current path must exist
    if not current_path.exists():
        return UndoResponse(
            operation_id=operation_id, 
            success=False, 
            message=f"Current file no longer exists at '{current_path}'. Cannot safely undo."
        )

    # Verification: Target original path must not conflict with an existing file
    if orig_path.exists():
        # Avoid overwriting whatever is at original path
        orig_path = get_unique_destination_path(orig_path, orig_path.parent)

    try:
        orig_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(current_path), str(orig_path))

        # Confirm on filesystem
        if not orig_path.exists() or current_path.exists():
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
            restored_path=str(orig_path),
            message=f"Successfully restored file to '{orig_path.name}'"
        )
    except Exception as e:
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=f"Undo failed: {str(e)}"
        )
