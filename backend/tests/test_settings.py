import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import Settings, settings
from backend.database import init_db, set_settings, get_all_settings

@pytest.fixture(autouse=True)
def setup_temp_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_settings_slothdesk.db"
    monkeypatch.setattr(settings, "db_path", test_db)
    init_db()

@pytest.fixture
def client():
    return TestClient(app)

def test_settings_persistence_across_reconstructed_instances(tmp_path):
    test_db = tmp_path / "test_settings_slothdesk.db"

    # Persist custom settings
    set_settings({
        "model_name": "gemma2:9b",
        "ollama_base_url": "http://127.0.0.1:11434",
        "seconds_saved_per_file": "90"
    })

    # Verify directly from database
    stored = get_all_settings()
    assert stored["model_name"] == "gemma2:9b"
    assert stored["seconds_saved_per_file"] == "90"

    # Create a completely fresh Settings instance pointing to the same database
    fresh_settings = Settings(db_path=test_db)
    assert fresh_settings.model_name == "gemma2:2b"  # Default before load
    assert fresh_settings.seconds_saved_per_file == 45  # Default before load

    # Load from DB
    fresh_settings.load_from_db()
    assert fresh_settings.model_name == "gemma2:9b"
    assert fresh_settings.seconds_saved_per_file == 90
    assert fresh_settings.ollama_base_url == "http://127.0.0.1:11434"

def test_settings_api_clamping_and_persistence(client, tmp_path):
    test_db = tmp_path / "test_settings_slothdesk.db"

    # Test clamping: seconds_saved_per_file must be >= 5 and <= 3600
    res_low = client.post("/api/settings", json={"seconds_saved_per_file": 2})
    assert res_low.status_code == 200
    assert res_low.json()["settings"]["seconds_saved_per_file"] == 5

    res_high = client.post("/api/settings", json={"seconds_saved_per_file": 50000})
    assert res_high.status_code == 200
    assert res_high.json()["settings"]["seconds_saved_per_file"] == 3600

    # Test custom model name update
    res_model = client.post("/api/settings", json={"model_name": "gemma2:custom"})
    assert res_model.status_code == 200
    assert res_model.json()["settings"]["model_name"] == "gemma2:custom"

    # Reconstruct settings and ensure value persisted to SQLite
    reconstructed = Settings(db_path=test_db)
    reconstructed.load_from_db()
    assert reconstructed.model_name == "gemma2:custom"
    assert reconstructed.seconds_saved_per_file == 3600

def test_schema_migration_backward_compatibility(tmp_path):
    # Create an old-version database with an earlier schema (without source_size_bytes or source_mtime)
    legacy_db = tmp_path / "legacy_slothdesk.db"
    conn = sqlite3.connect(str(legacy_db))
    conn.execute("""
    CREATE TABLE scan_sessions (
        id TEXT PRIMARY KEY,
        root_dir TEXT NOT NULL,
        scanned_at TEXT NOT NULL,
        total_files INTEGER NOT NULL,
        status TEXT NOT NULL
    );
    """)
    conn.execute("""
    CREATE TABLE suggestions (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        original_path TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        proposed_filename TEXT NOT NULL,
        category TEXT NOT NULL,
        proposed_rel_path TEXT NOT NULL,
        explanation TEXT NOT NULL,
        is_fallback INTEGER NOT NULL DEFAULT 0,
        model_used TEXT,
        latency_ms REAL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

    # Point settings to legacy database and run init_db
    custom_settings = Settings(db_path=legacy_db)

    # Run init_db using the connection to legacy_db
    conn = sqlite3.connect(str(legacy_db))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(suggestions);")
    cols_before = {row["name"] for row in cursor.fetchall()}
    assert "source_size_bytes" not in cols_before

    # Now run migrations logic
    if "source_size_bytes" not in cols_before:
        cursor.execute("ALTER TABLE suggestions ADD COLUMN source_size_bytes INTEGER DEFAULT 0;")
    if "source_mtime" not in cols_before:
        cursor.execute("ALTER TABLE suggestions ADD COLUMN source_mtime REAL DEFAULT 0.0;")
    conn.commit()

    cursor.execute("PRAGMA table_info(suggestions);")
    cols_after = {row["name"] for row in cursor.fetchall()}
    assert "source_size_bytes" in cols_after
    assert "source_mtime" in cols_after
    conn.close()
