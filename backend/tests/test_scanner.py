import os
import pytest
from pathlib import Path
from backend.scanner import scan_directory, is_path_safe_under_root, extract_bounded_text, create_sample_playground

def test_path_safety_check(tmp_path):
    root = tmp_path / "safe_root"
    root.mkdir()
    inside_file = root / "file.txt"
    inside_file.write_text("hello")

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("secret")

    assert is_path_safe_under_root(inside_file, root) is True
    assert is_path_safe_under_root(outside_file, root) is False
    
    # Path traversal attempt with ..
    traversal_path = root / ".." / "outside.txt"
    assert is_path_safe_under_root(traversal_path, root) is False

def test_scan_directory_basic(tmp_path):
    root = tmp_path / "test_folder"
    root.mkdir()

    (root / "doc1.txt").write_text("Sample document content")
    (root / "code.py").write_text("print('hello world')")
    (root / ".hidden_file").write_text("hidden")
    
    # Subdirectory with ignored name
    ignored_sub = root / "node_modules"
    ignored_sub.mkdir()
    (ignored_sub / "package.json").write_text("{}")

    # Valid subfolder
    sub = root / "sub_folder"
    sub.mkdir()
    (sub / "nested.md").write_text("# Title\nMarkdown text")

    files, duration_ms = scan_directory(str(root), recursive=True)
    
    # Hidden file and node_modules must be excluded
    filenames = [f.filename for f in files]
    assert "doc1.txt" in filenames
    assert "code.py" in filenames
    assert "nested.md" in filenames
    assert ".hidden_file" not in filenames
    assert "package.json" not in filenames
    assert duration_ms >= 0

def test_extract_bounded_text(tmp_path):
    file = tmp_path / "sample.txt"
    long_content = "Word " * 2000
    file.write_text(long_content)

    snippet, is_supported = extract_bounded_text(file)
    assert is_supported is True
    assert snippet is not None
    assert len(snippet) <= 1500

def test_create_sample_playground(tmp_path):
    sample_dir = tmp_path / "sample_test"
    created = create_sample_playground(sample_dir)
    assert created.exists()
    files = list(created.iterdir())
    assert len(files) >= 5
