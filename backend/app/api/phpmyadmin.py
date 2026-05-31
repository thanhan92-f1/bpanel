"""phpMyAdmin management API endpoints."""

from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.services import phpmyadmin
from app.services.audit import log_action


router = APIRouter(prefix="/phpmyadmin", tags=["phpmyadmin"])


# Request/Response schemas
class PhpMyAdminConfigUpdate(BaseModel):
    blowfish_secret: Optional[str] = None
    auth_type: Optional[str] = Field(None, pattern="^(cookie|http|config)$")
    host: Optional[str] = None
    compress: Optional[bool] = None
    force_ssl: Optional[bool] = None
    lang: Optional[str] = None
    default_lang: Optional[str] = None
    show_server_info: Optional[bool] = None
    show_php_info: Optional[bool] = None
    version_check: Optional[bool] = None
    cookie_secure: Optional[bool] = None
    cookie_httponly: Optional[bool] = None
    session_timeout: Optional[int] = Field(None, ge=60, le=86400)


class PhpMyAdminSecuritySettings(BaseModel):
    restrict_ips: bool = True
    allowed_ips: Optional[list] = None
    block_root_login: bool = True
    hide_version: bool = True
    enable_csrf_protection: bool = True
    session_timeout: int = Field(1800, ge=60, le=86400)
    max_failed_logins: int = Field(5, ge=1, le=100)
    enable_ssl_only: bool = True


class PhpMyAdminInstallSettings(BaseModel):
    subdomain: Optional[str] = None
    use_subdirectory: bool = False
    ssl_enabled: bool = True


class PhpMyAdminRestoreRequest(BaseModel):
    backup_timestamp: Optional[str] = None


@router.get("/status")
def get_status(current_user: User = Depends(get_current_user)):
    """Get phpMyAdmin installation status."""
    ensure_role(current_user.role, Role.admin)
    try:
        status = phpmyadmin.get_phpmyadmin_status()
        return status
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/install")
def install_phpmyadmin(
    settings: PhpMyAdminInstallSettings,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Install phpMyAdmin on the server."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = phpmyadmin.install_phpmyadmin(
            subdomain=settings.subdomain,
            use_subdirectory=settings.use_subdirectory,
            ssl_enabled=settings.ssl_enabled,
        )
        log_action(
            db=None,
            user_id=current_user.id,
            action="install_phpmyadmin",
            target=settings.subdomain or "/phpmyadmin",
            request=request,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("")
def uninstall_phpmyadmin(
    remove_data: bool = False,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Uninstall phpMyAdmin from the server."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = phpmyadmin.uninstall_phpmyadmin(remove_data=remove_data)
        log_action(
            db=None,
            user_id=current_user.id,
            action="uninstall_phpmyadmin",
            target=f"remove_data={remove_data}",
            request=request,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/config")
def get_config(current_user: User = Depends(get_current_user)):
    """Get current phpMyAdmin configuration."""
    ensure_role(current_user.role, Role.admin)
    try:
        status = phpmyadmin.get_phpmyadmin_status()
        if not status["configured"]:
            raise HTTPException(status_code=404, detail="phpMyAdmin is not configured")
        # Read config file
        from pathlib import Path
        config_file = Path("/etc/phpmyadmin/config.inc.php")
        if config_file.exists():
            content = config_file.read_text()
            return {
                "config_file": str(config_file),
                "configured": True,
                "content": content,
            }
        raise HTTPException(status_code=404, detail="Configuration file not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/config")
def update_config(
    settings: PhpMyAdminConfigUpdate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Update phpMyAdmin configuration settings."""
    ensure_role(current_user.role, Role.admin)
    try:
        # Build settings dict
        update_settings = {}
        for field, value in settings.model_dump(exclude_none=True).items():
            if value is not None:
                update_settings[field] = value

        result = phpmyadmin.update_phpmyadmin_config(update_settings)
        log_action(
            db=None,
            user_id=current_user.id,
            action="update_phpmyadmin_config",
            target="config",
            request=request,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/url")
def get_url(current_user: User = Depends(get_current_user)):
    """Get phpMyAdmin access URL."""
    ensure_role(current_user.role, Role.admin)
    try:
        url = phpmyadmin.get_phpmyadmin_url()
        if url is None:
            raise HTTPException(status_code=404, detail="phpMyAdmin URL not configured")
        return {"url": url}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/secure")
def apply_security_settings(
    settings: PhpMyAdminSecuritySettings,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Apply security settings to phpMyAdmin."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = phpmyadmin.secure_phpmyadmin(
            restrict_ips=settings.restrict_ips,
            allowed_ips=settings.allowed_ips,
            block_root_login=settings.block_root_login,
            hide_version=settings.hide_version,
            enable_csrf_protection=settings.enable_csrf_protection,
            session_timeout=settings.session_timeout,
            max_failed_logins=settings.max_failed_logins,
            enable_ssl_only=settings.enable_ssl_only,
        )
        log_action(
            db=None,
            user_id=current_user.id,
            action="secure_phpmyadmin",
            target="phpmyadmin",
            request=request,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/setup-secret")
def setup_secret(
    force: bool = False,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Generate and setup blowfish secret for phpMyAdmin."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = phpmyadmin.setup_blowfish_secret(force=force)
        log_action(
            db=None,
            user_id=current_user.id,
            action="setup_phpmyadmin_secret",
            target="blowfish_secret",
            request=request,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/requirements")
def check_requirements(current_user: User = Depends(get_current_user)):
    """Check server requirements for phpMyAdmin installation."""
    ensure_role(current_user.role, Role.admin)
    try:
        requirements = phpmyadmin.check_phpmyadmin_requirements()
        return requirements
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/backup-config")
def backup_config(current_user: User = Depends(get_current_user), request: Request = None):
    """Create a backup of phpMyAdmin configuration."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = phpmyadmin.backup_phpmyadmin_config()
        log_action(
            db=None,
            user_id=current_user.id,
            action="backup_phpmyadmin_config",
            target="phpmyadmin",
            request=request,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/restore-config")
def restore_config(
    payload: PhpMyAdminRestoreRequest,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Restore phpMyAdmin configuration from a backup."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = phpmyadmin.restore_phpmyadmin_config(backup_timestamp=payload.backup_timestamp)
        log_action(
            db=None,
            user_id=current_user.id,
            action="restore_phpmyadmin_config",
            target=payload.backup_timestamp or "latest",
            request=request,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/version")
def get_version(current_user: User = Depends(get_current_user)):
    """Get installed phpMyAdmin version."""
    ensure_role(current_user.role, Role.admin)
    try:
        version = phpmyadmin.get_phpmyadmin_version()
        if version is None:
            raise HTTPException(status_code=404, detail="phpMyAdmin is not installed")
        return {"version": version}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
