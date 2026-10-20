import io
import os
import struct
import time
import zipfile
import zlib
import xml.etree.ElementTree as ET
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
    """
    Verifies that un-resolved path and resolved path are strictly within the root directory.
    Rejects path traversal, symlinks pointing outside, and root escapes.
    """
    try:
        if path.is_symlink():
            return False
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

    elif ext in settings.supported_docx_extensions:
        try:
            with zipfile.ZipFile(file_path, "r") as z:
                if "word/document.xml" in z.namelist():
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    texts = [elem.text for elem in tree.iter() if elem.text]
                    combined = " ".join(" ".join(texts).split())
                    return combined[:settings.max_llm_content_chars], True
        except Exception:
            return None, False

    return None, False

def scan_directory(root_dir_str: str, recursive: bool = True, max_files: int = 200) -> tuple[list[FileMetadata], float]:
    """
    Scans a folder safely, respecting exclusions, symlinks, bounds, and path isolation.
    """
    start_time = time.perf_counter()
    raw_root = Path(root_dir_str)

    if raw_root.is_symlink():
        raise ValueError(f"Root path cannot be a symlink: {root_dir_str}")

    root_path = raw_root.resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Selected root directory does not exist: {root_dir_str}")
    if not root_path.is_dir():
        raise ValueError(f"Path is not a directory: {root_dir_str}")

    discovered_files: list[FileMetadata] = []

    # Use os.walk for controlled traversal with exclusions
    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
        current_dir = Path(dirpath)

        # Reject symlinked directories
        if current_dir.is_symlink():
            dirnames.clear()
            continue

        resolved_current = current_dir.resolve()
        if not is_path_safe_under_root(resolved_current, root_path):
            dirnames.clear()
            continue

        # Filter out ignored directories in-place to prevent traversing into them
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d.lower() not in IGNORED_DIR_NAMES
        ]

        if not recursive and resolved_current != root_path:
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
                        path=str(file_path.resolve()),
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

def _make_valid_pdf_bytes(text: str) -> bytes:
    """Generates a valid, parseable minimal PDF-1.4 file containing the given text."""
    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 50 720 Td ({safe_text}) Tj ET".encode("latin1")

    parts = [b"%PDF-1.4\n"]
    offsets = []

    def add_obj(num: int, data: bytes):
        offsets.append(sum(len(p) for p in parts))
        parts.append(f"{num} 0 obj\n".encode("latin1") + data + b"\nendobj\n")

    add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add_obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")
    add_obj(4, b"<< /Length " + str(len(stream)).encode("latin1") + b" >>\nstream\n" + stream + b"\nendstream")
    add_obj(5, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    startxref = sum(len(p) for p in parts)
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    for off in offsets:
        xref.append(f"{off:010d} 00000 n \n".encode("latin1"))

    trailer = b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(startxref).encode("latin1") + b"\n%%EOF\n"
    return b"".join(parts) + b"".join(xref) + trailer

def _make_valid_docx_bytes(text: str) -> bytes:
    """Generates a genuine valid minimal DOCX (OpenXML) file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""")
        z.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""")
        z.writestr("word/document.xml", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>""")
    return buf.getvalue()

def _make_valid_png_bytes() -> bytes:
    """Generates a genuine valid 1x1 PNG image."""
    raw_pixel = b"\x00\x1b\x3b\x2b\xff"  # filter 0, RGBA
    compressed = zlib.compress(raw_pixel)

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c))
        return struct.pack(">I", len(data)) + c + crc

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")

def create_sample_playground(target_dir: Optional[Path] = None) -> Path:
    """
    Creates a realistic messy test directory with genuine, valid sample documents,
    spreadsheets, code, and images for testing.
    """
    sample_root = target_dir or settings.sample_dir
    sample_root = sample_root.resolve()
    sample_root.mkdir(parents=True, exist_ok=True)

    samples = [
        ("CS101_Lecture04_BinaryTrees.pdf", _make_valid_pdf_bytes("Lecture on binary search trees, traversal algorithms, and AVL rotations in computer science")),
        ("draft_literature_review_v2_final.docx", _make_valid_docx_bytes("Literature review analyzing cognitive load theory in human-computer interaction and multimodal AI interfaces.")),
        ("IMG_8492_Screenshot_Meeting.png", _make_valid_png_bytes()),
        ("test_debug_script_scratch.py", "# Quick script to parse CSV data and test database connection\nimport sys\nprint('Testing parser')\n".encode("utf-8")),
        ("Q3_financial_quarterly_report_2026.csv", "Quarter,Revenue,Expenses,NetProfit\nQ1,120000,85000,35000\nQ2,145000,91000,54000\nQ3,180000,102000,78000\n".encode("utf-8")),
        ("todo_weekly_ideas_scratchpad.txt", "TODO:\n1. Buy groceries\n2. Prepare slide deck for Hacktoberfest Week 3 presentation\n3. Review Pull Requests\n".encode("utf-8")),
        ("app_architecture_diagram_v1.png", _make_valid_png_bytes()),
        ("dataset_user_feedback_clean.json", '{"feedbacks": [{"id": 1, "score": 5, "comment": "Great slow and steady AI assistant"}]}'.encode("utf-8")),
        ("bio102_lab_report_enzymes_draft.pdf", _make_valid_pdf_bytes("Biology Lab Report: Kinetic analysis of catalase enzymes under varying pH and temperature conditions")),
        ("receipt_office_supplies_amazon_oct.pdf", _make_valid_pdf_bytes("Tax Invoice: Office supplies, ergonomic keyboard, standing desk mat. Total $142.50"))
    ]

    for name, content in samples:
        file_path = sample_root / name
        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception:
            pass

    return sample_root
