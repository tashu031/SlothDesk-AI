import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ai_engine import classify_with_ollama, deterministic_classify, check_ollama_status
from backend.config import settings
from backend.models import FileMetadata, EvaluationDatasetItem, EvaluationResult

LABELED_EVAL_DATASET = [
    EvaluationDatasetItem(
        filename="CS101_Lecture05_Graphs_BFS_DFS.pdf",
        extension=".pdf",
        snippet="Breadth-First Search and Depth-First Search algorithms on directed acyclic graphs for computer science midterms.",
        expected_category="Study"
    ),
    EvaluationDatasetItem(
        filename="Draft_Essay_Ethics_In_Tech.docx",
        extension=".docx",
        snippet="An argumentative essay examining ethical considerations in algorithmic decision-making and privacy.",
        expected_category="Documents"
    ),
    EvaluationDatasetItem(
        filename="server_healthcheck_cron.py",
        extension=".py",
        snippet="import httpx\ndef check_services():\n    res = httpx.get('http://localhost:8000/api/health')\n    return res.status_code == 200",
        expected_category="Code"
    ),
    EvaluationDatasetItem(
        filename="Q4_financial_projections_2026.csv",
        extension=".csv",
        snippet="Month,ProjectedRevenue,ProjectedCost,EBITDA\nJan,45000,28000,17000\nFeb,48000,29000,19000",
        expected_category="Data"
    ),
    EvaluationDatasetItem(
        filename="screenshot_2026-10-18_at_14.22.png",
        extension=".png",
        snippet="",
        expected_category="Images"
    ),
    EvaluationDatasetItem(
        filename="biology_lab_report_osmosis_exp3.pdf",
        extension=".pdf",
        snippet="Biology Lab Report: Investigating osmotic rate in Solanum tuberosum cells across sucrose concentrations.",
        expected_category="Study"
    ),
    EvaluationDatasetItem(
        filename="invoice_apple_developer_program_2026.pdf",
        extension=".pdf",
        snippet="Tax Invoice: Apple Developer Program Annual Subscription Renewal. Total Paid $99.00 USD.",
        expected_category="Documents"
    ),
    EvaluationDatasetItem(
        filename="react_button_component.tsx",
        extension=".tsx",
        snippet="export const PrimaryButton = ({ label, onClick }: { label: string, onClick: () => void }) => <button>{label}</button>;",
        expected_category="Code"
    ),
    EvaluationDatasetItem(
        filename="customer_churn_analytics_raw.json",
        extension=".json",
        snippet='{"metrics": [{"cohort": "2026-Q1", "churn_rate": 0.042}]}',
        expected_category="Data"
    ),
    EvaluationDatasetItem(
        filename="project_assets_backup_october.zip",
        extension=".zip",
        snippet="",
        expected_category="Archives"
    )
]

async def run_evaluation(force_deterministic: bool = False) -> EvaluationResult:
    """
    Runs the benchmark evaluation against the labeled dataset.
    Uses Ollama Gemma if available and not forced to deterministic, otherwise falls back.
    Measures genuine latency and accuracy.
    """
    ollama_stat = check_ollama_status()
    use_ai = (not force_deterministic) and ollama_stat["available"] and ollama_stat["target_model_installed"]

    correct = 0
    total = len(LABELED_EVAL_DATASET)
    latencies = []
    details = []

    for item in LABELED_EVAL_DATASET:
        dummy_meta = FileMetadata(
            path=f"/sample/{item.filename}",
            filename=item.filename,
            relative_path=item.filename,
            extension=item.extension,
            size_bytes=1024,
            created_at="2026-10-20T00:00:00Z",
            modified_at="2026-10-20T00:00:00Z",
            preview_snippet=item.snippet,
            is_supported_content=bool(item.snippet)
        )

        if use_ai:
            t0 = time.perf_counter()
            res = await classify_with_ollama(dummy_meta)
            if res:
                predicted_cat, predicted_name, _, reason, lat = res
                is_correct = (predicted_cat.lower() == item.expected_category.lower())
                latencies.append(lat)
            else:
                # If specific call failed, fallback
                predicted_cat, predicted_name, _, reason = deterministic_classify(dummy_meta)
                lat = (time.perf_counter() - t0) * 1000.0
                is_correct = (predicted_cat.lower() == item.expected_category.lower())
                latencies.append(lat)
        else:
            t0 = time.perf_counter()
            predicted_cat, predicted_name, _, reason = deterministic_classify(dummy_meta)
            lat = (time.perf_counter() - t0) * 1000.0
            is_correct = (predicted_cat.lower() == item.expected_category.lower())
            latencies.append(lat)

        if is_correct:
            correct += 1

        details.append({
            "filename": item.filename,
            "expected_category": item.expected_category,
            "predicted_category": predicted_cat,
            "proposed_filename": predicted_name,
            "correct": is_correct,
            "latency_ms": round(lat, 2)
        })

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    accuracy = (correct / total) * 100.0 if total > 0 else 0.0

    return EvaluationResult(
        total_samples=total,
        correct_classifications=correct,
        accuracy_percentage=round(accuracy, 1),
        average_latency_ms=round(avg_latency, 2),
        model_tested=settings.model_name if use_ai else "deterministic_rules",
        is_fallback=(not use_ai),
        details=details
    )

if __name__ == "__main__":
    result = asyncio.run(run_evaluation())
    print(f"Model Tested: {result.model_tested}")
    print(f"Accuracy: {result.accuracy_percentage}% ({result.correct_classifications}/{result.total_samples})")
    print(f"Avg Latency: {result.average_latency_ms} ms")
    for d in result.details:
        status = "PASS" if d["correct"] else "FAIL"
        print(f"  [{status}] {d['filename']}: expected '{d['expected_category']}', got '{d['predicted_category']}' ({d['latency_ms']}ms)")
