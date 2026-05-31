"""
Comprehensive Settings API Router for BPanel.
Provides all settings endpoints including panel, network, SSL, auth, interface, backup, alarm, migration, and services.
"""
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.services import settings as settings_service
from app.services.audit import log_action

router = APIRouter(prefix="/settings", tags=["settings"])

# Asset upload settings
ASSETS_DIR = Path(os.environ.get("BPANEL_DATA_DIR", "/var/lib/bpanel")) / "assets"
MAX_ASSET_SIZE = 1024 * 1024


# =============================================================================
# Panel Settings
# =============================================================================

@router.get("")
def get_settings(
    current_user: User = Depends(get_current_user),
):
    """Get all panel settings."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_panel_settings()


@router.put("")
def update_settings(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Update panel settings."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.update_panel_settings(payload)
    log_action(get_db(), current_user.id, "update_settings", "settings", request=request)
    return result


# =============================================================================
# Network & Access
# =============================================================================

@router.get("/network")
def get_network_settings(
    current_user: User = Depends(get_current_user),
):
    """Get network settings."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_panel_access_info()


@router.put("/network/domain")
def set_domain(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Set panel domain."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.set_panel_domain(payload.get("domain", ""))
    log_action(get_db(), current_user.id, "set_panel_domain", payload.get("domain", ""), request=request)
    return result


@router.put("/network/port")
def set_port(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Set panel port."""
    ensure_role(current_user.role, Role.admin)
    port = payload.get("port", 2222)
    result = settings_service.set_panel_port(port)
    log_action(get_db(), current_user.id, "set_panel_port", str(port), request=request)
    return result


@router.put("/network/security-entrance")
def set_security_entrance(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Set security entrance path."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.set_security_entrance(payload.get("path", ""))
    log_action(get_db(), current_user.id, "set_security_entrance", payload.get("path", ""), request=request)
    return result


# =============================================================================
# Panel SSL
# =============================================================================

@router.get("/ssl")
def get_ssl(
    current_user: User = Depends(get_current_user),
):
    """Get panel SSL status."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_ssl_status()


@router.post("/ssl/setup")
def setup_ssl(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Setup panel SSL with certificate and key."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.setup_panel_ssl(
        payload.get("cert", ""),
        payload.get("key", "")
    )
    log_action(get_db(), current_user.id, "setup_panel_ssl", "panel_ssl", request=request)
    return result


@router.post("/ssl/renew")
def renew_ssl(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Renew panel SSL certificate."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.renew_panel_ssl()
    log_action(get_db(), current_user.id, "renew_panel_ssl", "panel_ssl", request=request)
    return result


@router.put("/ssl/toggle")
def toggle_ssl(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Enable or disable panel SSL."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.enable_panel_ssl(payload.get("enable", False))
    log_action(get_db(), current_user.id, "toggle_panel_ssl", str(payload.get("enable", False)), request=request)
    return result


# =============================================================================
# Developer Mode & API
# =============================================================================

@router.put("/developer-mode")
def toggle_developer_mode(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Enable or disable developer mode."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.enable_developer_mode(payload.get("enable", False))
    log_action(get_db(), current_user.id, "toggle_developer_mode", str(payload.get("enable", False)), request=request)
    return result


@router.put("/api")
def toggle_api(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Enable or disable API."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.enable_api(payload.get("enable", False))
    log_action(get_db(), current_user.id, "toggle_api", str(payload.get("enable", False)), request=request)
    return result


@router.get("/api/key")
def get_api_key(
    current_user: User = Depends(get_current_user),
):
    """Get API key."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_api_key()


@router.post("/api/reset-key")
def reset_api_key(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Reset API key."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.reset_api_key()
    log_action(get_db(), current_user.id, "reset_api_key", "api_key", request=request)
    return result


@router.get("/api/whitelist")
def get_api_whitelist(
    current_user: User = Depends(get_current_user),
):
    """Get API IP whitelist."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_api_whitelist()


@router.post("/api/whitelist")
def add_to_whitelist(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Add IP to API whitelist."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.add_api_whitelist(payload.get("ip", ""))
    log_action(get_db(), current_user.id, "add_api_whitelist", payload.get("ip", ""), request=request)
    return result


@router.delete("/api/whitelist/{ip}")
def remove_from_whitelist(
    ip: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Remove IP from API whitelist."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.remove_api_whitelist(ip)
    log_action(get_db(), current_user.id, "remove_api_whitelist", ip, request=request)
    return result


# =============================================================================
# Authentication & Security
# =============================================================================

@router.get("/auth")
def get_auth_settings(
    current_user: User = Depends(get_current_user),
):
    """Get authentication settings."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_auth_settings()


@router.put("/auth")
def update_auth_settings(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Update authentication settings."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.update_auth_settings(payload)
    log_action(get_db(), current_user.id, "update_auth_settings", "auth", request=request)
    return result


@router.post("/auth/basic-auth")
def setup_basic_auth(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Setup basic authentication."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.set_basic_auth(
        payload.get("username", ""),
        payload.get("password", "")
    )
    log_action(get_db(), current_user.id, "setup_basic_auth", "basic_auth", request=request)
    return result


@router.delete("/auth/basic-auth")
def disable_basic_auth(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Disable basic authentication."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.disable_basic_auth()
    log_action(get_db(), current_user.id, "disable_basic_auth", "basic_auth", request=request)
    return result


@router.post("/auth/google-auth")
def setup_google_auth(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Setup Google Authenticator."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.setup_google_auth(payload.get("secret", ""))
    log_action(get_db(), current_user.id, "setup_google_auth", "google_auth", request=request)
    return result


@router.delete("/auth/google-auth")
def disable_google_auth(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Disable Google Authenticator."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.disable_google_auth()
    log_action(get_db(), current_user.id, "disable_google_auth", "google_auth", request=request)
    return result


@router.put("/auth/strong-password")
def toggle_strong_password(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Enable or disable strong password requirement."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.enable_strong_password(payload.get("enable", False))
    log_action(get_db(), current_user.id, "toggle_strong_password", str(payload.get("enable", False)), request=request)
    return result


@router.put("/auth/authorized-ips")
def set_authorized_ips(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Set authorized IP addresses."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.set_authorized_ips(payload.get("ips", []))
    log_action(get_db(), current_user.id, "set_authorized_ips", "authorized_ips", request=request)
    return result


@router.put("/auth/password-expire")
def set_password_expire(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Set password expiration."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.set_password_expire(payload.get("days", 0))
    log_action(get_db(), current_user.id, "set_password_expire", str(payload.get("days", 0)), request=request)
    return result


# =============================================================================
# Interface Preferences
# =============================================================================

@router.get("/interface")
def get_interface_settings(
    current_user: User = Depends(get_current_user),
):
    """Get interface settings."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_interface_settings()


@router.put("/interface")
def update_interface_settings(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Update interface settings."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.update_interface_settings(payload)
    log_action(get_db(), current_user.id, "update_interface_settings", "interface", request=request)
    return result


@router.post("/interface/logo")
async def upload_logo(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload panel logo."""
    ensure_role(current_user.role, Role.admin)

    content = await file.read(MAX_ASSET_SIZE + 1)
    if len(content) > MAX_ASSET_SIZE:
        raise HTTPException(status_code=400, detail="Image must be 1 MB or smaller")

    # Validate image
    allowed_types = {".png", ".jpg", ".jpeg", ".webp", ".ico"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, WEBP, and ICO images are supported")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"logo{ext}"
    (ASSETS_DIR / filename).write_bytes(content)

    # Update settings
    import json
    from pathlib import Path
    SETTINGS_FILE = Path(os.environ.get("BPANEL_DATA_DIR", "/var/lib/bpanel")) / "panel-settings.json"

    data = {}
    if SETTINGS_FILE.exists():
        data = json.loads(SETTINGS_FILE.read_text())

    data["logo_filename"] = filename
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))

    log_action(get_db(), current_user.id, "upload_logo", "panel_logo", request=request)
    return {"success": True, "filename": filename}


@router.post("/interface/favicon")
async def upload_favicon(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload panel favicon."""
    ensure_role(current_user.role, Role.admin)

    content = await file.read(MAX_ASSET_SIZE + 1)
    if len(content) > MAX_ASSET_SIZE:
        raise HTTPException(status_code=400, detail="Image must be 1 MB or smaller")

    # Validate image
    allowed_types = {".png", ".jpg", ".jpeg", ".webp", ".ico"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, WEBP, and ICO images are supported")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"favicon{ext}"
    (ASSETS_DIR / filename).write_bytes(content)

    # Update settings
    import json
    from pathlib import Path
    SETTINGS_FILE = Path(os.environ.get("BPANEL_DATA_DIR", "/var/lib/bpanel")) / "panel-settings.json"

    data = {}
    if SETTINGS_FILE.exists():
        data = json.loads(SETTINGS_FILE.read_text())

    data["favicon_filename"] = filename
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))

    log_action(get_db(), current_user.id, "upload_favicon", "panel_favicon", request=request)
    return {"success": True, "filename": filename}


@router.post("/interface/background")
async def upload_background(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Upload background image."""
    ensure_role(current_user.role, Role.admin)
    # Placeholder - would handle file upload
    return {"success": True}


# =============================================================================
# Backup & Restore
# =============================================================================

@router.get("/backup")
def get_backup_settings(
    current_user: User = Depends(get_current_user),
):
    """Get backup settings."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_backup_settings()


@router.put("/backup")
def update_backup_settings(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Update backup settings."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.update_backup_settings(payload)
    log_action(get_db(), current_user.id, "update_backup_settings", "backup", request=request)
    return result


@router.post("/backup/create")
def create_backup(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Create a panel backup."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.create_panel_backup()
    log_action(get_db(), current_user.id, "create_panel_backup", "panel_backup", request=request)
    return result


@router.post("/backup/restore/{backup_id}")
def restore_backup(
    backup_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Restore a panel backup."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.restore_panel_backup(backup_id)
    log_action(get_db(), current_user.id, "restore_panel_backup", backup_id, request=request)
    return result


@router.get("/backup/list")
def list_backups(
    current_user: User = Depends(get_current_user),
):
    """List all panel backups."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.list_panel_backups()


@router.delete("/backup/{backup_id}")
def delete_backup(
    backup_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Delete a panel backup."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.delete_panel_backup(backup_id)
    log_action(get_db(), current_user.id, "delete_panel_backup", backup_id, request=request)
    return result


@router.post("/backup/clear")
def clear_backups(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Clear all panel backups."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.clear_all_backups()
    log_action(get_db(), current_user.id, "clear_all_backups", "panel_backups", request=request)
    return result


# =============================================================================
# Alarm System
# =============================================================================

@router.get("/alarm")
def get_alarm_settings(
    current_user: User = Depends(get_current_user),
):
    """Get alarm settings."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_alarm_settings()


@router.put("/alarm")
def update_alarm_settings(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Update alarm settings."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.update_alarm_settings(payload)
    log_action(get_db(), current_user.id, "update_alarm_settings", "alarm", request=request)
    return result


@router.get("/alarm/tasks")
def get_alarm_tasks(
    current_user: User = Depends(get_current_user),
):
    """Get all alarm tasks."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_alarm_list()


@router.post("/alarm/tasks")
def create_alarm_task(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Create an alarm task."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.create_alarm_task(payload)
    log_action(get_db(), current_user.id, "create_alarm_task", payload.get("title", ""), request=request)
    return result


@router.put("/alarm/tasks/{task_id}")
def update_alarm_task(
    task_id: int,
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Update an alarm task."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.update_alarm_task(task_id, payload)
    log_action(get_db(), current_user.id, "update_alarm_task", str(task_id), request=request)
    return result


@router.delete("/alarm/tasks/{task_id}")
def delete_alarm_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Delete an alarm task."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.delete_alarm_task(task_id)
    log_action(get_db(), current_user.id, "delete_alarm_task", str(task_id), request=request)
    return result


@router.get("/alarm/logs/{task_id}")
def get_alarm_logs(
    task_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get alarm logs for a task."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_alarm_logs(task_id)


# =============================================================================
# Migrate
# =============================================================================

@router.post("/migrate/aapanel")
def migrate_from_aapanel(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Migrate from aaPanel."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.migrate_from_aapanel(
        payload.get("server_ip", ""),
        payload.get("ssh_user", ""),
        payload.get("ssh_password", "")
    )
    log_action(get_db(), current_user.id, "migrate_from_aapanel", payload.get("server_ip", ""), request=request)
    return result


@router.post("/migrate/other")
def migrate_from_other(
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Migrate from other panels."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.migrate_from_other_panel(
        payload.get("server_ip", ""),
        payload.get("ssh_user", ""),
        payload.get("ssh_password", ""),
        payload.get("panel_type", "")
    )
    log_action(get_db(), current_user.id, "migrate_from_other", payload.get("server_ip", ""), request=request)
    return result


# =============================================================================
# Service Management
# =============================================================================

@router.get("/services/all")
def get_all_services(
    current_user: User = Depends(get_current_user),
):
    """Get all system services."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_all_services()


@router.get("/services/{service_name}/status")
def get_service_status(
    service_name: str,
    current_user: User = Depends(get_current_user),
):
    """Get status of a specific service."""
    ensure_role(current_user.role, Role.admin)
    return settings_service.get_service_status(service_name)


@router.post("/services/{service_name}/restart")
def restart_service(
    service_name: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Restart a service."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.restart_service(service_name)
    log_action(get_db(), current_user.id, "restart_service", service_name, request=request)
    return result


@router.post("/services/{service_name}/stop")
def stop_service(
    service_name: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Stop a service."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.stop_service(service_name)
    log_action(get_db(), current_user.id, "stop_service", service_name, request=request)
    return result


@router.post("/services/{service_name}/start")
def start_service(
    service_name: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Start a service."""
    ensure_role(current_user.role, Role.admin)
    result = settings_service.start_service(service_name)
    log_action(get_db(), current_user.id, "start_service", service_name, request=request)
    return result
