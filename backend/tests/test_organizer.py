import pytest
from pathlib import Path
from backend.config import settings
from backend.database import (
    init_db, save_scan_session, save_suggestions, approve_suggestions,
    get_operation_by_id
)
from backend.models import ActionItem
from backend.organizer import (
    execute_single_action, execute_batch_actions, undo_operation,
    is_safe_contained_path, get_unique_destination_path
)
from backend.ai_engine import sanitize_filename

@pytest.fixture(autouse=True)
def setup_temp_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_slothdesk.db"
    monkeypatch.setattr(settings, "db_path", test_db)
    init_db()

def create_valid_persisted_suggestion(
    session_id: str,
    root_dir: Path,
    file_path: Path,
    action_id: str = "sug_test_1",
    proposed_filename: str = "Clean_File.txt",
    category: str = "Documents",
    proposed_rel_path: str = "Documents/Clean_File.txt",
    approved: bool = True
) -> ActionItem:
    """Helper to create a genuine session and persisted suggestion in SQLite for tests."""
    save_scan_session(session_id, str(root_dir.resolve()), 1)
    stat = file_path.stat() if file_path.exists() else None
    sug_dict = {
        "id": action_id,
        "session_id": session_id,
        "original_path": str(file_path.resolve()),
        "original_filename": file_path.name,
        "proposed_filename": proposed_filename,
        "category": category,
        "proposed_rel_path": proposed_rel_path,
        "explanation": "Test suggestion",
        "is_fallback": 1,
        "model_used": "deterministic_rules",
        "latency_ms": 1.0,
        "status": "pending",
        "source_size_bytes": stat.st_size if stat else 0,
        "source_mtime": stat.st_mtime if stat else 0.0
    }
    save_suggestions([sug_dict])
    if approved:
        approve_suggestions([action_id])
    return ActionItem(
        id=action_id,
        original_path=str(file_path.resolve()),
        proposed_filename=proposed_filename,
        category=category,
        proposed_rel_path=proposed_rel_path,
        approved=approved
    )

def test_sanitize_filename():
    assert sanitize_filename("my:weird/file\\name?.txt") == "myweirdfilename.txt"
    assert sanitize_filename("../../../malicious.sh") == "malicious.sh"
    assert sanitize_filename(".hidden") == "hidden"
    assert sanitize_filename("") == "unnamed_file"

def test_conflict_free_destination(tmp_path):
    root = tmp_path / "organize_root"
    root.mkdir()

    target = root / "report.pdf"
    target.write_text("existing report")

    # When report.pdf already exists, candidate must become report_1.pdf
    unique_path = get_unique_destination_path(target, root)
    assert unique_path.name == "report_1.pdf"

    # If report_1.pdf also exists, candidate becomes report_2.pdf
    unique_path.write_text("second report")
    unique_path_2 = get_unique_destination_path(target, root)
    assert unique_path_2.name == "report_2.pdf"

def test_successful_move_and_undo(tmp_path):
    root = tmp_path / "organize_root"
    root.mkdir()

    test_file = root / "messy_essay_draft.docx"
    test_file.write_text("Homework essay content")

    action = create_valid_persisted_suggestion(
        session_id="sess_valid_1",
        root_dir=root,
        file_path=test_file,
        action_id="act_valid_1",
        proposed_filename="Essay_Draft.docx",
        category="Documents",
        proposed_rel_path="Documents/Essay_Draft.docx",
        approved=True
    )

    # Execute move
    result = execute_single_action(action, root)
    assert result.success is True
    dest_path = Path(result.destination_path)
    assert dest_path.exists()
    assert not test_file.exists()
    assert dest_path.read_text() == "Homework essay content"

    # Test Undo
    undo_res = undo_operation(result.operation_id)
    assert undo_res.success is True
    assert test_file.exists()
    assert not dest_path.exists()
    assert test_file.read_text() == "Homework essay content"

def test_undo_fails_safely_if_file_removed(tmp_path):
    root = tmp_path / "organize_root"
    root.mkdir()

    test_file = root / "temp.txt"
    test_file.write_text("abc")

    action = create_valid_persisted_suggestion(
        session_id="sess_undo_missing",
        root_dir=root,
        file_path=test_file,
        action_id="act_undo_missing",
        proposed_filename="renamed.txt",
        category="Documents",
        proposed_rel_path="Documents/renamed.txt",
        approved=True
    )

    result = execute_single_action(action, root)
    assert result.success is True

    # Delete destination file manually to simulate unexpected disappearance
    Path(result.destination_path).unlink()

    # Undo must safely report failure without crashing
    undo_res = undo_operation(result.operation_id)
    assert undo_res.success is False
    assert "no longer exists" in undo_res.message
