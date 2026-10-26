import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import pandas as pd
from backend.app.api.deps import event_broker
from backend.app.config import settings
from backend.app.db.repository import repo
from backend.app.graph.workflow import run_cleaning_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    dataset_id: str
    max_iterations: int = Field(default=3, ge=1, le=5)
    require_plan_approval: bool = False


class CreateRunResponse(BaseModel):
    run_id: str
    dataset_id: str
    status: str
    message: str


def execute_pipeline_in_background(run_id: str, file_path: str, max_iterations: int):
    """Background worker function executing the multi-agent graph."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def progress_callback(stage: str, iteration: int, msg: str):
        loop.run_until_complete(
            event_broker.broadcast_event(
                run_id=run_id,
                event_type="progress",
                data={"stage": stage, "iteration": iteration, "message": msg},
            )
        )

    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        state = run_cleaning_pipeline(
            df=df,
            run_id=run_id,
            max_iterations=max_iterations,
            progress_callback=progress_callback,
        )

        loop.run_until_complete(
            event_broker.broadcast_event(
                run_id=run_id,
                event_type="complete",
                data={"status": "completed", "final_score": state.get("final_score")},
            )
        )
    except Exception as e:
        logger.exception(f"Background execution failed for run {run_id}: {e}")
        repo.update_run(run_id, {"status": "failed", "error": str(e)})
        loop.run_until_complete(
            event_broker.broadcast_event(
                run_id=run_id,
                event_type="error",
                data={"status": "failed", "error": str(e)},
            )
        )
    finally:
        loop.close()


@router.post("", response_model=CreateRunResponse, status_code=status.HTTP_202_ACCEPTED)
def create_run(req: CreateRunRequest, background_tasks: BackgroundTasks):
    """Start an autonomous multi-agent cleaning run in a non-blocking background task."""
    dataset = repo.get_dataset(req.dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{req.dataset_id}' not found.",
        )

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    repo.create_run(run_id=run_id, dataset_id=req.dataset_id, max_iterations=req.max_iterations)

    background_tasks.add_task(
        execute_pipeline_in_background,
        run_id=run_id,
        file_path=dataset["file_path"],
        max_iterations=req.max_iterations,
    )

    return CreateRunResponse(
        run_id=run_id,
        dataset_id=req.dataset_id,
        status="queued",
        message="Autonomous cleaning pipeline queued in background.",
    )


@router.get("")
def list_runs(limit: int = Query(default=50, ge=1, le=100)):
    """List historical cleaning runs."""
    return repo.list_runs(limit=limit)


@router.get("/{run_id}")
def get_run(run_id: str):
    """Get status, current agent stage, scores, and timestamps of a run."""
    run = repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found.")
    return run


@router.get("/{run_id}/stream")
async def stream_run_events(run_id: str):
    """Server-Sent Events (SSE) stream for real-time pipeline progression."""
    run = repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found.")

    queue = event_broker.subscribe(run_id)

    async def event_generator():
        try:
            # Emit current status immediately upon connect
            initial_msg = f"event: connected\ndata: {{\"status\": \"{run.get('status')}\", \"stage\": \"{run.get('current_stage')}\"}}\n\n"
            yield initial_msg

            while True:
                msg = await queue.get()
                yield msg
                if "event: complete" in msg or "event: error" in msg:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            event_broker.unsubscribe(run_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{run_id}/issues")
def get_run_issues(run_id: str):
    """Retrieve detected data quality issues."""
    report = repo.get_report(run_id)
    if report and "remaining_issues" in report:
        return report.get("remaining_issues", [])
    # Check latest agent state snapshot
    states = repo.get_agent_states(run_id)
    for s in reversed(states):
        if "issues" in s.get("state", {}):
            return s["state"]["issues"]
    return []


@router.get("/{run_id}/plan")
def get_run_plan(run_id: str):
    """Retrieve cleaning plan and reasoning."""
    report = repo.get_report(run_id)
    if report:
        return {
            "operations": report.get("transformation_log", []),
            "total_operations": report.get("total_operations", 0),
        }
    return {"operations": []}


@router.get("/{run_id}/log")
def get_run_log(run_id: str):
    """Retrieve audit log of all transformations applied."""
    return repo.get_cleaning_logs(run_id)


@router.get("/{run_id}/report")
def get_run_report(run_id: str):
    """Retrieve comprehensive quality and narrative report."""
    report = repo.get_report(run_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for run '{run_id}' is not ready yet.",
        )
    return report


@router.get("/{run_id}/charts/{chart_name}")
def get_run_chart(run_id: str, chart_name: str):
    """Retrieve generated PNG chart by name."""
    clean_name = chart_name.replace(".png", "")
    chart_file = settings.OUTPUT_DIR / run_id / f"{clean_name}.png"
    if not chart_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chart '{chart_name}' not found for run '{run_id}'.",
        )
    return FileResponse(chart_file, media_type="image/png")


@router.get("/{run_id}/download")
def download_cleaned_dataset(run_id: str, format: str = Query(default="csv", pattern="^(csv|xlsx)$")):
    """Download cleaned dataset as CSV or Excel."""
    ext = format.lower()
    file_path = settings.OUTPUT_DIR / run_id / f"cleaned_dataset.{ext}"
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cleaned dataset in {format} format not found for run '{run_id}'.",
        )
    media_type = "text/csv" if ext == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(file_path, media_type=media_type, filename=f"cleaned_dataset_{run_id}.{ext}")
