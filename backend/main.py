import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import (
    init_db, save_scan_session, save_suggestions, get_recent_operations,
    update_suggestion_status, get_activity_stats, approve_suggestions,
    reject_suggestions, set_settings
)
from backend.models import (
    FolderScanRequest, FolderScanResponse,
    SuggestionBatchRequest, SuggestionBatchResponse,
    SuggestionApprovalRequest, SuggestionApprovalResponse,
    ExecuteActionsRequest, ExecuteActionsResponse,
    UndoRequest, UndoResponse,
    AIStatusResponse, ActivitySummaryResponse,
    EvaluationResult, SettingsUpdateRequest
)
from backend.scanner import scan_directory, create_sample_playground
from backend.ai_engine import (
    check_ollama_status, generate_suggestion_for_file
)
from backend.organizer import execute_batch_actions, undo_operation
from backend.lazy_summary import generate_lazy_morning_brief
from backend.evaluator import run_evaluation

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    init_db()
    # Load user-configured persistent settings from database
    settings.load_from_db()
    # Create sample playground directory for instant testing
    create_sample_playground()
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local-first AI file organization agent with safety controls, verification, and undo.",
    lifespan=lifespan
)

# Enable CORS for local Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "db": "connected" if settings.db_path.parent.exists() else "not_found"
    }

@app.get("/api/ai/status", response_model=AIStatusResponse)
def get_ai_status():
    ollama_info = check_ollama_status()
    is_available = ollama_info["available"]
    has_model = ollama_info["target_model_installed"]

    instructions = None
    if not is_available:
        instructions = (
            "Ollama service was not detected at " + settings.ollama_base_url + ".\n"
            "To enable local Gemma inference:\n"
            "1. Download & install Ollama from https://ollama.com\n"
            "2. Run in PowerShell: ollama pull " + settings.model_name + "\n"
            "3. SlothDesk AI will automatically detect the local model once running."
        )
    elif not has_model:
        instructions = (
            f"Ollama is running, but the configured model '{settings.model_name}' is not installed.\n"
            f"Run in PowerShell: ollama pull {settings.model_name}\n"
            f"Available models found: {', '.join(ollama_info['models']) if ollama_info['models'] else 'None'}"
        )

    return AIStatusResponse(
        ollama_available=is_available,
        ollama_url=settings.ollama_base_url,
        current_model=settings.model_name,
        model_available=has_model,
        available_models=ollama_info["models"],
        inference_mode="local_ollama" if (is_available and has_model) else "deterministic_fallback",
        offline_ready=True,
        privacy_guarantee="100% Local Inference. Document content and filenames never leave your machine.",
        setup_instructions=instructions
    )

@app.post("/api/scan", response_model=FolderScanResponse)
def scan_folder(request: FolderScanRequest):
    raw_path = Path(request.folder_path)
    if raw_path.is_symlink():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation: Scan root path cannot be a symlink: '{request.folder_path}'"
        )

    root_path = raw_path.resolve()
    if not root_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: '{request.folder_path}'. Please check the path."
        )

    try:
        files, duration_ms = scan_directory(
            root_dir_str=str(root_path),
            recursive=request.recursive,
            max_files=request.max_files or 200
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scanning failed: {str(e)}"
        )

    session_id = f"scan_{uuid.uuid4().hex[:8]}"
    save_scan_session(session_id, str(root_path), len(files))

    return FolderScanResponse(
        session_id=session_id,
        root_path=str(root_path),
        files_scanned=len(files),
        files=files,
        scan_duration_ms=round(duration_ms, 2)
    )

@app.post("/api/sample/create")
def create_sample_files():
    sample_dir = create_sample_playground()
    files, _ = scan_directory(str(sample_dir), recursive=True)
    return {
        "sample_dir": str(sample_dir),
        "created_files_count": len(files),
        "file_names": [f.filename for f in files]
    }

