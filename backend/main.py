
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import (
    init_db,
    save_scan_session,
    save_suggestions,
    get_recent_operations,
    update_suggestion_status,
    get_activity_stats,
    approve_suggestions as db_approve_suggestions,
    reject_suggestions as db_reject_suggestions,
    set_settings,
    get_scan_session,
    get_suggestion_by_id,
    get_operation_by_id,
)
from backend.models import (
    FolderScanRequest,
    FolderScanResponse,
    SuggestionBatchRequest,
    SuggestionBatchResponse,
    SuggestionApprovalRequest,
    SuggestionApprovalResponse,
    ExecuteActionsRequest,
    ExecuteActionsResponse,
    UndoRequest,
    UndoResponse,
    AIStatusResponse,
    ActivitySummaryResponse,
    EvaluationResult,
    SettingsUpdateRequest,
)
from backend.scanner import scan_directory, create_sample_playground
from backend.ai_engine import check_ollama_status, generate_suggestion_for_file
from backend.organizer import execute_batch_actions, undo_operation
from backend.lazy_summary import generate_lazy_morning_brief
from backend.evaluator import run_evaluation


def _sample_root() -> Path:
    """Return the canonical sample playground directory."""
    return settings.sample_dir.resolve()


def _is_inside(path: Path, root: Path) -> bool:
    """Return True only if the resolved path is root or a descendant of root."""
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
        return (
            resolved_path == resolved_root
            or resolved_root in resolved_path.parents
        )
    except (OSError, RuntimeError, ValueError):
        return False


def _require_demo_root(path_string: str) -> Path:
    """
    In demo mode, only allow the configured sample playground.
    Local mode keeps the existing user-selected-folder workflow.
    """
    raw_path = Path(path_string)

    if raw_path.is_symlink():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symlink paths are not allowed.",
        )

    resolved = raw_path.resolve()

    if settings.demo_mode:
        sample_root = _sample_root()
        if resolved != sample_root:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Public demo mode only allows the sample playground.",
            )

    if not resolved.exists() or not resolved.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected directory does not exist or is not a directory.",
        )

    return resolved


def _require_demo_suggestion(suggestion_id: str) -> dict[str, Any]:
    """In demo mode, only accept suggestions attached to the sample playground."""
    suggestion = get_suggestion_by_id(suggestion_id)
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found.",
        )

    if settings.demo_mode:
        session = get_scan_session(suggestion["session_id"])
        if not session or Path(session["root_dir"]).resolve() != _sample_root():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This suggestion is not part of the public sample demo.",
            )

    return suggestion


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.load_from_db()

    # Saved local settings must not override cloud demo model configuration.
    if settings.demo_mode:
        settings.model_name = os.getenv(
            "SLOTHDESK_MODEL",
            os.getenv("OLLAMA_MODEL", "gemma2:2b"),
        )
        settings.ollama_base_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434",
        )

    create_sample_playground()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Local-first AI file organization agent with safety controls, "
        "verification, and undo."
    ),
    lifespan=lifespan,
)

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
        "db": "connected" if settings.db_path.parent.exists() else "not_found",
        "demo_mode": settings.demo_mode,
    }


