"""Node.js Management API Router"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.services import nodejs

router = APIRouter(prefix="/nodejs", tags=["nodejs"])


@router.get("/version")
def get_node_version(current_user: User = Depends(get_current_user)):
    """Get the currently installed Node.js version."""
    ensure_role(current_user.role, Role.admin)
    return nodejs.get_node_version()


@router.get("/versions")
def list_node_versions(current_user: User = Depends(get_current_user)):
    """List available Node.js versions via nvm."""
    ensure_role(current_user.role, Role.admin)
    return nodejs.list_node_versions()


@router.post("/versions/{version}/install")
def install_node_version(version: str, current_user: User = Depends(get_current_user)):
    """Install a specific Node.js version."""
    ensure_role(current_user.role, Role.admin)
    try:
        return nodejs.install_node_version(version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/npm-version")
def get_npm_version(current_user: User = Depends(get_current_user)):
    """Get the npm version."""
    ensure_role(current_user.role, Role.admin)
    return nodejs.get_npm_version()


@router.get("/pm2/processes")
def list_pm2_processes(current_user: User = Depends(get_current_user)):
    """List all PM2 processes."""
    ensure_role(current_user.role, Role.admin)
    try:
        return nodejs.list_pm2_processes()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pm2/processes/{name}")
def get_pm2_process_info(name: str, current_user: User = Depends(get_current_user)):
    """Get detailed information about a specific PM2 process."""
    ensure_role(current_user.role, Role.admin)
    try:
        return nodejs.get_pm2_process_info(name)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pm2/processes/{name}/restart")
def restart_pm2_process(name: str, current_user: User = Depends(get_current_user)):
    """Restart a PM2 process."""
    ensure_role(current_user.role, Role.admin)
    try:
        return nodejs.restart_pm2_process(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pm2/processes/{name}/stop")
def stop_pm2_process(name: str, current_user: User = Depends(get_current_user)):
    """Stop a PM2 process."""
    ensure_role(current_user.role, Role.admin)
    try:
        return nodejs.stop_pm2_process(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/pm2/processes/{name}")
def delete_pm2_process(name: str, current_user: User = Depends(get_current_user)):
    """Delete a PM2 process."""
    ensure_role(current_user.role, Role.admin)
    try:
        return nodejs.delete_pm2_process(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pm2/processes/{name}/logs")
def get_pm2_logs(
    name: str,
    lines: int = Query(default=100, ge=10, le=5000),
    current_user: User = Depends(get_current_user)
):
    """Get PM2 logs for a specific process."""
    ensure_role(current_user.role, Role.admin)
    try:
        return nodejs.get_pm2_logs(name, lines)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pm2/setup/{website_id}")
def setup_pm2_for_website(
    website_id: int,
    path: str = Query(default=""),
    current_user: User = Depends(get_current_user)
):
    """Setup PM2 for a website application."""
    ensure_role(current_user.role, Role.admin)
    try:
        return nodejs.setup_pm2_process(website_id, path)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
