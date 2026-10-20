import os
import time
import pytest
from pathlib import Path

from backend.config import settings
from backend.database import (
    init_db, save_scan_session, save_suggestions, approve_suggestions,
    get_suggestion_by_id
)
from backend.models import ActionItem
from backend.organizer import (
    execute_single_action, execute_batch_actions, undo_operation
)

@pytest.fixture(autouse=True)
def setup_temp_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_security_slothdesk.db"
    monkeypatch.setattr(settings, "db_path", test_db)
    init_db()

def setup_test_suggestion(
    root: Path,
    file_name: str,
    content: str = "Test Content",
    action_id: str = "sug_sec_1",
    proposed_rel: str = "Documents/test.txt",
    approved: bool = True
) -> tuple[Path, ActionItem]:
    test_file = root / file_name
    test_file.write_text(content)
    stat = test_file.stat()

    session_id = f"sess_{action_id}"
    save_scan_session(session_id, str(root.resolve()), 1)

    sug = {
        "id": action_id,
        "session_id": session_id,
        "original_path": str(test_file.resolve()),
        "original_filename": file_name,
        "proposed_filename": Path(proposed_rel).name,
        "category": "Documents",
        "proposed_rel_path": proposed_rel,
        "explanation": "Security test",
        "is_fallback": 1,
        "model_used": "deterministic_rules",
        "latency_ms": 1.0,
        "status": "pending",
        "source_size_bytes": stat.st_size,
        "source_mtime": stat.st_mtime
    }
    save_suggestions([sug])
    if approved:
        approve_suggestions([action_id])

    action = ActionItem(
        id=action_id,
        original_path=str(test_file.resolve()),
        proposed_filename=Path(proposed_rel).name,
        category="Documents",
        proposed_rel_path=proposed_rel,
        approved=approved
    )
    return test_file, action

def test_forged_action_id_rejected(tmp_path):
    root = tmp_path / "valid_root"
    root.mkdir()
    fake_file = root / "some_file.txt"
    fake_file.write_text("Hello")

    action = ActionItem(
        id="forged_action_999",
        original_path=str(fake_file),
        proposed_filename="file.txt",
        category="Documents",
        proposed_rel_path="Documents/file.txt",
        approved=True
    )

    result = execute_single_action(action, root)
    assert result.success is False
    assert "Security violation" in result.error
    assert "does not correspond to a valid persisted suggestion" in result.error

def test_unapproved_action_rejected(tmp_path):
    root = tmp_path / "valid_root"
    root.mkdir()

    # Suggestion is 'pending' on the server.
    # Client sends approved=True, but server-side approval is NOT granted!
    test_file, action = setup_test_suggestion(
        root=root,
        file_name="unapproved_file.txt",
        action_id="sug_unapproved_1",
        approved=False
    )
    # Untrusted client boolean claims approved, but server must reject it!
    action.approved = True

    result = execute_single_action(action, root)
    assert result.success is False
    assert "has not been approved for execution" in result.error
    assert test_file.exists()

def test_explicit_unapproved_flag_in_request_rejected(tmp_path):
    root = tmp_path / "valid_root"
    root.mkdir()

    test_file, action = setup_test_suggestion(
        root=root,
        file_name="approved_in_db_but_not_in_client.txt",
        action_id="sug_client_unapproved_1",
        approved=True
    )

    # Client explicitly passes approved=False
    action.approved = False
    result = execute_single_action(action, root)
    assert result.success is False
    assert "marked unapproved" in result.error
    assert test_file.exists()

def test_changed_source_file_rejected(tmp_path):
    root = tmp_path / "valid_root"
    root.mkdir()

    test_file, action = setup_test_suggestion(
        root=root,
        file_name="will_change.txt",
        content="Original content 12345",
        action_id="sug_change_1",
        approved=True
    )

    # Modify file content/size on disk after suggestion was recorded
    test_file.write_text("Modified content that is much longer than original!")

    result = execute_single_action(action, root)
    assert result.success is False
    assert "has changed since suggestion was generated" in result.error
    assert test_file.exists()

def test_path_traversal_outside_root_rejected(tmp_path):
    root = tmp_path / "jail_root"
    root.mkdir()
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("super secret")

    # Save a suggestion with a path outside the root
    save_scan_session("sess_jail", str(root.resolve()), 1)
    save_suggestions([{
        "id": "sug_traversal_1",
        "session_id": "sess_jail",
        "original_path": str(outside_file.resolve()),
        "original_filename": "secret.txt",
        "proposed_filename": "escaped.txt",
        "category": "Documents",
        "proposed_rel_path": "Documents/escaped.txt",
        "explanation": "Traversal attack",
        "is_fallback": 1,
        "model_used": "rules",
        "latency_ms": 1.0,
        "status": "approved",
        "source_size_bytes": 12,
        "source_mtime": 0.0
    }])

    action = ActionItem(
        id="sug_traversal_1",
        original_path=str(outside_file.resolve()),
        proposed_filename="escaped.txt",
        category="Documents",
        proposed_rel_path="Documents/escaped.txt",
        approved=True
    )

    result = execute_single_action(action, root)
    assert result.success is False
    assert "outside approved root" in result.error
    assert outside_file.exists()

