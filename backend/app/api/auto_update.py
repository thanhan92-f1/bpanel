"""Auto Update API Router for BPanel.

Provides endpoints for checking, downloading, and installing BPanel updates,
as well as backup and rollback functionality.
"""

import logging
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.services import auto_update

logger = logging.getLogger("bpanel.api.auto_update")

router = APIRouter(prefix="/update", tags=["update"])


@router.get("/check")
def check_for_updates(current_user: User = Depends(get_current_user)):
    """Check for available BPanel updates from GitHub."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.check_for_updates()


@router.get("/current")
def get_current_version(current_user: User = Depends(get_current_user)):
    """Get current installed version of BPanel."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.get_current_version()


@router.get("/available")
def get_available_update(current_user: User = Depends(get_current_user)):
    """Get information about available update."""
    ensure_role(current_user.role, Role.admin)
    result = auto_update.check_for_updates()
    if result.get("update_available"):
        return {
            "available": True,
            "version": result.get("latest_version"),
            "release_name": result.get("release_name"),
            "release_notes": result.get("release_notes"),
            "prerelease": result.get("prerelease", False),
            "assets": result.get("assets", []),
        }
    return {
        "available": False,
        "current_version": result.get("current_version"),
    }


@router.post("/download/{version}")
def download_update(version: str, current_user: User = Depends(get_current_user)):
    """Download update package for specified version."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.download_update(version)


@router.post("/install/{version}")
def install_update(version: str, current_user: User = Depends(get_current_user)):
    """Install downloaded update for specified version."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.install_update(version, backup=True)


@router.get("/settings")
def get_update_settings(current_user: User = Depends(get_current_user)):
    """Get auto update settings."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.get_update_settings()


@router.put("/settings")
def update_settings(
    settings_update: dict,
    current_user: User = Depends(get_current_user)
):
    """Update auto update settings."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.update_update_settings(settings_update)


@router.get("/backups")
def list_update_backups(current_user: User = Depends(get_current_user)):
    """List available backups."""
    ensure_role(current_user.role, Role.admin)
    return {"backups": auto_update.list_backups()}


@router.post("/backup")
def create_update_backup(current_user: User = Depends(get_current_user)):
    """Create a backup before update."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.create_backup()


@router.post("/restore/{backup_id}")
def restore_from_backup(backup_id: str, current_user: User = Depends(get_current_user)):
    """Restore from a specific backup."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.restore_backup(backup_id)


@router.delete("/backup/{backup_id}")
def delete_update_backup(backup_id: str, current_user: User = Depends(get_current_user)):
    """Delete a specific backup."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.delete_backup(backup_id)


@router.post("/rollback")
def rollback_update(current_user: User = Depends(get_current_user)):
    """Rollback to the previous version using the most recent backup."""
    ensure_role(current_user.role, Role.admin)
    return auto_update.rollback()


@router.get("/logs")
def get_logs(current_user: User = Depends(get_current_user)):
    """Get recent update activity logs."""
    ensure_role(current_user.role, Role.admin)
    return {"logs": auto_update.get_update_logs()}


@router.get("/verify/{version}")
def verify_package(version: str, current_user: User = Depends(get_current_user)):
    """Verify a downloaded package for a specific version."""
    ensure_role(current_user.role, Role.admin)
    from pathlib import Path
    download_dir = Path("/var/backups/bpanel/updates/downloads")
    package_files = list(download_dir.glob(f"*{version}*"))
    if not package_files:
        return {
            "valid": False,
            "error": "Package not found. Please download first.",
        }
    return auto_update.verify_update_package(str(package_files[0]))
