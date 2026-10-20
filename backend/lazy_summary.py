from backend.config import settings
from backend.database import get_activity_stats, get_recent_operations
from backend.models import ActivitySummaryResponse

def generate_lazy_morning_brief() -> ActivitySummaryResponse:
    """
    Generates a clear, honest, data-backed summary of past activity
    and calculates estimated time saved.
    """
    stats = get_activity_stats()
    recent = get_recent_operations(10)

    total_scanned = stats["total_files_scanned"]
    pending = stats["pending_suggestions"]
    executed = stats["executed_operations"]
    undone = stats["undone_operations"]
    failed = stats["failed_operations"]

    # Calculation of estimated time saved:
    # Manual file review, renaming, destination subfolder creation, and moving
    # takes an estimated 45 seconds per file (configurable).
    sec_per_file = settings.seconds_saved_per_file
    est_seconds = executed * sec_per_file
    est_minutes = round(est_seconds / 60.0, 1)

    formula_explanation = (
        f"Estimate based on {sec_per_file} seconds saved per executed file action "
        f"({executed} files moved/renamed × {sec_per_file}s = {est_seconds}s). "
        "Accounts for manual inspection, category sorting, directory creation, and renaming."
    )

    if executed == 0 and pending == 0 and total_scanned == 0:
        brief_text = (
            "🦥 Good morning! Everything is quiet and peaceful. "
            "No folders have been scanned yet. Select a messy folder or click 'Try Sample Messy Folder' "
            "to let SlothDesk AI do the heavy lifting while you take it slow."
        )
    elif executed > 0 and pending == 0:
        brief_text = (
            f"🦥 Steady progress! You have organized {executed} file(s) across your workspaces, "
            f"saving approximately {est_minutes} minutes of mundane desktop housekeeping. "
            f"All pending suggestions are resolved, and no conflicts are blocking your workspace."
        )
    elif pending > 0:
        brief_text = (
            f"🦥 Work is ready for review: {pending} suggested action(s) are waiting in your approval queue. "
            f"So far, {executed} file(s) have been safely filed away (saving ~{est_minutes} mins). "
            f"Take a sip of coffee, review the suggestions at your leisure, and approve them with one click."
        )
    else:
        brief_text = (
            f"🦥 Scan session completed: {total_scanned} files inspected. "
            f"Your approval queue is up to date."
        )

    if failed > 0:
        brief_text += f" (Note: {failed} action(s) were safely blocked or failed safety checks; view activity history for details)."

    return ActivitySummaryResponse(
        total_scans=stats["total_scans"],
        total_files_scanned=total_scanned,
        pending_suggestions=pending,
        executed_operations=executed,
        undone_operations=undone,
        failed_operations=failed,
        estimated_seconds_saved=est_seconds,
        estimated_minutes_saved=est_minutes,
        time_saved_formula_explanation=formula_explanation,
        lazy_morning_brief=brief_text
    )
