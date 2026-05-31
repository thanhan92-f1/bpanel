from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, ensure_role
from app.models.entities import User, Website
from app.services import wordpress
from app.services.audit import log_action

router = APIRouter(prefix="/wordpress", tags=["wordpress"])


def _get_website(website_id: int, db: Session, current_user: User) -> Website:
    """Get website and verify ownership."""
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")
    if website.owner_id != current_user.id:
        ensure_role(current_user.role, Role.admin)
    return website


def _get_wp_path(website: Website) -> str:
    """Get the WordPress path (document root)."""
    if not website.root_path:
        raise HTTPException(status_code=400, detail="Website has no root path")
    public_path = Path(website.root_path) / "public_html"
    wp_cli = public_path / "wp-cli.php"
    wp_index = public_path / "index.php"
    if not wp_cli.exists() and not wp_index.exists():
        raise HTTPException(status_code=400, detail="WordPress not detected at this website")
    return str(public_path)


# Plugin endpoints
@router.get("/{website_id}/plugins")
def list_plugins(website_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all installed WordPress plugins."""
    website = _get_website(website_id, db, current_user)
    try:
        wp_path = _get_wp_path(website)
    except HTTPException:
        raise
    try:
        plugins = wordpress.list_plugins(wp_path, website.linux_user)
        return {"plugins": plugins}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{website_id}/plugins/{plugin}/activate")
def activate_plugin(website_id: int, plugin: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), request: Request = None):
    """Activate a WordPress plugin."""
    website = _get_website(website_id, db, current_user)
    try:
        wp_path = _get_wp_path(website)
    except HTTPException:
        raise
    try:
        result = wordpress.activate_plugin(wp_path, plugin, website.linux_user)
        log_action(db, current_user.id, "activate_plugin", website.domain, plugin, request=request)
        return {"message": f"Plugin '{plugin}' activated", "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{website_id}/plugins/{plugin}/deactivate")
def deactivate_plugin(website_id: int, plugin: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), request: Request = None):
    """Deactivate a WordPress plugin."""
    website = _get_website(website_id, db, current_user)
    try:
        wp_path = _get_wp_path(website)
    except HTTPException:
        raise
    try:
        result = wordpress.deactivate_plugin(wp_path, plugin, website.linux_user)
        log_action(db, current_user.id, "deactivate_plugin", website.domain, plugin, request=request)
        return {"message": f"Plugin '{plugin}' deactivated", "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{website_id}/plugins/{plugin}/delete")
def delete_plugin(website_id: int, plugin: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), request: Request = None):
    """Delete a WordPress plugin."""
    website = _get_website(website_id, db, current_user)
    ensure_role(current_user.role, Role.admin)  # Only admins can delete plugins
    try:
        wp_path = _get_wp_path(website)
    except HTTPException:
        raise
    try:
        result = wordpress.delete_plugin(wp_path, plugin, website.linux_user)
        log_action(db, current_user.id, "delete_plugin", website.domain, plugin, request=request)
        return {"message": f"Plugin '{plugin}' deleted", "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# Theme endpoints
@router.get("/{website_id}/themes")
def list_themes(website_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all installed WordPress themes."""
    website = _get_website(website_id, db, current_user)
    try:
        wp_path = _get_wp_path(website)
    except HTTPException:
        raise
    try:
        themes = wordpress.list_themes(wp_path, website.linux_user)
        return {"themes": themes}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{website_id}/themes/{theme}/activate")
def activate_theme(website_id: int, theme: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), request: Request = None):
    """Activate a WordPress theme."""
    website = _get_website(website_id, db, current_user)
    try:
        wp_path = _get_wp_path(website)
    except HTTPException:
        raise
    try:
        result = wordpress.activate_theme(wp_path, theme, website.linux_user)
        log_action(db, current_user.id, "activate_theme", website.domain, theme, request=request)
        return {"message": f"Theme '{theme}' activated", "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/{website_id}/health")
def health_check(website_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Run WordPress health check."""
    website = _get_website(website_id, db, current_user)
    try:
        wp_path = _get_wp_path(website)
    except HTTPException:
        raise
    try:
        result = wordpress.wp_health_check(wp_path, website.linux_user)
        return {"health": result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# Staging endpoints
@router.post("/{website_id}/staging/create")
def create_staging(website_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), request: Request = None):
    """Create a staging environment for the WordPress site."""
    website = _get_website(website_id, db, current_user)
    ensure_role(current_user.role, Role.admin)  # Only admins can create staging
    try:
        wp_path = _get_wp_path(website)
    except HTTPException:
        raise
    try:
        result = wordpress.create_staging(website.root_path, website.linux_user)
        log_action(db, current_user.id, "create_staging", website.domain, request=request)
        return {"message": "Staging environment created", "staging_path": result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{website_id}/staging/status")
def staging_status(website_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the status of the staging environment."""
    website = _get_website(website_id, db, current_user)
    try:
        status = wordpress.get_staging_status(website.root_path)
        return {"staging": status}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{website_id}/staging/push-to-production")
def push_staging_to_production(website_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), request: Request = None):
    """Push staging environment to production."""
    website = _get_website(website_id, db, current_user)
    ensure_role(current_user.role, Role.admin)  # Only admins can push to production
    try:
        wp_path = _get_wp_path(website)
    except HTTPException:
        raise
    try:
        result = wordpress.push_staging_to_production(website.root_path, website.linux_user)
        log_action(db, current_user.id, "push_staging_to_production", website.domain, request=request)
        return {"message": "Staging pushed to production", "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
