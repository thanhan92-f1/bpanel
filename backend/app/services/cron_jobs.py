"""
Cron Job Management Service.

Provides comprehensive cron job management with flexible scheduling options,
integration with system crontab, database tracking, and execution logging.
"""

import logging
import re
import shlex
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.util import get_next_run_time as apscheduler_next_run

from app.core.database import SessionLocal
from app.core.permissions import is_admin_role
from app.models.entities import CronJob, User
from app.services.shell import shell

logger = logging.getLogger("bpanel")

# Preset schedules
PRESET_SCHEDULES: Dict[str, str] = {
    "every_5_minutes": "*/5 * * * *",
    "every_10_minutes": "*/10 * * * *",
    "every_15_minutes": "*/15 * * * *",
    "every_30_minutes": "*/30 * * * *",
    "every_hour": "0 * * * *",
    "every_day_midnight": "0 0 * * *",
    "every_day_6am": "0 6 * * *",
    "every_day_noon": "0 12 * * *",
    "every_week_monday": "0 0 * * 1",
    "every_week_sunday": "0 0 * * 0",
    "every_month_first": "0 0 1 * *",
    "every_month_fifteenth": "0 0 15 * *",
}

# Schedule builder options for UI
SCHEDULE_TYPES: Dict[str, Dict] = {
    "minute": {"every": [1, 5, 10, 15, 30]},
    "hourly": {"minute": list(range(0, 60)), "every_hours": [1, 2, 3, 6, 12]},
    "daily": {"hour": list(range(0, 24)), "minute": list(range(0, 60))},
    "weekly": {
        "day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "hour": list(range(0, 24)),
        "minute": list(range(0, 60)),
    },
    "monthly": {
        "day": list(range(1, 32)),
        "hour": list(range(0, 24)),
        "minute": list(range(0, 60)),
    },
}

# Cron field validation patterns
CRON_FIELD_RE = re.compile(r"^(?:\*|\*/\d+|\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)$")

# Weekday mapping (cron uses 0=Sunday, Python uses 0=Monday)
WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# Reverse mapping for output
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _validate_cron_field(field: str, field_name: str, min_val: int, max_val: int) -> str:
    """Validate a single cron field."""
    if not CRON_FIELD_RE.match(field):
        raise ValueError(f"Invalid {field_name} field: {field}")
    return field


