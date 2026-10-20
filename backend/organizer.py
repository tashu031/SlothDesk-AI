
import shutil
import uuid
from pathlib import Path

from backend.config import settings
from backend.database import (
    log_operation,
    mark_operation_undone,
    get_operation_by_id,
    update_suggestion_status,
    get_suggestion_by_id,
    get_scan_session,
)
from backend.models import ActionItem, ExecutedActionResult, UndoResponse


def is_safe_contained_path(target_path: Path, root_path: Path) -> bool:
    """Check that target_path is strictly inside root_path, rejecting symlinks."""
    try:
        if target_path.is_symlink():
            return False

        resolved_root = root_path.resolve()
        resolved_target = target_path.resolve()

        return (
            resolved_target != resolved_root
            and resolved_root in resolved_target.parents
        )
    except (OSError, RuntimeError, ValueError):
        return False


def get_unique_destination_path(
    desired_path: Path,
    root_path: Path,
) -> Path:
    """Return a unique destination without overwriting existing files."""
    resolved_root = root_path.resolve()
    parent = desired_path.parent.resolve()

    if not (
        parent == resolved_root
        or resolved_root in parent.parents
    ):
        raise ValueError(
            "Destination directory is outside the approved root."
        )

    if not desired_path.exists() and not desired_path.is_symlink():
        return desired_path

    stem = desired_path.stem
    suffix = desired_path.suffix

    for counter in range(1, 1000):
        candidate = desired_path.parent / f"{stem}_{counter}{suffix}"

        if not candidate.exists() and not candidate.is_symlink():
            return candidate

    raise RuntimeError(
        "Exceeded maximum duplicate filename conflict resolution attempts."
    )


def _demo_root() -> Path:
    """Return the canonical sample playground path."""
    return Path(settings.sample_dir).resolve()


def _demo_path_allowed(path: Path) -> bool:
    """Check whether a path is strictly inside the sample playground."""
    if not settings.demo_mode:
        return True

    return is_safe_contained_path(path, _demo_root())


def _failed_action(
    op_id: str,
    action_id: str,
    original_path: str,
    error: str,
) -> ExecutedActionResult:
    """Log a failed action and return its result."""
    log_operation(
        op_id,
        action_id,
        original_path,
        "",
        0,
        status="failed",
        error_message=error,
    )

    return ExecutedActionResult(
        action_id=action_id,
        operation_id=op_id,
        original_path=original_path,
        destination_path="",
        success=False,
        error=error,
    )


