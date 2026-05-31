"""
Enhanced Backup API Router

Provides REST API endpoints for the enhanced backup system.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
from starlette.background import BackgroundTask

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, ensure_role, is_admin_role
from app.models.entities import User
from app.services import backup_enhanced as backup_service


router = APIRouter(prefix="/backup", tags=["backup"])


def require_admin(current_user: User = Depends(get_current_user)):
    """Require admin role for backup operations."""
    ensure_role(current_user.role, Role.admin)
    return current_user


# =============================================================================
# Backup Jobs
# =============================================================================

@router.get("/jobs")
def list_backup_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all backup jobs."""
    return backup_service.list_backup_jobs(db)


@router.post("/jobs")
def create_backup_job(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new backup job."""
    try:
        return backup_service.create_backup_job(
            db=db,
            name=payload.get("name"),
            job_type=payload.get("job_type", "full"),
            destinations=payload.get("destinations", ["local"]),
            include_websites=payload.get("include_websites"),
            include_databases=payload.get("include_databases"),
            exclude_paths=payload.get("exclude_paths"),
            schedule=payload.get("schedule"),
            retention_days=payload.get("retention_days", 30),
            encryption_enabled=payload.get("encryption_enabled", False),
            compression_level=payload.get("compression_level", 6),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}")
def get_backup_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific backup job."""
    jobs = backup_service.list_backup_jobs(db)
    for job in jobs:
        if job["id"] == job_id:
            return job
    raise HTTPException(status_code=404, detail="Backup job not found")


@router.put("/jobs/{job_id}")
def update_backup_job(
    job_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update a backup job."""
    try:
        return backup_service.update_backup_job(db, job_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/jobs/{job_id}")
def delete_backup_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a backup job."""
    try:
        return backup_service.delete_backup_job(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/jobs/{job_id}/run")
def run_backup_now(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Run a backup job immediately."""
    try:
        return backup_service.run_backup_now(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/history")
def get_job_backup_history(
    job_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get backup history for a specific job."""
    return backup_service.get_backup_history(db, job_id, page, per_page)


# =============================================================================
# Website Backup
# =============================================================================

@router.post("/website/{website_id}/full")
def backup_website_full(
    website_id: int,
    payload: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a full backup of a website (files + database)."""
    destinations = payload.get("destinations", ["local"]) if payload else ["local"]
    exclude_paths = payload.get("exclude_paths") if payload else None

    try:
        return backup_service.backup_website(db, website_id, destinations, exclude_paths)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/website/{website_id}/files")
def backup_website_files(
    website_id: int,
    payload: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Backup only website files."""
    destination = payload.get("destination", "local") if payload else "local"
    exclude_paths = payload.get("exclude_paths") if payload else None

    from app.models.entities import Website
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    backup_dir = Path(backup_service.BACKUP_ROOT) / "websites" / website.domain
    backup_dir.mkdir(parents=True, exist_ok=True)
    archive_path = backup_dir / f"{website.domain}-files-{timestamp}.tar.gz"

    try:
        result = backup_service.backup_website_files(
            website.root_path,
            str(archive_path),
            exclude_paths
        )
        return {
            "ok": True,
            "backup_file": str(archive_path),
            "website_id": website_id,
            "destination": destination,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/website/{website_id}/database")
def backup_website_database(
    website_id: int,
    payload: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Backup only the website database."""
    destination = payload.get("destination", "local") if payload else "local"

    try:
        return backup_service.backup_website_database(db, website_id, destination)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Database Backup
# =============================================================================

@router.get("/databases")
def list_database_backups(
    database_id: int = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List database backups."""
    return backup_service.list_database_backups(db, database_id)


@router.post("/database/{database_id}")
def backup_database(
    database_id: int,
    payload: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a backup of a specific database."""
    destination = payload.get("destination", "local") if payload else "local"

    try:
        return backup_service.backup_database(db, database_id, destination)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore/{backup_id}")
def restore_database_from_backup(
    backup_id: str,
    target_database_id: int = Query(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore a database from a backup."""
    try:
        return backup_service.restore_database_from_backup(db, backup_id, target_database_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Path Backup
# =============================================================================

@router.post("/path")
def backup_path_endpoint(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Backup a specific path."""
    path = payload.get("path")
    destination = payload.get("destination", "local")
    exclude_patterns = payload.get("exclude_patterns")

    if not path:
        raise HTTPException(status_code=400, detail="path is required")

    try:
        return backup_service.backup_path(path, destination, exclude_patterns)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Storage Configuration
# =============================================================================

@router.get("/storage")
def get_storage_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all storage configurations."""
    return backup_service.get_storage_configs(db)


@router.post("/storage/ftp")
def configure_ftp_storage(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Configure FTP storage."""
    try:
        return backup_service.configure_ftp_storage(db, config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/storage/s3")
def configure_s3_storage(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Configure S3 storage."""
    try:
        return backup_service.configure_s3_storage(db, config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/storage/ssh")
def configure_ssh_storage(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Configure SSH/SFTP storage."""
    try:
        return backup_service.configure_ssh_storage(db, config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/storage/onedrive")
def configure_onedrive_storage(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Configure OneDrive storage."""
    try:
        return backup_service.configure_onedrive_storage(db, config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/storage/google-drive")
def configure_google_drive_storage(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Configure Google Drive storage."""
    try:
        return backup_service.configure_google_drive_storage(db, config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/storage/webdav")
def configure_webdav_storage(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Configure WebDAV storage."""
    try:
        return backup_service.configure_webdav_storage(db, config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/storage/b2")
def configure_b2_storage(
    config: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Configure Backblaze B2 storage."""
    try:
        return backup_service.configure_b2_storage(db, config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/storage/{config_id}")
def delete_storage_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a storage configuration."""
    try:
        return backup_service.delete_storage_config(db, config_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/storage/{config_id}/test")
def test_storage_connection(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Test connection to a storage destination."""
    try:
        return backup_service.test_storage_connection(db, str(config_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Backup Operations
# =============================================================================

@router.get("/history")
def get_backup_history(
    job_id: int = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get backup history with pagination."""
    return backup_service.get_backup_history(db, job_id, page, per_page)


@router.get("/{backup_id}")
def get_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get backup details."""
    from app.models.entities import BackupHistory
    history = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Backup not found")
    return backup_service._history_to_dict(history)


@router.delete("/{backup_id}")
def delete_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a backup."""
    try:
        return backup_service.delete_backup(backup_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{backup_id}/download")
def download_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a backup file."""
    try:
        file_path = backup_service.download_backup(backup_id, db)
        return FileResponse(
            file_path,
            filename=Path(file_path).name,
            media_type="application/gzip",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{backup_id}/verify")
def verify_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify backup integrity."""
    try:
        return backup_service.verify_backup(backup_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{backup_id}/encrypt")
def encrypt_backup(
    backup_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Encrypt a backup file."""
    password = payload.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="password is required")

    try:
        return backup_service.encrypt_backup(backup_id, password, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{backup_id}/decrypt")
def decrypt_backup(
    backup_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Decrypt a backup file."""
    password = payload.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="password is required")

    try:
        return backup_service.decrypt_backup(backup_id, password, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Exclude Patterns
# =============================================================================

@router.get("/exclude-patterns")
def get_exclude_patterns(
    current_user: User = Depends(get_current_user),
):
    """Get common exclude patterns for backups."""
    return [
        {"pattern": "node_modules/*", "description": "Node.js dependencies"},
        {"pattern": ".git/*", "description": "Git repository"},
        {"pattern": "*.log", "description": "Log files"},
        {"pattern": "tmp/*", "description": "Temporary files"},
        {"pattern": "cache/*", "description": "Cache files"},
        {"pattern": "__pycache__/*", "description": "Python cache"},
        {"pattern": ".DS_Store", "description": "macOS system files"},
        {"pattern": "Thumbs.db", "description": "Windows system files"},
        {"pattern": "*.bak", "description": "Backup files"},
        {"pattern": "*.swp", "description": "Vim swap files"},
    ]


# =============================================================================
# Retention
# =============================================================================

@router.post("/retention/{job_id}/apply")
def apply_retention_policy(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Apply retention policy to a backup job."""
    try:
        return backup_service.apply_retention_policy(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/retention/stats")
def get_retention_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get backup retention statistics."""
    return backup_service.get_retention_stats(db)
