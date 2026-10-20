import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from backend.config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_sessions (
        id TEXT PRIMARY KEY,
        root_dir TEXT NOT NULL,
        scanned_at TEXT NOT NULL,
        total_files INTEGER NOT NULL,
        status TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suggestions (
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
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES scan_sessions(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operations (
        id TEXT PRIMARY KEY,
        suggestion_id TEXT,
        original_path TEXT NOT NULL,
        destination_path TEXT NOT NULL,
        file_size INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'executed',
        error_message TEXT,
        executed_at TEXT NOT NULL,
        undone_at TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

def save_scan_session(session_id: str, root_dir: str, total_files: int, status: str = "completed"):
    conn = get_db_connection()
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO scan_sessions (id, root_dir, scanned_at, total_files, status) VALUES (?, ?, ?, ?, ?)",
            (session_id, root_dir, datetime.now(timezone.utc).isoformat(), total_files, status)
        )
    conn.close()

def save_suggestions(suggestions: list[dict[str, Any]]):
    conn = get_db_connection()
    with conn:
        for s in suggestions:
            conn.execute(
                """
                INSERT OR REPLACE INTO suggestions 
                (id, session_id, original_path, original_filename, proposed_filename, category, proposed_rel_path, explanation, is_fallback, model_used, latency_ms, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s["id"],
                    s["session_id"],
                    s["original_path"],
                    s["original_filename"],
                    s["proposed_filename"],
                    s["category"],
                    s["proposed_rel_path"],
                    s["explanation"],
                    1 if s.get("is_fallback") else 0,
                    s.get("model_used", ""),
                    s.get("latency_ms", 0.0),
                    s.get("status", "pending"),
                    s.get("created_at", datetime.now(timezone.utc).isoformat())
                )
            )
    conn.close()

def update_suggestion_status(suggestion_id: str, status: str):
    conn = get_db_connection()
    with conn:
        conn.execute("UPDATE suggestions SET status = ? WHERE id = ?", (status, suggestion_id))
    conn.close()

def log_operation(op_id: str, suggestion_id: Optional[str], original_path: str, destination_path: str, file_size: int, status: str = "executed", error_message: Optional[str] = None):
    conn = get_db_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO operations (id, suggestion_id, original_path, destination_path, file_size, status, error_message, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (op_id, suggestion_id, original_path, destination_path, file_size, status, error_message, datetime.now(timezone.utc).isoformat())
        )
    conn.close()

def mark_operation_undone(op_id: str):
    conn = get_db_connection()
    with conn:
        conn.execute(
            "UPDATE operations SET status = 'undone', undone_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), op_id)
        )
    conn.close()

def get_recent_operations(limit: int = 50) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM operations ORDER BY executed_at DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_operation_by_id(op_id: str) -> Optional[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM operations WHERE id = ?", (op_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_activity_stats() -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM scan_sessions")
    total_scans = cursor.fetchone()["count"]

    cursor.execute("SELECT SUM(total_files) as count FROM scan_sessions")
    sum_files = cursor.fetchone()["count"] or 0

    cursor.execute("SELECT COUNT(*) as count FROM suggestions WHERE status = 'pending'")
    pending_suggestions = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM operations WHERE status = 'executed'")
    executed_ops = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM operations WHERE status = 'undone'")
    undone_ops = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM operations WHERE status = 'failed'")
    failed_ops = cursor.fetchone()["count"]

    conn.close()
    return {
        "total_scans": total_scans,
        "total_files_scanned": sum_files,
        "pending_suggestions": pending_suggestions,
        "executed_operations": executed_ops,
        "undone_operations": undone_ops,
        "failed_operations": failed_ops
    }