@app.get("/api/ai/status", response_model=AIStatusResponse)
def get_ai_status():
    ollama_info = check_ollama_status()
    is_available = ollama_info["available"]
    has_model = ollama_info["target_model_installed"]

    instructions = None

    if not is_available:
        if settings.demo_mode:
            instructions = (
                "The hosted demo does not have access to your computer's "
                "local Ollama service. Deterministic fallback suggestions "
                "may be used instead."
            )
        else:
            instructions = (
                "Ollama service was not detected at "
                + settings.ollama_base_url
                + ".\nTo enable local Gemma inference:\n"
                "1. Install Ollama from https://ollama.com\n"
                f"2. Run: ollama pull {settings.model_name}\n"
                "3. SlothDesk AI will detect the model when it is running."
            )
    elif not has_model:
        instructions = (
            f"Ollama is running, but '{settings.model_name}' is not installed.\n"
            f"Run: ollama pull {settings.model_name}\n"
            "Available models: "
            + (
                ", ".join(ollama_info["models"])
                if ollama_info["models"]
                else "None"
            )
        )

    return AIStatusResponse(
        ollama_available=is_available,
        ollama_url=settings.ollama_base_url,
        current_model=settings.model_name,
        model_available=has_model,
        available_models=ollama_info["models"],
        inference_mode=(
            "local_ollama"
            if is_available and has_model
            else "deterministic_fallback"
        ),
        offline_ready=not settings.demo_mode,
        privacy_guarantee=(
            "Hosted demo: only generated sample files should be used. "
            "Requests are processed by the hosted server."
            if settings.demo_mode
            else "Local inference is available when using local Ollama. "
            "Data handling depends on the selected inference mode."
        ),
        setup_instructions=instructions,
    )


@app.post("/api/scan", response_model=FolderScanResponse)
def scan_folder(request: FolderScanRequest):
    root_path = _require_demo_root(request.folder_path)

    try:
        files, duration_ms = scan_directory(
            root_dir_str=str(root_path),
            recursive=request.recursive,
            max_files=min(
                request.max_files or 200,
                settings.max_scan_files,
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scanning failed: {exc}",
        ) from exc

    session_id = f"scan_{uuid.uuid4().hex[:8]}"
    save_scan_session(session_id, str(root_path), len(files))

    return FolderScanResponse(
        session_id=session_id,
        root_path=str(root_path),
        files_scanned=len(files),
        files=files,
        scan_duration_ms=round(duration_ms, 2),
    )


@app.post("/api/sample/create")
def create_sample_files():
    sample_dir = create_sample_playground().resolve()
    files, _ = scan_directory(str(sample_dir), recursive=True)

    return {
        "sample_dir": str(sample_dir),
        "created_files_count": len(files),
        "file_names": [file.filename for file in files],
    }


@app.post("/api/suggestions", response_model=SuggestionBatchResponse)
async def generate_suggestions(request: SuggestionBatchRequest):
    session = get_scan_session(request.session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session not found. Scan the folder again.",
        )

    session_root = Path(session["root_dir"]).resolve()
    requested_root = Path(request.root_path)

    if requested_root.is_symlink():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symlink paths are not allowed.",
        )

    if requested_root.resolve() != session_root:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The requested root does not match the scan session.",
        )

    if settings.demo_mode and session_root != _sample_root():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public demo mode only allows the sample playground.",
        )

    # Do not trust client-supplied file metadata or snippets.
    # In demo mode, every file must be an existing regular file under sample_root.
    for file in request.files:
        file_path = Path(file.path)

        if file_path.is_symlink() or not _is_inside(file_path, session_root):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A requested file is outside the scanned folder.",
            )

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A requested file no longer exists.",
            )

        if settings.demo_mode:
            try:
                file_path.resolve().relative_to(_sample_root())
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Public demo mode only allows sample files.",
                ) from exc

    suggestions = []
    fallback_count = 0
    ai_count = 0
    total_latency = 0.0

    for file in request.files:
        suggestion = await generate_suggestion_for_file(
            file=file,
            session_id=request.session_id,
            custom_rules=request.custom_rules,
        )
        suggestions.append(suggestion)
        total_latency += suggestion.latency_ms

        if suggestion.is_fallback:
            fallback_count += 1
        else:
            ai_count += 1

    save_suggestions([item.model_dump() for item in suggestions])

    return SuggestionBatchResponse(
        session_id=request.session_id,
        suggestions=suggestions,
        model_used=(
            settings.model_name if ai_count > 0 else "deterministic_rules"
        ),
        fallback_count=fallback_count,
        ai_count=ai_count,
        total_latency_ms=round(total_latency, 2),
    )


