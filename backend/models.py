from typing import Optional
from pydantic import BaseModel, Field

class FileMetadata(BaseModel):
    path: str
    filename: str
    relative_path: str
    extension: str
    size_bytes: int
    created_at: str
    modified_at: str
    preview_snippet: Optional[str] = None
    is_supported_content: bool = False

class FolderScanRequest(BaseModel):
    folder_path: str = Field(..., description="Absolute or normalized local path to scan")
    recursive: bool = True
    max_files: Optional[int] = Field(default=200, ge=1, le=1000)

class FolderScanResponse(BaseModel):
    session_id: str
    root_path: str
    files_scanned: int
    files: list[FileMetadata]
    scan_duration_ms: float

class SuggestionItem(BaseModel):
    id: str
    session_id: Optional[str] = None
    original_path: str
    original_filename: str
    proposed_filename: str
    category: str
    proposed_rel_path: str
    explanation: str
    is_fallback: bool
    model_used: str
    confidence: float = 0.95
    latency_ms: float = 0.0
    status: str = "pending"
    source_size_bytes: int = 0
    source_mtime: float = 0.0

class SuggestionBatchRequest(BaseModel):
    session_id: str
    root_path: str
    files: list[FileMetadata]
    custom_rules: Optional[dict[str, str]] = None

class SuggestionBatchResponse(BaseModel):
    session_id: str
    suggestions: list[SuggestionItem]
    model_used: str
    fallback_count: int
    ai_count: int
    total_latency_ms: float

class SuggestionApprovalRequest(BaseModel):
    suggestion_ids: list[str]

class SuggestionApprovalResponse(BaseModel):
    status: str
    approved_ids: list[str]
    count: int

class ActionItem(BaseModel):
    id: str
    original_path: str
    proposed_filename: str
    category: str
    proposed_rel_path: str
    approved: bool = True

class ExecuteActionsRequest(BaseModel):
    root_path: str
    actions: list[ActionItem]

class ExecutedActionResult(BaseModel):
    action_id: str
    operation_id: str
    original_path: str
    destination_path: str
    success: bool
    error: Optional[str] = None

class ExecuteActionsResponse(BaseModel):
    total_requested: int
    total_succeeded: int
    total_failed: int
    results: list[ExecutedActionResult]

class UndoRequest(BaseModel):
    operation_id: str

class UndoResponse(BaseModel):
    operation_id: str
    success: bool
    restored_path: Optional[str] = None
    message: str

class AIStatusResponse(BaseModel):
    ollama_available: bool
    ollama_url: str
    current_model: str
    model_available: bool
    available_models: list[str]
    inference_mode: str
    offline_ready: bool
    privacy_guarantee: str
    setup_instructions: Optional[str] = None

class ActivitySummaryResponse(BaseModel):
    total_scans: int
    total_files_scanned: int
    pending_suggestions: int
    executed_operations: int
    undone_operations: int
    failed_operations: int
    estimated_seconds_saved: int
    estimated_minutes_saved: float
    time_saved_formula_explanation: str
    lazy_morning_brief: str

class EvaluationDatasetItem(BaseModel):
    filename: str
    extension: str
    snippet: str
    expected_category: str

class EvaluationResult(BaseModel):
    total_samples: int
    correct_classifications: int
    accuracy_percentage: float
    average_latency_ms: float
    model_tested: str
    is_fallback: bool
    details: list[dict]

class SettingsUpdateRequest(BaseModel):
    model_name: Optional[str] = None
    ollama_base_url: Optional[str] = None
    seconds_saved_per_file: Optional[int] = None
    categories: Optional[dict[str, str]] = None