def execute_single_action(
    action: ActionItem,
    root_dir: Path,
) -> ExecutedActionResult:
    """Safely execute one approved file move or rename."""
    op_id = f"op_{uuid.uuid4().hex[:12]}"
    resolved_root = root_dir.resolve()

    # Demo mode must never operate outside the sample playground.
    if settings.demo_mode and resolved_root != _demo_root():
        return _failed_action(
            op_id,
            action.id,
            action.original_path,
            "Demo mode allows file operations only inside the sample playground.",
        )

    # 1. The action must refer to a persisted suggestion.
    suggestion = get_suggestion_by_id(action.id)

    if not suggestion:
        return _failed_action(
            op_id,
            action.id,
            action.original_path,
            (
                f"Security violation: Action ID '{action.id}' "
                "does not correspond to a valid persisted suggestion."
            ),
        )

    original_path = suggestion["original_path"]

    # 2. Require approval in the request and in the database.
    if not action.approved:
        return _failed_action(
            op_id,
            action.id,
            original_path,
            (
                f"Action '{action.id}' was marked unapproved in the request. "
                "Server-side approval is required."
            ),
        )

    if suggestion["status"] != "approved":
        status = suggestion["status"]

        if status == "pending":
            error = (
                f"Action '{action.id}' has not been approved for execution. "
                "Server-side approval is required."
            )
        elif status == "executed":
            error = f"Action '{action.id}' has already been executed."
        elif status == "rejected":
            error = f"Action '{action.id}' was rejected."
        else:
            error = f"Action '{action.id}' has invalid status '{status}'."

        return _failed_action(op_id, action.id, original_path, error)

    # 3. Bind the action to its original scan session.
    session = get_scan_session(suggestion["session_id"])

    if not session:
        return _failed_action(
            op_id,
            action.id,
            original_path,
            (
                f"Security violation: Scan session "
                f"'{suggestion['session_id']}' for suggestion "
                f"'{action.id}' not found."
            ),
        )

    session_root = Path(session["root_dir"]).resolve()

    if session_root != resolved_root:
        return _failed_action(
            op_id,
            action.id,
            original_path,
            (
                f"Security violation: Action bound to scan root "
                f"'{session_root}' cannot be executed under root "
                f"'{resolved_root}'."
            ),
        )

    if settings.demo_mode and session_root != _demo_root():
        return _failed_action(
            op_id,
            action.id,
            original_path,
            "Demo mode blocked an action outside the sample playground.",
        )

    # Always use the persisted source path, not the client's path.
    raw_source = Path(original_path)

    # 4. Reject symlinks in the source path and its parent components.
    current = raw_source

    while True:
        if current.is_symlink():
            return _failed_action(
                op_id,
                action.id,
                str(raw_source),
                (
                    f"Security violation: Source path '{current}' "
                    "is a symlink. Operations on symlinks are blocked for safety."
                ),
            )

        if current == resolved_root or current.parent == current:
            break

        current = current.parent

    source = raw_source.resolve()

    # 5. The source must be strictly inside the approved root.
    if not is_safe_contained_path(source, resolved_root):
        return _failed_action(
            op_id,
            action.id,
            str(source),
            (
                f"Security violation: Source file '{source}' "
                f"is outside approved root '{resolved_root}'."
            ),
        )

    # 6. The source must exist and be a regular file.
    if not source.exists():
        return _failed_action(
            op_id,
            action.id,
            str(source),
            f"Source file does not exist: {source}",
        )

    if not source.is_file():
        return _failed_action(
            op_id,
            action.id,
            str(source),
            f"Source path is not a regular file: {source}",
        )

    if settings.demo_mode and not _demo_path_allowed(source):
        return _failed_action(
            op_id,
            action.id,
            str(source),
            "Demo mode blocked a source outside the sample playground.",
        )

    # 7. Reject files changed since the suggestion was created.
    file_stat = source.stat()
    recorded_size = suggestion.get("source_size_bytes")

    if recorded_size and file_stat.st_size != recorded_size:
        return _failed_action(
            op_id,
            action.id,
            str(source),
            (
                f"Source file '{source.name}' has changed since suggestion "
                "was generated (size mismatch). Operation rejected."
            ),
        )

    recorded_mtime = suggestion.get("source_mtime")

    if (
        recorded_mtime
        and abs(file_stat.st_mtime - recorded_mtime) > 1.0
    ):
        return _failed_action(
            op_id,
            action.id,
            str(source),
            (
                f"Source file '{source.name}' has changed since suggestion "
                "was generated (mtime mismatch). Operation rejected."
            ),
        )

    # Build the destination using the persisted suggestion.
    relative_path = suggestion["proposed_rel_path"].strip("/\\")
    clean_parts = [
        part
        for part in Path(relative_path).parts
        if part not in ("..", ".", "/", "\\")
    ]

    if not clean_parts:
        clean_parts = [suggestion["proposed_filename"]]

    raw_destination = resolved_root.joinpath(*clean_parts)

    # Reject symlinks in destination components before resolving.
    current = raw_destination

    while current != resolved_root and current != current.parent:
        if current.is_symlink():
            return _failed_action(
                op_id,
                action.id,
                str(source),
                (
                    f"Security violation: Destination path component "
                    f"'{current}' is a symlink. Symlinks are blocked."
                ),
            )

        current = current.parent

    destination = raw_destination.resolve()

    # 8. Destination must be strictly inside the approved root.
    if not is_safe_contained_path(destination, resolved_root):
        return _failed_action(
            op_id,
            action.id,
            str(source),
            (
                f"Security violation: Target destination '{destination}' "
                "escapes approved root directory."
            ),
        )

    if settings.demo_mode and not _demo_path_allowed(destination):
        return _failed_action(
            op_id,
            action.id,
            str(source),
            "Demo mode blocked a destination outside the sample playground.",
        )

    try:
        final_destination = get_unique_destination_path(
            destination,
            resolved_root,
        )

        final_destination.parent.mkdir(parents=True, exist_ok=True)

        # Recheck immediately before moving.
        if (
            final_destination.is_symlink()
            or not is_safe_contained_path(final_destination, resolved_root)
        ):
            raise ValueError("Destination failed its final safety check.")

        shutil.move(str(source), str(final_destination))

        if not final_destination.exists() or source.exists():
            raise IOError("Filesystem verification failed after move operation.")

        log_operation(
            op_id,
            action.id,
            str(source),
            str(final_destination),
            file_stat.st_size,
            status="executed",
        )
        update_suggestion_status(action.id, "executed")

        return ExecutedActionResult(
            action_id=action.id,
            operation_id=op_id,
            original_path=str(source),
            destination_path=str(final_destination),
            success=True,
            error=None,
        )

    except Exception as exc:
        return _failed_action(
            op_id,
            action.id,
            str(source),
            f"Move operation failed: {exc}",
        )


