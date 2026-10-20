import pytest
from backend.ai_engine import (
    parse_llm_json, deterministic_classify, check_ollama_status, LLMSuggestionSchema
)
from backend.models import FileMetadata

def test_parse_llm_json_raw_object():
    raw = '{"category": "Documents", "suggested_filename": "Doc.pdf", "suggested_subfolder": "Documents", "reason": "Test"}'
    res = parse_llm_json(raw)
    assert res is not None
    assert res["category"] == "Documents"
    validated = LLMSuggestionSchema.model_validate(res)
    assert validated.suggested_filename == "Doc.pdf"

def test_parse_llm_json_markdown_fenced_block():
    raw = '''Here is the requested suggestion:
```json
{
  "category": "Code",
  "suggested_filename": "script.py",
  "suggested_subfolder": "Code_Projects",
  "reason": "Python script"
}
```
Let me know if you need more.'''
    res = parse_llm_json(raw)
    assert res is not None
    assert res["category"] == "Code"
    assert res["suggested_filename"] == "script.py"

def test_parse_llm_json_embedded_braces():
    raw = 'I classified your file: {"category": "Data", "suggested_filename": "metrics.csv", "suggested_subfolder": "Data_Sheets", "reason": "CSV metrics"}. Enjoy!'
    res = parse_llm_json(raw)
    assert res is not None
    assert res["category"] == "Data"

def test_parse_llm_json_malformed():
    raw = "Not a JSON at all, just plain text with error."
    res = parse_llm_json(raw)
    assert res is None

def test_deterministic_invoice_not_classified_as_code():
    meta = FileMetadata(
        path="/sample/invoice_apple_developer_program_2026.pdf",
        filename="invoice_apple_developer_program_2026.pdf",
        relative_path="invoice_apple_developer_program_2026.pdf",
        extension=".pdf",
        size_bytes=2048,
        created_at="2026-10-20T00:00:00Z",
        modified_at="2026-10-20T00:00:00Z",
        preview_snippet="Tax Invoice: Apple Developer Program Annual Subscription Renewal. Total Paid $99.00 USD.",
        is_supported_content=True
    )
    category, proposed_name, subfolder, explanation = deterministic_classify(meta)
    assert category == "Documents"
    assert "matched keyword: 'tax invoice'" in explanation or "matched keyword: 'invoice'" in explanation
    assert subfolder == "Documents"

def test_deterministic_essay_not_classified_as_study_due_to_examining():
    meta = FileMetadata(
        path="/sample/Draft_Essay_Ethics_In_Tech.docx",
        filename="Draft_Essay_Ethics_In_Tech.docx",
        relative_path="Draft_Essay_Ethics_In_Tech.docx",
        extension=".docx",
        size_bytes=4096,
        created_at="2026-10-20T00:00:00Z",
        modified_at="2026-10-20T00:00:00Z",
        preview_snippet="An argumentative essay examining ethical considerations in algorithmic decision-making and privacy.",
        is_supported_content=True
    )
    category, proposed_name, subfolder, explanation = deterministic_classify(meta)
    assert category == "Documents"
    assert "matched keyword: 'essay'" in explanation
    assert subfolder == "Documents"

def test_check_ollama_status_offline_handling():
    status = check_ollama_status()
    assert isinstance(status, dict)
    assert "available" in status
    assert "models" in status
    assert "target_model_installed" in status