@app.post("/api/suggestions", response_model=SuggestionBatchResponse)
async def generate_suggestions(request: SuggestionBatchRequest):
    suggestions = []
    fallback_count = 0
    ai_count = 0
    total_latency = 0.0

    for file in request.files:
        sug = await generate_suggestion_for_file(
            file=file,
            session_id=request.session_id,
            custom_rules=request.custom_rules
        )
        suggestions.append(sug)
        total_latency += sug.latency_ms
        if sug.is_fallback:
            fallback_count += 1
        else:
            ai_count += 1

    # Persist in SQLite
    save_suggestions([s.model_dump() for s in suggestions])

    return SuggestionBatchResponse(
        session_id=request.session_id,
        suggestions=suggestions,
        model_used=settings.model_name if ai_count > 0 else "deterministic_rules",
        fallback_count=fallback_count,
        ai_count=ai_count,
        total_latency_ms=round(total_latency, 2)
    )

@app.post("/api/suggestions/approve", response_model=SuggestionApprovalResponse)
def approve_suggestions_endpoint(request: SuggestionApprovalRequest):
    approved_ids = approve_suggestions(request.suggestion_ids)
    return SuggestionApprovalResponse(
        status="approved",
        approved_ids=approved_ids,
        count=len(approved_ids)
    )

@app.post("/api/suggestions/reject", response_model=SuggestionApprovalResponse)
def reject_suggestions_endpoint(request: SuggestionApprovalRequest):
    rejected_ids = reject_suggestions(request.suggestion_ids)
    return SuggestionApprovalResponse(
        status="rejected",
        approved_ids=rejected_ids,
        count=len(rejected_ids)
    )

@app.post("/api/execute", response_model=ExecuteActionsResponse)
def execute_actions(request: ExecuteActionsRequest):
    raw_root = Path(request.root_path)
    if raw_root.is_symlink():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation: Execution root cannot be a symlink: {request.root_path}"
        )

    root_path = raw_root.resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid root path for execution: {request.root_path}"
        )

    succeeded, failed, results = execute_batch_actions(request.actions, str(root_path))
    return ExecuteActionsResponse(
        total_requested=len(request.actions),
        total_succeeded=succeeded,
        total_failed=failed,
        results=results
    )

@app.post("/api/undo", response_model=UndoResponse)
def undo_action(request: UndoRequest):
    return undo_operation(request.operation_id)

@app.get("/api/history")
def get_history(limit: int = 50):
    return {"operations": get_recent_operations(limit)}

@app.get("/api/summary", response_model=ActivitySummaryResponse)
def get_summary():
    return generate_lazy_morning_brief()

@app.post("/api/evaluate", response_model=EvaluationResult)
async def evaluate_classifier(force_deterministic: bool = False):
    return await run_evaluation(force_deterministic=force_deterministic)

@app.get("/api/settings")
def get_current_settings():
    return {
        "model_name": settings.model_name,
        "ollama_base_url": settings.ollama_base_url,
        "seconds_saved_per_file": settings.seconds_saved_per_file,
        "max_scan_files": settings.max_scan_files,
        "sample_dir": str(settings.sample_dir),
        "categories": settings.default_categories
    }

@app.post("/api/settings")
def update_settings(update: SettingsUpdateRequest):
    updates_to_persist = {}
    if update.model_name and update.model_name.strip():
        clean_model = update.model_name.strip()
        settings.model_name = clean_model
        updates_to_persist["model_name"] = clean_model

    if update.ollama_base_url and update.ollama_base_url.strip():
        clean_url = update.ollama_base_url.strip()
        if clean_url.startswith("http://") or clean_url.startswith("https://"):
            settings.ollama_base_url = clean_url
            updates_to_persist["ollama_base_url"] = clean_url

    if update.seconds_saved_per_file is not None:
        validated_sec = max(5, min(3600, int(update.seconds_saved_per_file)))
        settings.seconds_saved_per_file = validated_sec
        updates_to_persist["seconds_saved_per_file"] = str(validated_sec)

    if update.categories:
        settings.default_categories.update(update.categories)
        updates_to_persist["default_categories"] = settings.default_categories

    if updates_to_persist:
        set_settings(updates_to_persist)

    return {"status": "updated", "settings": get_current_settings()}

# Serve built frontend distribution if present
dist_path = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist_path.exists() and (dist_path / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="frontend-dist")
