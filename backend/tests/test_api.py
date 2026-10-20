import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from backend.main import app
from backend.config import settings
from backend.database import init_db

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_api_slothdesk.db"
    monkeypatch.setattr(settings, "db_path", test_db)
    init_db()

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app"] == "SlothDesk AI"

def test_ai_status(client):
    res = client.get("/api/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert "ollama_available" in data
    assert "inference_mode" in data
    assert data["offline_ready"] is True

def test_scan_and_suggest_pipeline(client, tmp_path):
    # Create test directory with files
    scan_dir = tmp_path / "messy_folder"
    scan_dir.mkdir()
    (scan_dir / "invoice_march.pdf").write_text("Tax Invoice #12345 for services rendered.")
    (scan_dir / "calc_budget.py").write_text("def calc(): return 100")

    # Call /api/scan
    scan_res = client.post("/api/scan", json={"folder_path": str(scan_dir), "recursive": True})
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert scan_data["files_scanned"] == 2
    session_id = scan_data["session_id"]

    # Call /api/suggestions
    sug_res = client.post("/api/suggestions", json={
        "session_id": session_id,
        "root_path": str(scan_dir),
        "files": scan_data["files"]
    })
    assert sug_res.status_code == 200
    sug_data = sug_res.json()
    assert len(sug_data["suggestions"]) == 2

    first_sug = sug_data["suggestions"][0]
    assert first_sug["category"] in ["Documents", "Code", "Data", "Study", "Images", "Archives", "Miscellaneous"]

    # Test /api/summary
    summary_res = client.get("/api/summary")
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["total_scans"] >= 1
    assert "Lazy Morning Brief" or "🦥" in summary_data["lazy_morning_brief"]

def test_api_approval_execution_and_undo_flow(client, tmp_path):
    scan_dir = tmp_path / "api_exec_folder"
    scan_dir.mkdir()
    test_file = scan_dir / "quick_test.py"
    test_file.write_text("print('hello world')")

    scan_res = client.post("/api/scan", json={"folder_path": str(scan_dir), "recursive": True})
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    session_id = scan_data["session_id"]

    sug_res = client.post("/api/suggestions", json={
        "session_id": session_id,
        "root_path": str(scan_dir),
        "files": scan_data["files"]
    })
    assert sug_res.status_code == 200
    sug_data = sug_res.json()
    sug = sug_data["suggestions"][0]
    sug_id = sug["id"]

    # Step 1: Execution BEFORE approval must be rejected by server
    exec_unapproved = client.post("/api/execute", json={
        "root_path": str(scan_dir),
        "actions": [{
            "id": sug_id,
            "original_path": sug["original_path"],
            "proposed_filename": sug["proposed_filename"],
            "category": sug["category"],
            "proposed_rel_path": sug["proposed_rel_path"],
            "approved": True
        }]
    })
    assert exec_unapproved.status_code == 200
    res_data = exec_unapproved.json()
    assert res_data["total_failed"] == 1
    assert res_data["total_succeeded"] == 0
    assert "not been approved for execution" in res_data["results"][0]["error"]
    assert test_file.exists()

    # Step 2: Explicit server-side approval
    appr_res = client.post("/api/suggestions/approve", json={"suggestion_ids": [sug_id]})
    assert appr_res.status_code == 200
    assert sug_id in appr_res.json()["approved_ids"]

    # Step 3: Execution AFTER approval succeeds
    exec_approved = client.post("/api/execute", json={
        "root_path": str(scan_dir),
        "actions": [{
            "id": sug_id,
            "original_path": sug["original_path"],
            "proposed_filename": sug["proposed_filename"],
            "category": sug["category"],
            "proposed_rel_path": sug["proposed_rel_path"],
            "approved": True
        }]
    })
    assert exec_approved.status_code == 200
    res_data2 = exec_approved.json()
    assert res_data2["total_succeeded"] == 1
    assert res_data2["total_failed"] == 0
    assert not test_file.exists()
    op_id = res_data2["results"][0]["operation_id"]
    dest_path = Path(res_data2["results"][0]["destination_path"])
    assert dest_path.exists()

    # Step 4: Undo via /api/undo restores file safely
    undo_res = client.post("/api/undo", json={"operation_id": op_id})
    assert undo_res.status_code == 200
    assert undo_res.json()["success"] is True
    assert test_file.exists()
    assert not dest_path.exists()

def test_settings_endpoints(client):
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["seconds_saved_per_file"] == 45

    post_res = client.post("/api/settings", json={"seconds_saved_per_file": 60})
    assert post_res.status_code == 200
    assert post_res.json()["settings"]["seconds_saved_per_file"] == 60

def test_evaluation_endpoint(client):
    eval_res = client.post("/api/evaluate?force_deterministic=true")
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert data["total_samples"] == 10
    assert data["accuracy_percentage"] >= 70.0
    assert data["is_fallback"] is True
