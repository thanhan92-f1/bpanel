"""
Cron Jobs API Router.

Provides REST API endpoints for managing cron jobs with flexible scheduling options.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, ensure_role, is_admin_role
from app.models.entities import CronJob, User
from app.services import cron_jobs
from app.services.audit import log_action

router = APIRouter(prefix="/cron", tags=["cron"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class CronJobCreate(BaseModel):
    """Schema for creating a new cron job."""
    user: str = Field(default="root", max_length=50)
    command: str = Field(min_length=1, max_length=10000)
    schedule: str = Field(min_length=9, max_length=100)  # Min: "* * * * *" (9 chars)
    description: str = Field(default="", max_length=255)

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, value: str) -> str:
        parsed = cron_jobs.parse_cron_expression(value)
        if not parsed["is_valid"]:
            raise ValueError(f"Invalid cron schedule: {parsed['error']}")
        return value


class CronJobUpdate(BaseModel):
    """Schema for updating an existing cron job."""
    command: Optional[str] = Field(default=None, max_length=10000)
    schedule: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    enabled: Optional[bool] = None

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        parsed = cron_jobs.parse_cron_expression(value)
        if not parsed["is_valid"]:
            raise ValueError(f"Invalid cron schedule: {parsed['error']}")
        return value


class CronJobToggle(BaseModel):
    """Schema for toggling a cron job."""
    enabled: bool


class CronJobOut(BaseModel):
    """Schema for cron job output."""
    id: int
    user: str
    command: str
    schedule: str
    description: str
    enabled: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class CronJobLogOut(BaseModel):
    """Schema for cron job log output."""
    job_id: int
    lines: int
    content: str
    exists: bool
    source: Optional[str] = None


class CronJobRunOut(BaseModel):
    """Schema for cron job run result."""
    job_id: int
    success: bool
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    started_at: str
    ended_at: str


class ScheduleParseOut(BaseModel):
    """Schema for parsed cron expression."""
    minute: Optional[str] = None
    hour: Optional[str] = None
    day: Optional[str] = None
    month: Optional[str] = None
    weekday: Optional[str] = None
    is_valid: bool
    error: Optional[str] = None


class ScheduleGenerateIn(BaseModel):
    """Schema for generating a schedule."""
    schedule_type: str = Field(description="Type: minute, hourly, daily, weekly, monthly")
    options: dict = Field(default_factory=dict)


class ScheduleGenerateOut(BaseModel):
    """Schema for generated schedule."""
    schedule: str
    description: str


class NextRunsOut(BaseModel):
    """Schema for next run times."""
    schedule: str
    runs: List[str]


class PresetSchedulesOut(BaseModel):
    """Schema for preset schedules."""
    presets: dict


class ScheduleValidateIn(BaseModel):
    """Schema for validating a schedule."""
    schedule: str


class ScheduleValidateOut(BaseModel):
    """Schema for validation result."""
    valid: bool
    error: Optional[str] = None
    parsed: Optional[ScheduleParseOut] = None


# ============================================================================
# Cron Jobs Endpoints
# ============================================================================

@router.get("/jobs", response_model=List[CronJobOut])
def list_cron_jobs(
    user: str = Query(default="root", max_length=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all cron jobs for a user.

    Admins can view any user's jobs.
    Regular users can only view their own jobs.
    """
    if not is_admin_role(current_user.role) and current_user.username != user:
        user = current_user.username

    jobs = cron_jobs.list_cron_jobs(user)
    return jobs


