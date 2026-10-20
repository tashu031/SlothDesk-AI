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