def test_destination_traversal_rejected(tmp_path):
    root = tmp_path / "jail_root"
    root.mkdir()
    test_file = root / "normal.txt"
    test_file.write_text("Hello")

    save_scan_session("sess_dest_trav", str(root.resolve()), 1)
    save_suggestions([{
        "id": "sug_dest_trav",
        "session_id": "sess_dest_trav",
        "original_path": str(test_file.resolve()),
        "original_filename": "normal.txt",
        "proposed_filename": "escape.txt",
        "category": "Documents",
        "proposed_rel_path": "../../escape.txt",
        "explanation": "Traversal in rel path",
        "is_fallback": 1,
        "model_used": "rules",
        "latency_ms": 1.0,
        "status": "approved",
        "source_size_bytes": 5,
        "source_mtime": test_file.stat().st_mtime
    }])

    action = ActionItem(
        id="sug_dest_trav",
        original_path=str(test_file.resolve()),
        proposed_filename="escape.txt",
        category="Documents",
        proposed_rel_path="../../escape.txt",
        approved=True
    )

    # Clean parts in organizer strips .. so destination is kept safe within root
    result = execute_single_action(action, root)
    assert result.success is True
    dest_path = Path(result.destination_path)
    assert root.resolve() in dest_path.resolve().parents

def test_symlink_escapes_rejected(tmp_path):
    root = tmp_path / "symlink_root"
    root.mkdir()
    target_file = tmp_path / "target_outside.txt"
    target_file.write_text("outside data")

    symlink_file = root / "symlink_inside.txt"
    try:
        symlink_file.symlink_to(target_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not permitted in this environment")

    save_scan_session("sess_symlink", str(root.resolve()), 1)
    save_suggestions([{
        "id": "sug_symlink_1",
        "session_id": "sess_symlink",
        "original_path": str(symlink_file),
        "original_filename": "symlink_inside.txt",
        "proposed_filename": "symlink_inside.txt",
        "category": "Documents",
        "proposed_rel_path": "Documents/symlink_inside.txt",
        "explanation": "Symlink test",
        "is_fallback": 1,
        "model_used": "rules",
        "latency_ms": 1.0,
        "status": "approved",
        "source_size_bytes": 12,
        "source_mtime": target_file.stat().st_mtime
    }])

    action = ActionItem(
        id="sug_symlink_1",
        original_path=str(symlink_file),
        proposed_filename="symlink_inside.txt",
        category="Documents",
        proposed_rel_path="Documents/symlink_inside.txt",
        approved=True
    )

    # Must reject symlink BEFORE resolving
    result = execute_single_action(action, root)
    assert result.success is False
    assert "symlink" in result.error.lower()
    assert target_file.exists()

def test_mismatched_session_root_rejected(tmp_path):
    root_a = tmp_path / "root_a"
    root_b = tmp_path / "root_b"
    root_a.mkdir()
    root_b.mkdir()

    test_file, action = setup_test_suggestion(
        root=root_a,
        file_name="file_a.txt",
        action_id="sug_mismatch_1",
        approved=True
    )

    # Attempt execution against root_b
    result = execute_single_action(action, root_b)
    assert result.success is False
    assert "Security violation" in result.error
    assert "cannot be executed under root" in result.error

def test_conflicting_destinations_prevent_data_loss(tmp_path):
    root = tmp_path / "conflict_root"
    root.mkdir()
    (root / "Documents").mkdir()

    # Pre-existing file at destination
    existing_dest = root / "Documents" / "File.txt"
    existing_dest.write_text("I am the existing original file that must never be overwritten!")

    test_file, action = setup_test_suggestion(
        root=root,
        file_name="messy_file.txt",
        content="I am the new incoming file",
        action_id="sug_conflict_test",
        proposed_rel="Documents/File.txt",
        approved=True
    )

    result = execute_single_action(action, root)
    assert result.success is True
    dest_path = Path(result.destination_path)
    assert dest_path.name == "File_1.txt"
    assert dest_path.exists()
    assert dest_path.read_text() == "I am the new incoming file"
    assert existing_dest.exists()
    assert existing_dest.read_text() == "I am the existing original file that must never be overwritten!"

def test_unsafe_undo_when_file_modified(tmp_path):
    root = tmp_path / "undo_test_root"
    root.mkdir()

    test_file, action = setup_test_suggestion(
        root=root,
        file_name="note.txt",
        content="123456",
        action_id="sug_undo_tamper",
        approved=True
    )

    result = execute_single_action(action, root)
    assert result.success is True

    # Tamper with the moved destination file (alter size)
    dest_path = Path(result.destination_path)
    dest_path.write_text("1234567890EXTRA")

    # Undo must safely reject reversal because file was modified
    undo_res = undo_operation(result.operation_id)
    assert undo_res.success is False
    assert "has been modified since execution" in undo_res.message

def test_undo_destination_conflict_resolved_safely(tmp_path):
    root = tmp_path / "undo_conflict_root"
    root.mkdir()

    test_file, action = setup_test_suggestion(
        root=root,
        file_name="resume.pdf",
        content="Original resume content",
        action_id="sug_undo_conflict",
        proposed_rel="Documents/resume.pdf",
        approved=True
    )

    result = execute_single_action(action, root)
    assert result.success is True
    dest_path = Path(result.destination_path)
    assert dest_path.exists()

    # Create a new file where original file used to be
    test_file.write_text("New file created at original location")

    # Undo must safely restore without overwriting the new file
    undo_res = undo_operation(result.operation_id)
    assert undo_res.success is True
    restored_path = Path(undo_res.restored_path)
    assert restored_path.exists()
    assert restored_path != test_file  # Got a unique conflict-free name
    assert restored_path.read_text() == "Original resume content"
    assert test_file.read_text() == "New file created at original location"