@router.get("/jobs/{job_id}", response_model=CronJobOut)
def get_cron_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific cron job by ID."""
    job = cron_jobs.get_cron_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Cron job not found")

    # Check permissions
    if not is_admin_role(current_user.role) and job["user"] != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")

    return job


@router.post("/jobs", response_model=CronJobOut, status_code=201)
def create_cron_job(
    payload: CronJobCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new cron job.

    Regular users can only create jobs for their own username.
    Admins can create jobs for any user.
    """
    # Validate user permission
    if not is_admin_role(current_user.role):
        payload.user = current_user.username

    try:
        job = cron_jobs.create_cron_job(
            user=payload.user,
            command=payload.command,
            schedule=payload.schedule,
            description=payload.description,
        )
        log_action(
            db,
            current_user.id,
            "create_cron_job",
            f"job:{job['id']} ({payload.description or payload.schedule})",
            request=request,
        )
        return job
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/jobs/{job_id}", response_model=CronJobOut)
def update_cron_job(
    job_id: int,
    payload: CronJobUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing cron job."""
    existing = cron_jobs.get_cron_job(job_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cron job not found")

    # Check permissions
    if not is_admin_role(current_user.role) and existing["user"] != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        job = cron_jobs.update_cron_job(
            job_id=job_id,
            command=payload.command,
            schedule=payload.schedule,
            description=payload.description,
            enabled=payload.enabled,
        )
        log_action(
            db,
            current_user.id,
            "update_cron_job",
            f"job:{job_id}",
            request=request,
        )
        return job
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/jobs/{job_id}")
def delete_cron_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a cron job."""
    existing = cron_jobs.get_cron_job(job_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cron job not found")

    # Check permissions
    if not is_admin_role(current_user.role) and existing["user"] != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        result = cron_jobs.delete_cron_job(job_id)
        log_action(
            db,
            current_user.id,
            "delete_cron_job",
            f"job:{job_id}",
            request=request,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/jobs/{job_id}/toggle", response_model=CronJobOut)
def toggle_cron_job(
    job_id: int,
    payload: CronJobToggle,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enable or disable a cron job."""
    existing = cron_jobs.get_cron_job(job_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cron job not found")

    # Check permissions
    if not is_admin_role(current_user.role) and existing["user"] != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        job = cron_jobs.toggle_cron_job(job_id, payload.enabled)
        log_action(
            db,
            current_user.id,
            "toggle_cron_job",
            f"job:{job_id} -> {'enabled' if payload.enabled else 'disabled'}",
            request=request,
        )
        return job
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/jobs/{job_id}/log", response_model=CronJobLogOut)
def get_cron_job_log(
    job_id: int,
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get the execution log for a cron job."""
    existing = cron_jobs.get_cron_job(job_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cron job not found")

    # Check permissions
    if not is_admin_role(current_user.role) and existing["user"] != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")

    return cron_jobs.get_cron_job_log(job_id, lines)


@router.post("/jobs/{job_id}/run", response_model=CronJobRunOut)
def run_cron_job_now(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a cron job immediately (on-demand)."""
    existing = cron_jobs.get_cron_job(job_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cron job not found")

    # Check permissions
    if not is_admin_role(current_user.role) and existing["user"] != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        result = cron_jobs.run_cron_job_now(job_id)
        log_action(
            db,
            current_user.id,
            "run_cron_job",
            f"job:{job_id}",
            request=request,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Schedule Endpoints
# ============================================================================

@router.get("/presets", response_model=PresetSchedulesOut)
def get_preset_schedules():
    """Get all available preset schedules."""
    return PresetSchedulesOut(
        presets=cron_jobs.PRESET_SCHEDULES,
    )


@router.get("/schedule-types")
def get_schedule_types():
    """Get schedule builder options for UI."""
    return {
        "types": cron_jobs.SCHEDULE_TYPES,
    }


@router.get("/schedules/next", response_model=NextRunsOut)
def get_next_runs(
    schedule: str = Query(..., min_length=9, max_length=100),
    count: int = Query(default=5, ge=1, le=100),
):
    """Get the next N run times for a schedule."""
    parsed = cron_jobs.parse_cron_expression(schedule)
    if not parsed["is_valid"]:
        raise HTTPException(status_code=400, detail=f"Invalid schedule: {parsed['error']}")

    runs = cron_jobs.get_next_runs(schedule, count)
    return NextRunsOut(
        schedule=schedule,
        runs=[r.isoformat() for r in runs],
    )


@router.post("/schedules/validate", response_model=ScheduleValidateOut)
def validate_schedule(payload: ScheduleValidateIn):
    """Validate a cron schedule expression."""
    parsed = cron_jobs.parse_cron_expression(payload.schedule)
    return ScheduleValidateOut(
        valid=parsed["is_valid"],
        error=parsed["error"],
        parsed=ScheduleParseOut(**parsed) if parsed["is_valid"] else None,
    )


@router.post("/schedules/generate", response_model=ScheduleGenerateOut)
def generate_schedule(payload: ScheduleGenerateIn):
    """Generate a cron schedule from schedule type and options."""
    try:
        schedule = cron_jobs.generate_cron_schedule(
            payload.schedule_type,
            payload.options,
        )
        # Generate a human-readable description
        description = _describe_schedule(payload.schedule_type, payload.options, schedule)
        return ScheduleGenerateOut(
            schedule=schedule,
            description=description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _describe_schedule(schedule_type: str, options: dict, schedule: str) -> str:
    """Generate a human-readable description of a schedule."""
    if schedule_type == "minute":
        every = options.get("every", 5)
        return f"Every {every} minute(s)"

    elif schedule_type == "hourly":
        minute = options.get("minute", 0)
        every_hours = options.get("every_hours")
        if every_hours:
            return f"Every {every_hours} hour(s) at minute {minute}"
        return f"Every hour at minute {minute}"

    elif schedule_type == "daily":
        hour = options.get("hour", 0)
        minute = options.get("minute", 0)
        time_str = f"{hour:02d}:{minute:02d}"
        return f"Daily at {time_str}"

    elif schedule_type == "weekly":
        day = options.get("day", "Monday")
        hour = options.get("hour", 0)
        minute = options.get("minute", 0)
        time_str = f"{hour:02d}:{minute:02d}"
        return f"Weekly on {day} at {time_str}"

    elif schedule_type == "monthly":
        day = options.get("day", 1)
        hour = options.get("hour", 0)
        minute = options.get("minute", 0)
        time_str = f"{hour:02d}:{minute:02d}"
        return f"Monthly on day {day} at {time_str}"

    return schedule


# ============================================================================
# User Crons Endpoint
# ============================================================================

@router.get("/users/{user}/jobs", response_model=List[CronJobOut])
def list_user_cron_jobs(
    user: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all cron jobs for a specific user.

    Regular users can only view their own jobs.
    Admins can view any user's jobs.
    """
    if not is_admin_role(current_user.role) and user != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")

    return cron_jobs.list_cron_jobs(user)
