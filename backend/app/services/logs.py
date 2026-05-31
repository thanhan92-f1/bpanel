"""
Logs Service - Centralized log management for BPanel.
Provides functions to read, search, and manage various log types.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import AuditLog, User
from app.services.shell import shell

# Panel log paths
PANEL_LOG_DIR = Path("/var/log/bpanel")
PANEL_MAIN_LOG = PANEL_LOG_DIR / "bpanel.log"
PANEL_ACCESS_LOG = PANEL_LOG_DIR / "access.log"
PANEL_ERROR_LOG = PANEL_LOG_DIR / "error.log"

# Nginx log path template
NGINX_LOG_DIR = Path("/var/log/nginx")


def _safe_read_log_file(path: Path, lines: int = 100) -> dict:
    """Read a log file and return structured data."""
    if not path.exists():
        return {
            "path": str(path),
            "content": "",
            "lines": lines,
            "exists": False,
            "error": f"Log file not found: {path}",
        }

    try:
        result = shell.run(
            ["tail", "-n", str(lines), str(path)],
            check=False
        )
        if result.returncode != 0:
            return {
                "path": str(path),
                "content": "",
                "lines": lines,
                "exists": True,
                "error": result.stderr or "Failed to read log file",
            }
        return {
            "path": str(path),
            "content": result.stdout or "",
            "lines": lines,
            "exists": True,
            "error": None,
        }
    except Exception as e:
        return {
            "path": str(path),
            "content": "",
            "lines": lines,
            "exists": True,
            "error": str(e),
        }


def _grep_log_file(path: Path, pattern: str, lines: int = 100) -> dict:
    """Grep a log file for a pattern."""
    if not path.exists():
        return {
            "path": str(path),
            "content": "",
            "matches": 0,
            "error": f"Log file not found: {path}",
        }

    try:
        result = shell.run(
            ["grep", "-E", pattern, str(path)] + (["tail", "-n", str(lines)] if lines else []),
            check=False
        )
        content = result.stdout or ""
        matches = len(content.splitlines()) if content else 0
        return {
            "path": str(path),
            "content": content,
            "matches": matches,
            "error": None,
        }
    except Exception as e:
        return {
            "path": str(path),
            "content": "",
            "matches": 0,
            "error": str(e),
        }


# =============================================================================
# Panel Logs
# =============================================================================

def get_panel_logs(lines: int = 100, level: str = None) -> dict:
    """Get BPanel application logs."""
    result = _safe_read_log_file(PANEL_MAIN_LOG, lines)

    if level and result.get("content"):
        level_pattern = _get_log_level_pattern(level)
        if level_pattern:
            lines_list = result["content"].splitlines()
            filtered = [l for l in lines_list if re.search(level_pattern, l, re.IGNORECASE)]
            result["content"] = "\n".join(filtered)

    return result


def get_panel_error_logs(lines: int = 100) -> dict:
    """Get BPanel error logs."""
    return _safe_read_log_file(PANEL_ERROR_LOG, lines)


def get_panel_access_logs(lines: int = 100) -> dict:
    """Get BPanel access logs."""
    return _safe_read_log_file(PANEL_ACCESS_LOG, lines)


def _get_log_level_pattern(level: str) -> Optional[str]:
    """Get regex pattern for log level."""
    patterns = {
        "error": r"\b(ERROR|FATAL|CRITICAL)\b",
        "warning": r"\b(WARN|WARNING)\b",
        "info": r"\b(INFO)\b",
        "debug": r"\b(DEBUG)\b",
    }
    return patterns.get(level.lower())


# =============================================================================
# Website Logs
# =============================================================================

def get_website_logs(website_id: int, log_type: str = "access", lines: int = 100, db: Session = None) -> dict:
    """Get website logs (access, error, ssl)."""
    from app.models.entities import Website

    if not db:
        return {"error": "Database session required", "content": ""}

    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        return {"error": "Website not found", "content": ""}

    domain = website.domain.lower().replace(".", "_")
    log_map = {
        "access": f"{domain}_access.log",
        "error": f"{domain}_error.log",
        "ssl": f"{domain}_ssl.log",
    }

    log_file = NGINX_LOG_DIR / log_map.get(log_type, f"{domain}_access.log")
    result = _safe_read_log_file(log_file, lines)
    result["domain"] = website.domain
    result["log_type"] = log_type
    return result


def get_website_error_logs(website_id: int, lines: int = 100, db: Session = None) -> dict:
    """Get website error logs."""
    return get_website_logs(website_id, "error", lines, db)


def get_website_ssl_logs(website_id: int, lines: int = 100, db: Session = None) -> dict:
    """Get website SSL logs."""
    return get_website_logs(website_id, "ssl", lines, db)


def get_website_php_logs(website_id: int, lines: int = 100, db: Session = None) -> dict:
    """Get PHP error logs for a website."""
    from app.models.entities import Website

    if not db:
        return {"error": "Database session required", "content": ""}

    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        return {"error": "Website not found", "content": ""}

    # PHP error log typically in /var/log/php*_fpm.log or site-specific location
    php_log = Path(f"/var/log/php{website.php_version}-fpm.log")
    result = _safe_read_log_file(php_log, lines)
    result["domain"] = website.domain
    result["log_type"] = "php"
    return result


def get_website_fpm_slow_logs(website_id: int, lines: int = 100, db: Session = None) -> dict:
    """Get PHP-FPM slow request logs."""
    from app.models.entities import Website

    if not db:
        return {"error": "Database session required", "content": ""}

    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        return {"error": "Website not found", "content": ""}

    # Slow log location varies by PHP version
    slow_log = Path(f"/var/log/php{website.php_version}-fpm-slow.log")
    result = _safe_read_log_file(slow_log, lines)
    result["domain"] = website.domain
    result["log_type"] = "fpm-slow"
    return result


# =============================================================================
# Audit Logs
# =============================================================================

def get_audit_logs(
    db: Session,
    user_id: int = None,
    action: str = None,
    lines: int = 100
) -> dict:
    """Get audit/action logs from database."""
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)

    logs = query.order_by(AuditLog.created_at.desc()).limit(lines).all()

    # Get user info for each log
    user_ids = set(log.user_id for log in logs if log.user_id)
    users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map = {u.id: u.username for u in users}

    entries = []
    for log in logs:
        entries.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": user_map.get(log.user_id, "System"),
            "action": log.action,
            "target": log.target,
            "detail": log.detail,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "logs": entries,
        "total": len(entries),
    }


def create_audit_log(
    db: Session,
    user_id: int,
    action: str,
    target: str,
    details: dict = None
) -> dict:
    """Create a new audit log entry."""
    detail = ""
    if details:
        detail = " | ".join(f"{k}={v}" for k, v in details.items())

    log = AuditLog(
        user_id=user_id,
        action=action,
        target=target,
        detail=detail,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "target": log.target,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def get_audit_stats(db: Session, days: int = 30) -> dict:
    """Get audit statistics."""
    since = datetime.utcnow() - timedelta(days=days)

    # Total actions in period
    total = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= since
    ).scalar() or 0

    # Actions by type
    by_action = db.query(
        AuditLog.action,
        func.count(AuditLog.id)
    ).filter(
        AuditLog.created_at >= since
    ).group_by(AuditLog.action).all()

    # Actions by user
    by_user = db.query(
        User.username,
        func.count(AuditLog.id)
    ).join(AuditLog).filter(
        AuditLog.created_at >= since
    ).group_by(User.username).all()

    # Recent activity (last 24h)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= yesterday
    ).scalar() or 0

    return {
        "period_days": days,
        "total_actions": total,
        "recent_actions": recent,
        "by_action": [{"action": a, "count": c} for a, c in by_action],
        "by_user": [{"username": u, "count": c} for u, c in by_user],
    }


# =============================================================================
# SSH Login Logs
# =============================================================================

def get_ssh_login_logs(lines: int = 100) -> dict:
    """Get SSH login attempts from auth.log."""
    auth_log = Path("/var/log/auth.log")

    # SSH login patterns
    pattern = r"sshd|Accepted|Failed|Invalid"
    result = shell.run(
        ["grep", "-E", pattern, str(auth_log)],
        check=False
    )

    # Tail to get last N lines
    lines_output = result.stdout or ""
    if lines_output:
        all_lines = lines_output.splitlines()
        lines_output = "\n".join(all_lines[-lines:])

    return {
        "path": str(auth_log),
        "content": lines_output,
        "lines": lines,
        "exists": auth_log.exists(),
    }


def get_failed_ssh_logins(lines: int = 100) -> dict:
    """Get failed SSH login attempts."""
    auth_log = Path("/var/log/auth.log")

    # Failed login pattern
    result = shell.run(
        ["grep", "-E", r"Failed password|Invalid user", str(auth_log)],
        check=False
    )

    lines_output = result.stdout or ""
    if lines_output:
        all_lines = lines_output.splitlines()
        lines_output = "\n".join(all_lines[-lines:])

    return {
        "path": str(auth_log),
        "content": lines_output,
        "type": "failed",
        "lines": lines,
        "exists": auth_log.exists(),
    }


def get_successful_ssh_logins(lines: int = 100) -> dict:
    """Get successful SSH login attempts."""
    auth_log = Path("/var/log/auth.log")

    # Successful login pattern
    result = shell.run(
        ["grep", "-E", r"Accepted", str(auth_log)],
        check=False
    )

    lines_output = result.stdout or ""
    if lines_output:
        all_lines = lines_output.splitlines()
        lines_output = "\n".join(all_lines[-lines:])

    return {
        "path": str(auth_log),
        "content": lines_output,
        "type": "successful",
        "lines": lines,
        "exists": auth_log.exists(),
    }


def get_ssh_login_stats(days: int = 30) -> dict:
    """Get SSH login statistics."""
    auth_log = Path("/var/log/auth.log")
    if not auth_log.exists():
        return {"error": "Auth log not found", "total": 0, "successful": 0, "failed": 0}

    # Count successful logins
    success_result = shell.run(
        ["grep", "-c", "Accepted", str(auth_log)],
        check=False
    )
    successful = int(success_result.stdout.strip() or 0) if success_result.returncode == 0 else 0

    # Count failed logins
    fail_result = shell.run(
        ["grep", "-cE", r"Failed password|Invalid user", str(auth_log)],
        check=False
    )
    failed = int(fail_result.stdout.strip() or 0) if fail_result.returncode == 0 else 0

    # Extract unique IPs from failed attempts
    ip_result = shell.run(
        ["grep", "-oE", r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", str(auth_log)],
        check=False
    )
    ip_output = ip_result.stdout or ""
    unique_ips = len(set(ip_output.split())) if ip_output else 0

    return {
        "total": successful + failed,
        "successful": successful,
        "failed": failed,
        "unique_ips": unique_ips,
        "path": str(auth_log),
    }


# =============================================================================
# Soft Logs (Software/Package Logs)
# =============================================================================

def get_system_update_logs(lines: int = 100) -> dict:
    """Get system update logs from apt."""
    apt_history = Path("/var/log/apt/history.log")
    apt_term = Path("/var/log/apt/term.log")

    # Try history.log first
    result = _safe_read_log_file(apt_history, lines)

    # If empty, try term.log
    if not result.get("content"):
        result = _safe_read_log_file(apt_term, lines)

    result["type"] = "system_update"
    return result


def get_install_logs(lines: int = 100) -> dict:
    """Get package installation logs."""
    dpkg_log = Path("/var/log/dpkg.log")
    apt_log = Path("/var/log/apt/term.log")

    # Try dpkg.log first
    result = _safe_read_log_file(dpkg_log, lines)

    # If empty, try apt term log
    if not result.get("content"):
        result = _safe_read_log_file(apt_log, lines)

    result["type"] = "install"
    return result


def get_service_logs(service: str, lines: int = 100) -> dict:
    """Get logs for a systemd service using journalctl."""
    try:
        result = shell.privileged(
            "journalctl",
            helper_args=["-u", service, "-n", str(lines), "--no-pager"],
            check=False,
            fallback=["journalctl", "-u", service, "-n", str(lines), "--no-pager"]
        )
        return {
            "service": service,
            "content": result.stdout or "",
            "lines": lines,
            "error": None if result.returncode == 0 else result.stderr,
        }
    except Exception as e:
        return {
            "service": service,
            "content": "",
            "lines": lines,
            "error": str(e),
        }


def get_docker_logs(container: str = None, lines: int = 100) -> dict:
    """Get Docker container logs."""
    try:
        args = ["docker", "logs"]
        if container:
            args.extend(["--name", container])
        else:
            args.append("--all")
        args.extend(["--tail", str(lines), "--no-pager"])

        result = shell.run(args, check=False)
        return {
            "container": container,
            "content": result.stdout or result.stderr or "",
            "lines": lines,
            "error": None if result.returncode == 0 else result.stderr,
        }
    except Exception as e:
        return {
            "container": container,
            "content": "",
            "lines": lines,
            "error": str(e),
        }


def get_mail_logs(lines: int = 100) -> dict:
    """Get mail server logs."""
    mail_log = Path("/var/log/mail.log")
    mail_error = Path("/var/log/mail.err")

    result = _safe_read_log_file(mail_log, lines)

    # Also get error log
    error_result = _safe_read_log_file(mail_error, lines)

    result["type"] = "mail"
    if error_result.get("content"):
        result["content"] += "\n\n--- Errors ---\n" + error_result["content"]

    return result


def get_cron_logs(lines: int = 100) -> dict:
    """Get cron logs."""
    # Cron logs often go to syslog
    result = shell.run(
        ["grep", "-E", "CRON|cron", "/var/log/syslog"],
        check=False
    )

    content = result.stdout or ""
    if content:
        all_lines = content.splitlines()
        content = "\n".join(all_lines[-lines:])

    return {
        "type": "cron",
        "content": content,
        "lines": lines,
        "exists": True,
    }


# =============================================================================
# Log Management
# =============================================================================

def search_logs(
    query: str,
    log_type: str = "all",
    date_from: str = None,
    date_to: str = None,
    db: Session = None
) -> dict:
    """Search across logs."""
    results = []

    if log_type in ("all", "panel"):
        panel_result = get_panel_logs(lines=1000)
        if panel_result.get("content"):
            results.append({
                "type": "panel",
                "path": panel_result.get("path"),
                "matches": _count_matches(panel_result["content"], query),
            })

    if log_type in ("all", "audit") and db:
        audit_result = get_audit_logs(db, lines=1000)
        matches = [l for l in audit_result.get("logs", []) if query.lower() in (
            f"{l.get('action', '')} {l.get('target', '')} {l.get('detail', '')}".lower()
        )]
        results.append({
            "type": "audit",
            "matches": matches,
            "count": len(matches),
        })

    if log_type in ("all", "ssh"):
        ssh_result = get_ssh_login_logs(lines=1000)
        if ssh_result.get("content"):
            results.append({
                "type": "ssh",
                "path": ssh_result.get("path"),
                "matches": _count_matches(ssh_result["content"], query),
            })

    return {
        "query": query,
        "log_type": log_type,
        "results": results,
    }


def _count_matches(content: str, pattern: str) -> int:
    """Count regex matches in content."""
    try:
        return len(re.findall(pattern, content, re.IGNORECASE))
    except re.error:
        # If invalid regex, do simple string search
        return content.lower().count(pattern.lower())


def rotate_logs() -> dict:
    """Rotate logs using logrotate."""
    try:
        result = shell.privileged(
            "logrotate",
            helper_args=["-f", "/etc/logrotate.conf"],
            check=False,
            fallback=["logrotate", "-f", "/etc/logrotate.conf"]
        )
        return {
            "success": result.returncode == 0,
            "message": "Log rotation completed" if result.returncode == 0 else result.stderr,
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


def clear_old_logs(days: int = 30) -> dict:
    """Clear old log files older than specified days."""
    try:
        # Find and remove old log files
        result = shell.run(
            ["find", "/var/log", "-name", "*.log", "-mtime", f"+{days}", "-type", "f"],
            check=False
        )

        old_files = result.stdout.strip().split("\n") if result.stdout else []
        deleted = []
        errors = []

        for f in old_files:
            if f and not f.startswith("/var/log/"):
                # Only delete from safe directories
                try:
                    shell.run(["rm", "-f", f], check=False)
                    deleted.append(f)
                except Exception as e:
                    errors.append(f"{f}: {str(e)}")

        return {
            "success": True,
            "deleted_count": len(deleted),
            "deleted_files": deleted,
            "errors": errors,
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


def export_logs(
    log_type: str,
    format: str = "txt",
    date_from: str = None,
    date_to: str = None,
    db: Session = None
) -> str:
    """Export logs to specified format."""
    content = ""

    if log_type == "audit" and db:
        logs = get_audit_logs(db, lines=10000)
        if format == "json":
            import json
            content = json.dumps(logs.get("logs", []), indent=2)
        elif format == "csv":
            lines = ["ID,User,Action,Target,Detail,Created At"]
            for log in logs.get("logs", []):
                lines.append(f"{log['id']},{log['username']},{log['action']},{log['target']},{log['detail']},{log['created_at']}")
            content = "\n".join(lines)
        else:
            for log in logs.get("logs", []):
                content += f"[{log['created_at']}] {log['username']}: {log['action']} - {log['target']}\n"

    elif log_type == "ssh":
        ssh_logs = get_ssh_login_logs(lines=10000)
        content = ssh_logs.get("content", "")

    else:
        panel_logs = get_panel_logs(lines=10000)
        content = panel_logs.get("content", "")

    return content
