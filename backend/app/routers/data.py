import uuid
from fastapi import APIRouter, BackgroundTasks

from ..schemas import GatherResponse, StatusResponse
from ..services.data_gatherer import run_gather_job, get_job_state

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/gather", response_model=GatherResponse)
async def gather_data(background_tasks: BackgroundTasks):
    state = get_job_state()
    if state["status"] == "running":
        return GatherResponse(message="Job already running", job_id=state["job_id"])

    job_id = str(uuid.uuid4())
    background_tasks.add_task(run_gather_job, job_id)
    return GatherResponse(message="Data gathering started", job_id=job_id)


@router.get("/status", response_model=StatusResponse)
async def get_status():
    state = get_job_state()
    return StatusResponse(
        job_id=state.get("job_id") or "",
        status=state.get("status", "idle"),
        total_malls=state.get("total_malls", 0),
        completed_malls=state.get("completed_malls", 0),
        current_mall=state.get("current_mall"),
        error=state.get("error"),
    )
