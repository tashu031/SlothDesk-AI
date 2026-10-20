import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    app_name: str = "SlothDesk AI"
    app_version: str = "1.0.0"
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name: str = os.getenv("SLOTHDESK_MODEL", os.getenv("OLLAMA_MODEL", "gemma2:2b"))
    db_path: Path = Path(os.getenv("SLOTHDESK_DB_PATH", str(BASE_DIR / "slothdesk.db")))
    seconds_saved_per_file: int = int(os.getenv("SECONDS_SAVED_PER_FILE", "45"))
    max_scan_files: int = int(os.getenv("MAX_SCAN_FILES", "500"))
    max_preview_bytes: int = int(os.getenv("MAX_PREVIEW_BYTES", "4096"))
    max_llm_content_chars: int = int(os.getenv("MAX_LLM_CONTENT_CHARS", "1500"))
    sample_dir: Path = BASE_DIR / "sample_playground"
    supported_text_extensions: set[str] = {
        ".txt", ".md", ".markdown", ".py", ".js", ".ts", ".html",
        ".css", ".json", ".csv", ".yaml", ".yml", ".sql", ".sh", ".rst"
    }
    supported_pdf_extensions: set[str] = {".pdf"}
    supported_docx_extensions: set[str] = {".docx"}

    # Common categories and their target subfolders
    default_categories: dict[str, str] = {
        "Documents": "Documents",
        "Study": "Study_Materials",
        "Code": "Code_Projects",
        "Images": "Images_Media",
        "Data": "Data_Sheets",
        "Archives": "Archives",
        "Miscellaneous": "Miscellaneous"
    }

    def load_from_db(self):
        """
        Loads saved user settings from SQLite if present, validates values,
        and applies sensible defaults so preferences persist across restarts.
        """
        try:
            from backend.database import get_all_settings
            saved = get_all_settings()
            if not saved:
                return

            if "model_name" in saved and saved["model_name"].strip():
                self.model_name = saved["model_name"].strip()

            if "ollama_base_url" in saved and saved["ollama_base_url"].strip():
                url = saved["ollama_base_url"].strip()
                if url.startswith("http://") or url.startswith("https://"):
                    self.ollama_base_url = url

            if "seconds_saved_per_file" in saved:
                try:
                    val = int(saved["seconds_saved_per_file"])
                    self.seconds_saved_per_file = max(5, min(3600, val))
                except (ValueError, TypeError):
                    pass

            if "default_categories" in saved:
                try:
                    cats = json.loads(saved["default_categories"])
                    if isinstance(cats, dict):
                        self.default_categories.update(cats)
                except Exception:
                    pass
        except Exception:
            pass

settings = Settings()