@app.post("/api/suggestions/approve", response_model=SuggestionApprovalResponse)
def approve_suggestions_endpoint(request: SuggestionApprovalRequest):
    for suggestion_id in request.suggestion_ids:
        _require_demo_suggestion(suggestion_id)

    approved_ids = db_approve_suggestions(request.suggestion_ids)

    return SuggestionApprovalResponse(
        status="approved",
        approved_ids=approved_ids,
        count=len(approved_ids),
    )


@app.post("/api/suggestions/reject", response_model=SuggestionApprovalResponse)
def reject_suggestions_endpoint(request: SuggestionApprovalRequest):
    for suggestion_id in request.suggestion_ids:
        _require_demo_suggestion(suggestion_id)

    rejected_ids = db_reject_suggestions(request.suggestion_ids)

    return SuggestionApprovalResponse(
        status="rejected",
        approved_ids=rejected_ids,
        count=len(rejected_ids),
    )


@app.post("/api/execute", response_model=ExecuteActionsResponse)
def execute_actions(request: ExecuteActionsRequest):
    root_path = _require_demo_root(request.root_path)

    if settings.demo_mode:
        for action in request.actions:
            _require_demo_suggestion(action.id)

    succeeded, failed, results = execute_batch_actions(
        request.actions,
        str(root_path),
    )

    return ExecuteActionsResponse(
        total_requested=len(request.actions),
        total_succeeded=succeeded,
        total_failed=failed,
        results=results,
    )


@app.post("/api/undo", response_model=UndoResponse)
def undo_action(request: UndoRequest):
    if settings.demo_mode:
        operation = get_operation_by_id(request.operation_id)

        if not operation:
            return UndoResponse(
                operation_id=request.operation_id,
                success=False,
                message="Operation record not found.",
            )

        sample_root = _sample_root()
        original_path = Path(operation["original_path"])
        destination_path = Path(operation["destination_path"])

        if (
            not _is_inside(original_path, sample_root)
            or not _is_inside(destination_path, sample_root)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Public demo undo is restricted to sample playground files.",
            )

        suggestion_id = operation.get("suggestion_id")
        if suggestion_id:
            _require_demo_suggestion(suggestion_id)

    return undo_operation(request.operation_id)


@app.get("/api/history")
def get_history(limit: int = 50):
    safe_limit = max(1, min(limit, 100))
    operations = get_recent_operations(safe_limit)

    if settings.demo_mode:
        sample_root = _sample_root()
        operations = [
            operation
            for operation in operations
            if _is_inside(Path(operation["original_path"]), sample_root)
            and _is_inside(Path(operation["destination_path"]), sample_root)
        ]

    return {"operations": operations}


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
        "categories": settings.default_categories,
        "demo_mode": settings.demo_mode,
    }


@app.post("/api/settings")
def update_settings(update: SettingsUpdateRequest):
    updates_to_persist = {}

    # Public demo must not allow callers to change model or Ollama endpoint.
    if not settings.demo_mode:
        if update.model_name and update.model_name.strip():
            clean_model = update.model_name.strip()
            settings.model_name = clean_model
            updates_to_persist["model_name"] = clean_model

        if update.ollama_base_url and update.ollama_base_url.strip():
            clean_url = update.ollama_base_url.strip()
            if clean_url.startswith(("http://", "https://")):
                settings.ollama_base_url = clean_url
                updates_to_persist["ollama_base_url"] = clean_url

    if update.seconds_saved_per_file is not None:
        validated_seconds = max(5, min(3600, int(update.seconds_saved_per_file)))
        settings.seconds_saved_per_file = validated_seconds
        updates_to_persist["seconds_saved_per_file"] = str(validated_seconds)

    if update.categories and not settings.demo_mode:
        settings.default_categories.update(update.categories)
        updates_to_persist["default_categories"] = settings.default_categories

    if updates_to_persist:
        set_settings(updates_to_persist)

    return {"status": "updated", "settings": get_current_settings()}


# Serve the built frontend when frontend/dist/index.html exists.
dist_path = (
    Path(__file__).resolve().parent.parent / "frontend" / "dist"
)
if dist_path.exists() and (dist_path / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="frontend-dist")