def _sanitize_command(command: str) -> str:
    """Sanitize cron command to prevent command injection."""
    # Block dangerous patterns
    dangerous_patterns = [
        r';\s*rm\s', r';\s*del\s', r'&\s*rm\s', r'\|\s*rm\s',
        r';\s*cat\s', r'&\s*cat\s', r'\|\s*cat\s',
        r';\s*wget\s', r';\s*curl\s',
        r';\s*nc\s', r'&\s*nc\s', r'\|\s*nc\s',
        r';\s*bash\s', r'&\s*bash\s', r'\|\s*bash\s',
        r';\s*sh\s', r'&\s*sh\s', r'\|\s*sh\s',
        r'>\s*/etc/', r'>\s*/var/', r'>\s*/root/',
        r'<\s*/etc/passwd',
        r';\s*chmod\s+0', r';\s*chmod\s+7',
        r';\s*useradd', r';\s*adduser',
        r'eval\s*\(', r'exec\s*\(',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            raise ValueError("Command contains dangerous patterns")

    # Allow only safe characters
    safe_pattern = r'^[\w\s\/\-\.\,\:\'\"|\<\>\=\+\*\?\!\@\#\$\%\^\&\(\)\[\]\{\}\~\`\$\{\}\\\\]+$'
    if not re.match(safe_pattern, command):
        # Allow basic shell features but validate
        if not re.match(r'^[\w\s\/\-\.\,\:\'\"|\<\>\=\+\*\?\!\@\#\$\%\^\&\(\)\[\]\{\}\~\`]+$', command):
            raise ValueError("Command contains unsafe characters")

    return command

    # Check step values
    if "/" in field:
        base, step = field.split("/", 1)
        if base != "*":
            try:
                val = int(base)
                if val < min_val or val > max_val:
                    raise ValueError(f"{field_name} value {val} out of range ({min_val}-{max_val})")
            except ValueError:
                raise ValueError(f"Invalid {field_name} range: {base}")
        try:
            step_val = int(step)
            if step_val < 1:
                raise ValueError(f"{field_name} step must be positive")
        except ValueError:
            raise ValueError(f"Invalid {field_name} step: {step}")

    # Check range values
    if "-" in field and "/" not in field:
        parts = field.split(",")
        for part in parts:
            if "-" in part:
                start, end = part.split("-", 1)
                try:
                    s, e = int(start), int(end)
                    if s < min_val or s > max_val or e < min_val or e > max_val:
                        raise ValueError(f"{field_name} range ({s}-{e}) out of bounds ({min_val}-{max_val})")
                    if s > e:
                        raise ValueError(f"{field_name} range start ({s}) greater than end ({e})")
                except ValueError as exc:
                    raise ValueError(f"Invalid {field_name} range: {part}") from exc

    # Check specific values
    if "/" not in field and "-" not in field and field != "*":
        parts = field.split(",")
        for part in parts:
            try:
                val = int(part)
                if val < min_val or val > max_val:
                    raise ValueError(f"{field_name} value {val} out of range ({min_val}-{max_val})")
            except ValueError:
                raise ValueError(f"Invalid {field_name} value: {part}")

    return field


def parse_cron_expression(expression: str) -> dict:
    """
    Parse a cron expression into its components.

    Returns a dictionary with:
    - minute, hour, day, month, weekday: the parsed fields
    - is_valid: boolean indicating if the expression is valid
    - error: error message if invalid
    """
    result = {
        "minute": None,
        "hour": None,
        "day": None,
        "month": None,
        "weekday": None,
        "is_valid": False,
        "error": None,
    }

    if not expression:
        result["error"] = "Expression is empty"
        return result

    fields = expression.strip().split()
    if len(fields) != 5:
        result["error"] = f"Expected 5 fields, got {len(fields)}"
        return result

    try:
        result["minute"] = _validate_cron_field(fields[0], "minute", 0, 59)
        result["hour"] = _validate_cron_field(fields[1], "hour", 0, 23)
        result["day"] = _validate_cron_field(fields[2], "day", 1, 31)
        result["month"] = _validate_cron_field(fields[3], "month", 1, 12)
        result["weekday"] = _validate_cron_field(fields[4], "weekday", 0, 7)  # 0 and 7 both mean Sunday
        result["is_valid"] = True
    except ValueError as exc:
        result["error"] = str(exc)

    return result


def generate_cron_schedule(schedule_type: str, options: dict) -> str:
    """
    Generate a cron schedule string from schedule type and options.

    schedule_type: "minute", "hourly", "daily", "weekly", "monthly"
    options: dict containing schedule-specific options

    Returns a cron expression string.
    """
    if schedule_type == "minute":
        every = options.get("every", 5)
        if every not in [1, 5, 10, 15, 30]:
            raise ValueError("minute schedule 'every' must be one of: 1, 5, 10, 15, 30")
        return f"*/{every} * * * *"

    elif schedule_type == "hourly":
        minute = options.get("minute", 0)
        if not isinstance(minute, int) or minute < 0 or minute > 59:
            raise ValueError("hourly schedule 'minute' must be 0-59")
        every_hours = options.get("every_hours")
        if every_hours:
            if every_hours not in [1, 2, 3, 6, 12]:
                raise ValueError("hourly schedule 'every_hours' must be one of: 1, 2, 3, 6, 12")
            return f"0 */{every_hours} * * *"
        return f"{minute} * * * *"

    elif schedule_type == "daily":
        hour = options.get("hour", 0)
        minute = options.get("minute", 0)
        if not isinstance(hour, int) or hour < 0 or hour > 23:
            raise ValueError("daily schedule 'hour' must be 0-23")
        if not isinstance(minute, int) or minute < 0 or minute > 59:
            raise ValueError("daily schedule 'minute' must be 0-59")
        return f"{minute} {hour} * * *"

    elif schedule_type == "weekly":
        day = options.get("day", "Monday").lower()
        if day not in WEEKDAY_MAP:
            raise ValueError(f"weekly schedule 'day' must be one of: {', '.join(WEEKDAY_NAMES)}")
        hour = options.get("hour", 0)
        minute = options.get("minute", 0)
        if not isinstance(hour, int) or hour < 0 or hour > 23:
            raise ValueError("weekly schedule 'hour' must be 0-23")
        if not isinstance(minute, int) or minute < 0 or minute > 59:
            raise ValueError("weekly schedule 'minute' must be 0-59")
        cron_weekday = (WEEKDAY_MAP[day] + 1) % 7  # Convert to cron format (0=Sunday)
        return f"{minute} {hour} * * {cron_weekday}"

    elif schedule_type == "monthly":
        day = options.get("day", 1)
        if not isinstance(day, int) or day < 1 or day > 31:
            raise ValueError("monthly schedule 'day' must be 1-31")
        hour = options.get("hour", 0)
        minute = options.get("minute", 0)
        if not isinstance(hour, int) or hour < 0 or hour > 23:
            raise ValueError("monthly schedule 'hour' must be 0-23")
        if not isinstance(minute, int) or minute < 0 or minute > 59:
            raise ValueError("monthly schedule 'minute' must be 0-59")
        return f"{minute} {hour} {day} * *"

    else:
        raise ValueError(f"Unknown schedule type: {schedule_type}")


def get_next_run_time(schedule: str) -> Optional[datetime]:
    """
    Calculate the next run time for a cron schedule.

    Returns a datetime object for the next scheduled run,
    or None if the schedule is invalid.
    """
    parsed = parse_cron_expression(schedule)
    if not parsed["is_valid"]:
        return None

    try:
        # Use APScheduler's cron trigger for accurate next run calculation
        fields = schedule.split()
        hour = fields[1]
        minute = fields[0]
        day = fields[2]
        month = fields[3]
        weekday = fields[4]

        # Simple calculation for common cases
        now = datetime.now()
        result = _calculate_next_run_simple(now, minute, hour, day, month, weekday)
        return result
    except Exception as exc:
        logger.warning(f"Failed to calculate next run time: {exc}")
        return None


def _calculate_next_run_simple(
    now: datetime,
    minute: str,
    hour: str,
    day: str,
    month: str,
    weekday: str
) -> datetime:
    """Simple next run time calculation."""
    # Handle step values for minute
    if minute.startswith("*/"):
        minute_step = int(minute[2:])
        next_minute = ((now.minute // minute_step) + 1) * minute_step
        if next_minute >= 60:
            next_minute = minute_step
            delta_hours = 1 + (next_minute == 0 and minute_step == 0)
        else:
            delta_hours = 0
    else:
        next_minute = int(minute) if minute != "*" else now.minute
        delta_hours = 0

    # Handle step values for hour
    if hour.startswith("*/"):
        hour_step = int(hour[2:])
        next_hour = ((now.hour // hour_step) + 1) * hour_step
        if next_hour >= 24:
            next_hour = hour_step
            delta_days = 1 + (next_hour == 0 and hour_step == 0)
        else:
            delta_days = 0
    else:
        next_hour = int(hour) if hour != "*" else now.hour
        delta_days = 0

    # Simple case: minute only
    if hour == "*" and day == "*" and month == "*" and weekday == "*":
        result = now.replace(second=0, microsecond=0)
        if minute.startswith("*/"):
            minute_step = int(minute[2:])
            if now.minute % minute_step == 0:
                # Already on a multiple, add step
                result = result + timedelta(minutes=minute_step)
            else:
                # Find next multiple
                result = result + timedelta(minutes=minute_step - (now.minute % minute_step))
        else:
            target_minute = int(minute)
            if now.minute < target_minute:
                result = result.replace(minute=target_minute)
            else:
                result = result.replace(minute=target_minute) + timedelta(hours=1)
        return result

    # Daily case
    if day == "*" and month == "*" and weekday == "*":
        result = now.replace(second=0, microsecond=0)
        target_hour = int(hour) if hour != "*" else now.hour

        if minute.startswith("*/"):
            minute_step = int(minute[2:])
            result = result + timedelta(minutes=minute_step - (now.minute % minute_step))
            if result <= now:
                result = result + timedelta(hours=1)
        else:
            result = result.replace(minute=int(minute))

        if hour.startswith("*/"):
            hour_step = int(hour[2:])
            if result.hour % hour_step == 0 and result.minute == 0:
                pass  # Already aligned
            else:
                next_h = ((result.hour // hour_step) + 1) * hour_step
                if next_h >= 24:
                    next_h = hour_step
                result = result.replace(hour=next_h, minute=0)
                if result <= now:
                    result = result + timedelta(days=1)
        else:
            if result.hour < target_hour:
                result = result.replace(hour=target_hour)
            elif result.hour > target_hour:
                result = result.replace(hour=target_hour) + timedelta(days=1)
            else:
                # Same hour
                if minute.startswith("*/"):
                    minute_step = int(minute[2:])
                    if now.minute % minute_step == 0:
                        result = result + timedelta(minutes=minute_step)
                    else:
                        result = result + timedelta(minutes=minute_step - (now.minute % minute_step))
                    if result.hour != target_hour:
                        result = result.replace(hour=target_hour)

        if result <= now:
            result = result + timedelta(days=1)
        return result

    # For more complex cases, use a simple iteration
    result = now.replace(second=0, microsecond=0)
    for _ in range(366 * 24 * 60):  # Max 1 year of minutes
        result = result + timedelta(minutes=1)
        if _matches_cron(result, minute, hour, day, month, weekday):
            return result

    return None


def _matches_cron(dt: datetime, minute: str, hour: str, day: str, month: str, weekday: str) -> bool:
    """Check if a datetime matches a cron expression."""
    # Convert Python weekday (0=Monday) to cron weekday (0=Sunday)
    cron_weekday = (dt.weekday() + 1) % 7

    if not _field_matches(minute, dt.minute, 0, 59):
        return False
    if not _field_matches(hour, dt.hour, 0, 23):
        return False
    if not _field_matches(day, dt.day, 1, 31):
        return False
    if not _field_matches(month, dt.month, 1, 12):
        return False
    if not _field_matches(weekday, cron_weekday, 0, 7):
        return False

    return True


def _field_matches(field: str, value: int, min_val: int, max_val: int) -> bool:
    """Check if a cron field matches a value."""
    if field == "*":
        return True

    for part in field.split(","):
        part = part.strip()
        if not part:
            continue

        # Handle step
        step = 1
        if "/" in part:
            part, step_str = part.split("/", 1)
            step = int(step_str)
            if step < 1:
                continue

        # Handle range
        if part == "*":
            start, end = min_val, max_val
        elif "-" in part:
            start, end = part.split("-", 1)
            start, end = int(start), int(end)
        else:
            start = end = int(part)

        # Check if value matches
        if start <= value <= end and (value - start) % step == 0:
            return True

    return False


def get_next_runs(schedule: str, count: int = 5) -> List[datetime]:
    """
    Get the next N run times for a cron schedule.

    Returns a list of datetime objects.
    """
    runs = []
    next_time = get_next_run_time(schedule)

    while next_time and len(runs) < count:
        runs.append(next_time)
        # Simple increment for common cases
        parsed = parse_cron_expression(schedule)
        if not parsed["is_valid"]:
            break

        minute = parsed["minute"]
        if minute.startswith("*/"):
            step = int(minute[2:])
            next_time = next_time + timedelta(minutes=step)
        elif parsed["hour"].startswith("*/"):
            step = int(parsed["hour"][2:])
            next_time = next_time + timedelta(hours=step)
        elif parsed["day"] != "*":
            next_time = next_time + timedelta(days=1)
            # Reset to correct time
            parts = schedule.split()
            next_time = next_time.replace(
                hour=int(parts[1]) if parts[1] != "*" else 0,
                minute=int(parts[0]) if parts[0] != "*" else 0
            )
        elif parsed["weekday"] != "*":
            next_time = next_time + timedelta(days=1)
        else:
            next_time = next_time + timedelta(hours=1)

        # Prevent infinite loops
        if len(runs) > 0 and runs[-1] == next_time:
            break

    return runs


def _get_cron_marker(job_id: int) -> str:
    """Generate a unique marker for a cron job."""
    return f"# bpanel:job:{job_id}"


def _read_crontab(user: str = "root") -> str:
    """Read the current crontab for a user."""
    try:
        result = shell.privileged(
            "cron-list",
            helper_args=[user],
            check=False,
            fallback=["bash", "-lc", f"crontab -u {shlex.quote(user)} -l 2>/dev/null || true"],
        )
        return result.stdout or ""
    except Exception as exc:
        logger.warning(f"Failed to read crontab for {user}: {exc}")
        return ""


def _write_crontab(user: str, content: str) -> None:
    """Write content to a user's crontab."""
    try:
        shell.privileged(
            "cron-write",
            helper_args=[user],
            input=content,
            fallback=["bash", "-lc", f"crontab -u {shlex.quote(user)} - <<'EOF'\n{content}\nEOF"],
        )
    except Exception as exc:
        logger.error(f"Failed to write crontab for {user}: {exc}")
        raise


def _sync_crontab(user: str = "root") -> None:
    """Sync the system crontab with all enabled jobs from the database."""
    db = SessionLocal()
    try:
        jobs = db.query(CronJob).filter(
            CronJob.user == user,
            CronJob.enabled == True
        ).all()

        lines = []
        for job in jobs:
            marker = _get_cron_marker(job.id)
            line = f"{job.schedule} {job.command} {marker}"
            lines.append(line)

        content = "\n".join(lines) + ("\n" if lines else "")
        _write_crontab(user, content)
    finally:
        db.close()


def list_cron_jobs(user: str = "root") -> List[dict]:
    """List all cron jobs for a user."""
    db = SessionLocal()
    try:
        jobs = db.query(CronJob).filter(CronJob.user == user).order_by(CronJob.id.desc()).all()
        return [_job_to_dict(job) for job in jobs]
    finally:
        db.close()


def get_cron_job(job_id: int) -> Optional[dict]:
    """Get a single cron job by ID."""
    db = SessionLocal()
    try:
        job = db.query(CronJob).filter(CronJob.id == job_id).first()
        return _job_to_dict(job) if job else None
    finally:
        db.close()


def _job_to_dict(job: CronJob) -> dict:
    """Convert a CronJob model to a dictionary."""
    return {
        "id": job.id,
        "user": job.user,
        "command": job.command,
        "schedule": job.schedule,
        "description": job.description or "",
        "enabled": job.enabled,
        "last_run": job.last_run.isoformat() if job.last_run else None,
        "next_run": job.next_run.isoformat() if job.next_run else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def create_cron_job(user: str, command: str, schedule: str, description: str = "") -> dict:
    """
    Create a new cron job.

    Args:
        user: The Linux user for the cron job
        command: The command to execute
        schedule: Cron expression (e.g., "0 * * * *")
        description: Optional description

    Returns:
        The created job as a dictionary

    Raises:
        ValueError: If command or schedule is invalid.
    """
    # Validate the schedule
    parsed = parse_cron_expression(schedule)
    if not parsed["is_valid"]:
        raise ValueError(f"Invalid cron schedule: {parsed['error']}")

    # Basic command validation (prevent obvious issues)
    if not command or not command.strip():
        raise ValueError("Command is required")

    # Sanitize command to prevent command injection
    safe_command = _sanitize_command(command)

    db = SessionLocal()
    try:
        job = CronJob(
            user=user,
            command=safe_command,
            schedule=schedule,
            description=description,
            enabled=True,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Sync crontab
        _sync_crontab(user)

        return _job_to_dict(job)
    except Exception as exc:
        db.rollback()
        raise
    finally:
        db.close()


def update_cron_job(
    job_id: int,
    command: str = None,
    schedule: str = None,
    description: str = None,
    enabled: bool = None
) -> dict:
    """
    Update an existing cron job.

    Args:
        job_id: The job ID
        command: New command (optional)
        schedule: New schedule (optional)
        description: New description (optional)
        enabled: New enabled state (optional)

    Returns:
        The updated job as a dictionary

    Raises:
        ValueError: If job not found or parameters are invalid.
    """
    db = SessionLocal()
    try:
        job = db.query(CronJob).filter(CronJob.id == job_id).first()
        if not job:
            raise ValueError(f"Cron job {job_id} not found")

        if command is not None:
            if not command.strip():
                raise ValueError("Command cannot be empty")
            # Sanitize command to prevent command injection
            job.command = _sanitize_command(command)

        if schedule is not None:
            parsed = parse_cron_expression(schedule)
            if not parsed["is_valid"]:
                raise ValueError(f"Invalid cron schedule: {parsed['error']}")
            job.schedule = schedule

        if description is not None:
            job.description = description

        if enabled is not None:
            job.enabled = enabled

        db.commit()
        db.refresh(job)

        # Sync crontab
        _sync_crontab(job.user)

        return _job_to_dict(job)
    except Exception as exc:
        db.rollback()
        raise
    finally:
        db.close()


def delete_cron_job(job_id: int) -> dict:
    """
    Delete a cron job.

    Args:
        job_id: The job ID

    Returns:
        A confirmation dictionary
    """
    db = SessionLocal()
    try:
        job = db.query(CronJob).filter(CronJob.id == job_id).first()
        if not job:
            raise ValueError(f"Cron job {job_id} not found")

        user = job.user
        db.delete(job)
        db.commit()

        # Sync crontab
        _sync_crontab(user)

        return {"ok": True, "message": f"Cron job {job_id} deleted"}
    except Exception as exc:
        db.rollback()
        raise
    finally:
        db.close()


def toggle_cron_job(job_id: int, enabled: bool) -> dict:
    """
    Enable or disable a cron job.

    Args:
        job_id: The job ID
        enabled: True to enable, False to disable

    Returns:
        The updated job as a dictionary
    """
    return update_cron_job(job_id, enabled=enabled)


def get_cron_job_log(job_id: int, lines: int = 100) -> dict:
    """
    Get the execution log for a cron job.

    Args:
        job_id: The job ID
        lines: Number of log lines to retrieve

    Returns:
        A dictionary with log content
    """
    # Cron logs are typically in /var/log/syslog or /var/log/cron
    # The actual implementation depends on the system's cron setup
    log_paths = [
        "/var/log/syslog",
        "/var/log/cron",
        "/var/log/cron.log",
        "/var/log/messages",
    ]

    result = {
        "job_id": job_id,
        "lines": lines,
        "content": "",
        "exists": False,
    }

    marker = _get_cron_marker(job_id)

    # Try to find logs containing this job
    for log_path in log_paths:
        try:
            grep_result = shell.run(
                ["grep", "-a", marker, log_path],
                check=False,
            )
            if grep_result.returncode == 0:
                content = grep_result.stdout
                if content:
                    result["content"] = content
                    result["exists"] = True
                    result["source"] = log_path
                    break
        except Exception:
            continue

    # Also try journalctl for systemd systems
    try:
        journal_result = shell.run(
            ["journalctl", "-u", "cron", "--since", "7 days ago", "--no-pager"],
            check=False,
        )
        if journal_result.returncode == 0 and marker in journal_result.stdout:
            result["content"] = journal_result.stdout
            result["exists"] = True
            result["source"] = "journalctl"
    except Exception:
        pass

    # Limit lines
    if result["content"]:
        all_lines = result["content"].splitlines()
        result["content"] = "\n".join(all_lines[-lines:])

    return result


def run_cron_job_now(job_id: int) -> dict:
    """
    Run a cron job immediately.

    Args:
        job_id: The job ID

    Returns:
        A dictionary with execution result
    """
    db = SessionLocal()
    try:
        job = db.query(CronJob).filter(CronJob.id == job_id).first()
        if not job:
            raise ValueError(f"Cron job {job_id} not found")

        start_time = datetime.now()

        try:
            # Sanitize command before execution
            safe_command = _sanitize_command(job.command)

            # Execute the command
            result = shell.run(
                ["/bin/sh", "-c", safe_command],
                check=False,
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Update last run
            job.last_run = end_time

            db.commit()

            return {
                "job_id": job_id,
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_seconds": duration,
                "started_at": start_time.isoformat(),
                "ended_at": end_time.isoformat(),
            }
        except Exception as exc:
            job.last_run = datetime.now()
            db.commit()
            raise RuntimeError(f"Failed to execute job: {exc}")
    finally:
        db.close()


def list_user_crons(user: str) -> List[dict]:
    """
    List all cron jobs for a specific user.

    Args:
        user: The Linux username

    Returns:
        List of cron job dictionaries
    """
    return list_cron_jobs(user)