def execute_batch_actions(
    actions: list[ActionItem],
    root_dir_str: str,
) -> tuple[int, int, list[ExecutedActionResult]]:
    """Execute a batch of actions and return success/failure counts."""
    root_dir = Path(root_dir_str).resolve()
    results: list[ExecutedActionResult] = []
    succeeded = 0
    failed = 0

    for action in actions:
        result = execute_single_action(action, root_dir)
        results.append(result)

        if result.success:
            succeeded += 1
        else:
            failed += 1

    return succeeded, failed, results


def undo_operation(operation_id: str) -> UndoResponse:
    """Safely reverse an executed move without overwriting files."""
    operation = get_operation_by_id(operation_id)

    if not operation:
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message="Operation record not found.",
        )

    if operation["status"] == "undone":
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message="Operation has already been undone.",
        )

    if operation["status"] != "executed":
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=(
                f"Cannot undo operation with status '{operation['status']}'."
            ),
        )

    current_path = Path(operation["destination_path"])
    original_path = Path(operation["original_path"])

    # Demo-mode boundary checks must happen before filesystem changes.
    if settings.demo_mode:
        sample_root = _demo_root()

        if not is_safe_contained_path(current_path, sample_root):
            return UndoResponse(
                operation_id=operation_id,
                success=False,
                message=(
                    "Demo mode blocked undo: current file is outside "
                    "the sample playground."
                ),
            )

        if not is_safe_contained_path(original_path, sample_root):
            return UndoResponse(
                operation_id=operation_id,
                success=False,
                message=(
                    "Demo mode blocked undo: restore path is outside "
                    "the sample playground."
                ),
            )

        suggestion_id = operation.get("suggestion_id")

        if suggestion_id:
            suggestion = get_suggestion_by_id(suggestion_id)

            if not suggestion:
                return UndoResponse(
                    operation_id=operation_id,
                    success=False,
                    message="Undo blocked: associated suggestion was not found.",
                )

            session = get_scan_session(suggestion["session_id"])

            if (
                not session
                or Path(session["root_dir"]).resolve() != sample_root
            ):
                return UndoResponse(
                    operation_id=operation_id,
                    success=False,
                    message=(
                        "Demo mode blocked undo: associated scan session "
                        "is outside the sample playground."
                    ),
                )

    # Reject symlinks before resolving paths.
    if current_path.is_symlink():
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message="Destination path is a symlink. Undo blocked for safety.",
        )

    if original_path.is_symlink():
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message="Target restore path is a symlink. Undo blocked for safety.",
        )

    resolved_current = current_path.resolve()
    resolved_original = original_path.resolve()

    # Preserve the expected behavior when the moved file has disappeared.
    if not resolved_current.exists():
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=(
                f"Current file no longer exists at '{resolved_current}'. "
                "Cannot safely undo."
            ),
        )

    if not resolved_current.is_file():
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=(
                f"Current path is not a regular file at '{resolved_current}'. "
                "Cannot safely undo."
            ),
        )

    # Verify file integrity.
    if resolved_current.stat().st_size != operation["file_size"]:
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=(
                f"File at '{resolved_current}' has been modified since "
                "execution (size mismatch). Cannot safely undo."
            ),
        )

    if settings.demo_mode:
        sample_root = _demo_root()

        if not is_safe_contained_path(resolved_current, sample_root):
            return UndoResponse(
                operation_id=operation_id,
                success=False,
                message="Demo mode blocked undo outside the sample playground.",
            )

        if not is_safe_contained_path(resolved_original, sample_root):
            return UndoResponse(
                operation_id=operation_id,
                success=False,
                message="Demo mode blocked restore outside the sample playground.",
            )

    restore_path = resolved_original

    # Never overwrite an existing file.
    if restore_path.exists():
        restore_path = get_unique_destination_path(
            restore_path,
            restore_path.parent,
        )

    try:
        restore_path.parent.mkdir(parents=True, exist_ok=True)

        if settings.demo_mode and not is_safe_contained_path(
            restore_path,
            _demo_root(),
        ):
            return UndoResponse(
                operation_id=operation_id,
                success=False,
                message="Demo mode blocked the restore destination.",
            )

        if restore_path.is_symlink():
            return UndoResponse(
                operation_id=operation_id,
                success=False,
                message="Restore destination is a symlink. Undo blocked.",
            )

        shutil.move(str(resolved_current), str(restore_path))

        if not restore_path.exists() or resolved_current.exists():
            return UndoResponse(
                operation_id=operation_id,
                success=False,
                message="Filesystem verification failed after reversal attempt.",
            )

        mark_operation_undone(operation_id)

        suggestion_id = operation.get("suggestion_id")
        if suggestion_id:
            update_suggestion_status(suggestion_id, "pending")

        return UndoResponse(
            operation_id=operation_id,
            success=True,
            restored_path=str(restore_path),
            message=f"Successfully restored file to '{restore_path.name}'",
        )

    except Exception as exc:
        return UndoResponse(
            operation_id=operation_id,
            success=False,
            message=f"Undo failed: {exc}",
        )
