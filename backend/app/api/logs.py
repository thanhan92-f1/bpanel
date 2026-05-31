"""
Logs API Router - Provides endpoints for log management.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.entities import User
from app.services import logs

router = APIRouter(prefix="/logs", tags=["logs"])


# =============================================================================
# Panel Logs
# =============================================================================

@router.get("/panel")
def get_panel_logs(
    lines: int = Query(default=100, ge=1, le=5000),
    level: str = Query(default=None, pattern="^(error|warning|info|debug)$"),
    current_user: User = Depends(get_current_user),
):
    """Get BPanel application logs."""
    return logs.get_panel_logs(lines=lines, level=level)


@router.get("/panel/errors")
def get_panel_error_logs(
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get BPanel error logs."""
    return logs.get_panel_error_logs(lines=lines)


@router.get("/panel/access")
def get_panel_access_logs(
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get BPanel access logs."""
    return logs.get_panel_access_logs(lines=lines)


# =============================================================================
# Website Logs
# =============================================================================

@router.get("/websites/{website_id}")
def get_website_logs(
    website_id: int,
    log_type: str = Query(default="access", pattern="^(access|error|ssl|php|fpm-slow)$"),
    lines: int = Query(default=100, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get website logs (access, error, ssl, php, fpm-slow)."""
    if log_type == "error":
        return logs.get_website_error_logs(website_id, lines, db)
    elif log_type == "ssl":
        return logs.get_website_ssl_logs(website_id, lines, db)
    elif log_type == "php":
        return logs.get_website_php_logs(website_id, lines, db)
    elif log_type == "fpm-slow":
        return logs.get_website_fpm_slow_logs(website_id, lines, db)
    else:
        return logs.get_website_logs(website_id, log_type, lines, db)


@router.get("/websites/{website_id}/access")
def get_website_access_logs(
    website_id: int,
    lines: int = Query(default=100, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get website access logs."""
    return logs.get_website_logs(website_id, "access", lines, db)


@router.get("/websites/{website_id}/error")
def get_website_error(
    website_id: int,
    lines: int = Query(default=100, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get website error logs."""
    return logs.get_website_error_logs(website_id, lines, db)


@router.get("/websites/{website_id}/ssl")
def get_website_ssl(
    website_id: int,
    lines: int = Query(default=100, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get website SSL logs."""
    return logs.get_website_ssl_logs(website_id, lines, db)


@router.get("/websites/{website_id}/php")
def get_website_php(
    website_id: int,
    lines: int = Query(default=100, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get PHP error logs for website."""
    return logs.get_website_php_logs(website_id, lines, db)


@router.get("/websites/{website_id}/fpm-slow")
def get_website_fpm_slow(
    website_id: int,
    lines: int = Query(default=100, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get PHP-FPM slow request logs."""
    return logs.get_website_fpm_slow_logs(website_id, lines, db)


# =============================================================================
# Audit Logs
# =============================================================================

@router.get("/audit")
def get_audit_logs(
    user_id: int = Query(default=None),
    action: str = Query(default=None),
    lines: int = Query(default=100, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get audit/action logs."""
    return logs.get_audit_logs(db, user_id=user_id, action=action, lines=lines)


@router.get("/audit/stats")
def get_audit_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get audit statistics."""
    return logs.get_audit_stats(db, days=days)


# =============================================================================
# SSH Logs
# =============================================================================

@router.get("/ssh")
def get_ssh_logs(
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get SSH login logs."""
    return logs.get_ssh_login_logs(lines=lines)


@router.get("/ssh/failed")
def get_failed_ssh(
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get failed SSH login attempts."""
    return logs.get_failed_ssh_logins(lines=lines)


@router.get("/ssh/successful")
def get_successful_ssh(
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get successful SSH login attempts."""
    return logs.get_successful_ssh_logins(lines=lines)


@router.get("/ssh/stats")
def get_ssh_stats(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
):
    """Get SSH login statistics."""
    return logs.get_ssh_login_stats(days=days)


# =============================================================================
# Soft Logs
# =============================================================================

@router.get("/system/updates")
def get_system_updates(
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get system update logs."""
    return logs.get_system_update_logs(lines=lines)


@router.get("/system/install")
def get_install_logs(
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get package installation logs."""
    return logs.get_install_logs(lines=lines)


@router.get("/system/service/{service}")
def get_service_logs(
    service: str,
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get logs for a systemd service."""
    return logs.get_service_logs(service, lines=lines)


@router.get("/docker")
def get_docker_logs(
    container: str = Query(default=None),
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get Docker container logs."""
    return logs.get_docker_logs(container=container, lines=lines)


@router.get("/mail")
def get_mail_logs(
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get mail server logs."""
    return logs.get_mail_logs(lines=lines)


@router.get("/cron")
def get_cron_logs(
    lines: int = Query(default=100, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
):
    """Get cron logs."""
    return logs.get_cron_logs(lines=lines)


# =============================================================================
# Management
# =============================================================================

@router.post("/search")
def search_logs_endpoint(
    query: str,
    log_type: str = Query(default="all", pattern="^(all|panel|audit|ssh|website)$"),
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search across logs."""
    return logs.search_logs(query, log_type, date_from, date_to, db)


@router.post("/rotate")
def rotate_logs_endpoint(
    current_user: User = Depends(get_current_user),
):
    """Rotate logs."""
    return logs.rotate_logs()


@router.post("/clear")
def clear_old_logs(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
):
    """Clear old log files."""
    return logs.clear_old_logs(days=days)


@router.get("/export")
def export_logs(
    log_type: str = Query(default="audit", pattern="^(audit|ssh|panel)$"),
    format: str = Query(default="txt", pattern="^(txt|json|csv)$"),
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export logs to specified format."""
    content = logs.export_logs(log_type, format, date_from, date_to, db)
    return {"content": content, "format": format, "log_type": log_type}
