from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:
    from app.orchestrator import run_pipeline
except ModuleNotFoundError:
    from orchestrator import run_pipeline

app = FastAPI(title="UNICC AI Safety Lab Upload API")

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
OUTPUTS_DIR = BASE_DIR / "outputs"
LOGS_DIR = BASE_DIR / "logs"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class SubmissionRequest(BaseModel):
    submission_id: str
    submitted_by: str
    agent_name: str
    agent_description: str
    use_case: str
    deployment_context: str
    selected_frameworks: list[str] = Field(default_factory=list)
    risk_focus: list[str] = Field(default_factory=list)
    submitted_evidence: list[dict[str, str]] = Field(default_factory=list)
    notes: str = ""


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "status": "ok",
        "message": "UNICC AI Safety Lab API is running",
        "endpoints": {
            "submit": "/submit",
            "docs": "/docs",
        },
        "artifacts_base_dir": str(OUTPUTS_DIR),
    }


@app.post("/submit")
async def submit_agent(request: SubmissionRequest) -> JSONResponse:
    submission_timestamp = datetime.now(UTC).isoformat()

    submission_artifact_dir = ARTIFACTS_DIR / request.submission_id
    submission_artifact_dir.mkdir(parents=True, exist_ok=True)

    input_data = {
        "submission_id": request.submission_id,
        "submitted_by": request.submitted_by,
        "submission_timestamp": submission_timestamp,
        "agent_name": request.agent_name,
        "agent_description": request.agent_description,
        "use_case": request.use_case,
        "deployment_context": request.deployment_context,
        "selected_frameworks": request.selected_frameworks,
        "risk_focus": request.risk_focus,
        "submitted_evidence": request.submitted_evidence,
        "notes": request.notes,
    }

    results = run_pipeline(input_data)

    submission_path = OUTPUTS_DIR / f"{request.submission_id}_submission.json"
    judge_output_paths = [
        OUTPUTS_DIR / f"{request.submission_id}_judge1_output.json",
        OUTPUTS_DIR / f"{request.submission_id}_judge2_output.json",
        OUTPUTS_DIR / f"{request.submission_id}_judge3_output.json",
    ]
    critique_round_path = OUTPUTS_DIR / f"{request.submission_id}_critique_round.json"
    synthesis_path = OUTPUTS_DIR / f"{request.submission_id}_synthesis_output.json"
    full_result_path = OUTPUTS_DIR / f"{request.submission_id}_full_result.json"
    log_path = LOGS_DIR / f"{request.submission_id}_pipeline_log.json"

    _write_json(submission_path, input_data)
    for path, judge_output in zip(judge_output_paths, results["judge_outputs"], strict=True):
        _write_json(path, judge_output)

    _write_json(critique_round_path, results["critique_round"])
    _write_json(synthesis_path, results["synthesis_output"])
    _write_json(full_result_path, results)

    artifact_map = {
        "submission": _relative_path(submission_path),
        "judge_outputs": [_relative_path(path) for path in judge_output_paths],
        "critique_round": _relative_path(critique_round_path),
        "synthesis_output": _relative_path(synthesis_path),
        "full_result": _relative_path(full_result_path),
        "log": _relative_path(log_path),
    }

    log_entry = {
        "timestamp": submission_timestamp,
        "submission_id": request.submission_id,
        "status": "completed",
        "saved_artifact_dir": str(submission_artifact_dir),
        "uploaded_files": [item["file_name"] for item in request.submitted_evidence],
        "generated_files": [
            Path(artifact_map["submission"]).name,
            *(Path(path).name for path in artifact_map["judge_outputs"]),
            Path(artifact_map["critique_round"]).name,
            Path(artifact_map["synthesis_output"]).name,
            Path(artifact_map["full_result"]).name,
        ],
        "artifact_map": artifact_map,
    }
    _write_json(log_path, log_entry)

    return JSONResponse(
        content={
            "message": "Submission received and pipeline completed",
            "submission": input_data,
            "results": results,
            "artifacts": artifact_map,
        }
    )
