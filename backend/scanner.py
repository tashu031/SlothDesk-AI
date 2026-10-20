import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import pypdf

from backend.config import settings
from backend.models import FileMetadata

IGNORED_DIR_NAMES = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv", "env", 
    "__pycache__", ".pytest_cache", ".idea", ".vscode", "dist", "build",
    "appdata", "system volume information", "$recycle.bin", "recovery", "windows"
}

def is_path_safe_under_root(path: Path, root: Path) -> bool:
    """Verifies that resolved path is strictly within the resolved root directory."""
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
        return resolved_path == resolved_root or resolved_root in resolved_path.parents
    except Exception:
        return False

def extract_bounded_text(file_path: Path) -> tuple[Optional[str], bool]:
    """Safely extracts a bounded amount of text from supported document types."""
    ext = file_path.suffix.lower()
    
    if ext in settings.supported_text_extensions:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                snippet = f.read(settings.max_preview_bytes)
                # Trim and clean up whitespace
                cleaned = " ".join(snippet.split())
                return cleaned[:settings.max_llm_content_chars], True
        except Exception:
            return None, False

    elif ext in settings.supported_pdf_extensions:
        try:
            reader = pypdf.PdfReader(str(file_path))
            extracted_text = []
            for i, page in enumerate(reader.pages):
                if i >= 3:  # Only read first 3 pages
                    break
                text = page.extract_text()
                if text:
                    extracted_text.append(text)
            combined = " ".join(" ".join(extracted_text).split())
            return combined[:settings.max_llm_content_chars], True
        except Exception:
            return None, False

    return None, False

def scan_directory(root_dir_str: str, recursive: bool = True, max_files: int = 200) -> tuple[list[FileMetadata], float]:
    """
    Scans a folder safely, respecting exclusions, symlinks, bounds, and path isolation.
    """
    start_time = time.perf_counter()
    root_path = Path(root_dir_str).resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Selected root directory does not exist: {root_dir_str}")
    if not root_path.is_dir():
        raise ValueError(f"Path is not a directory: {root_dir_str}")

    discovered_files: list[FileMetadata] = []

    # Use os.walk for controlled traversal with exclusions
    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
        current_dir = Path(dirpath).resolve()

        # Security check: directory must be under root
        if not is_path_safe_under_root(current_dir, root_path):
            dirnames.clear()
            continue

        # Filter out ignored directories in-place to prevent traversing into them
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d.lower() not in IGNORED_DIR_NAMES
        ]

        if not recursive and current_dir != root_path:
            dirnames.clear()
            continue

        for filename in filenames:
            if filename.startswith("."):
                continue  # Skip hidden files

            file_path = current_dir / filename

            # Ensure file is not a symlink to prevent escapes
            if file_path.is_symlink():
                continue

            if not is_path_safe_under_root(file_path, root_path):
                continue

            try:
                stat = file_path.stat()
                rel_path = file_path.relative_to(root_path)

                snippet, is_supported = extract_bounded_text(file_path)

                created_iso = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
                modified_iso = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

                discovered_files.append(
                    FileMetadata(
                        path=str(file_path),
                        filename=filename,
                        relative_path=str(rel_path).replace("\\", "/"),
                        extension=file_path.suffix.lower(),
                        size_bytes=stat.st_size,
                        created_at=created_iso,
                        modified_at=modified_iso,
                        preview_snippet=snippet,
                        is_supported_content=is_supported
                    )
                )

                if len(discovered_files) >= max_files:
                    break
            except (PermissionError, FileNotFoundError):
                continue

        if len(discovered_files) >= max_files:
            break

    duration_ms = (time.perf_counter() - start_time) * 1000.0
    return discovered_files, duration_ms

def create_sample_playground(target_dir: Optional[Path] = None) -> Path:
    """
    Creates a realistic messy test directory with sample downloads and documents
    for first-time testing.
    """
    sample_root = target_dir or settings.sample_dir
    sample_root = sample_root.resolve()
    sample_root.mkdir(parents=True, exist_ok=True)

    samples = [
        ("CS101_Lecture04_BinaryTrees.pdf", b"%PDF-1.4 sample lecture on binary search trees, traversal algorithms, and AVL rotations in computer science"),
        ("draft_literature_review_v2_final.docx", "Literature review analyzing cognitive load theory in human-computer interaction and multimodal AI interfaces.".encode("utf-8")),
        ("IMG_8492_Screenshot_Meeting.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"),
        ("test_debug_script_scratch.py", "# Quick script to parse CSV data and test database connection\nimport sys\nprint('Testing parser')\n".encode("utf-8")),
        ("Q3_financial_quarterly_report_2026.csv", "Quarter,Revenue,Expenses,NetProfit\nQ1,120000,85000,35000\nQ2,145000,91000,54000\nQ3,180000,102000,78000\n".encode("utf-8")),
        ("todo_weekly_ideas_scratchpad.txt", "TODO:\n1. Buy groceries\n2. Prepare slide deck for Hacktoberfest Week 3 presentation\n3. Review Pull Requests\n".encode("utf-8")),
        ("app_architecture_diagram_v1.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"),
        ("dataset_user_feedback_clean.json", '{"feedbacks": [{"id": 1, "score": 5, "comment": "Great slow and steady AI assistant"}]}'.encode("utf-8")),
        ("bio102_lab_report_enzymes_draft.pdf", b"%PDF-1.4 Biology Lab Report: Kinetic analysis of catalase enzymes under varying pH and temperature conditions"),
        ("receipt_office_supplies_amazon_oct.pdf", b"%PDF-1.4 Tax Invoice: Office supplies, ergonomic keyboard, standing desk mat. Total $142.50")
    ]

    for name, content in samples:
        file_path = sample_root / name
        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception:
            pass

    return sample_root
