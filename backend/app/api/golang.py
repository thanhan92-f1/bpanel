"""Go Management API Router"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body

from app.api.deps import get_current_user
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.services import golang

router = APIRouter(prefix="/golang", tags=["golang"])


@router.get("/version")
def get_go_version(current_user: User = Depends(get_current_user)):
    """Get the currently installed Go version."""
    ensure_role(current_user.role, Role.admin)
    return golang.get_go_version()


@router.get("/versions")
def list_go_versions(current_user: User = Depends(get_current_user)):
    """List available Go versions."""
    ensure_role(current_user.role, Role.admin)
    return golang.list_go_versions()


@router.post("/versions/{version}/install")
def install_go_version(version: str, current_user: User = Depends(get_current_user)):
    """Install a specific Go version."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.install_go_version(version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/modules")
def get_go_modules(path: str = Query(..., description="Path to Go project"), current_user: User = Depends(get_current_user)):
    """List Go modules in a project."""
    ensure_role(current_user.role, Role.admin)
    try:
        return {"modules": golang.get_go_modules(path)}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/build")
def build_go_project(
    path: str = Query(..., description="Path to Go project"),
    output: str = Query(default="", description="Output binary path"),
    current_user: User = Depends(get_current_user)
):
    """Build a Go project."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.build_go_project(path, output)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/run")
def run_go_project(
    path: str = Query(..., description="Path to Go project"),
    args: list = Body(default=[], description="Arguments to pass to the Go application"),
    current_user: User = Depends(get_current_user)
):
    """Run a Go application."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.run_go_project(path, args)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/env")
def get_go_env(path: str = Query(default="", description="Path to Go project (optional)"), current_user: User = Depends(get_current_user)):
    """Get Go environment for project or global."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.get_go_env(path if path else "")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/test")
def test_go_project(
    path: str = Query(..., description="Path to Go project"),
    current_user: User = Depends(get_current_user)
):
    """Run Go tests in a project."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.test_go_project(path)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/setup/{website_id}")
def setup_golang_service(website_id: int, current_user: User = Depends(get_current_user)):
    """Setup Go web server with systemd for a website."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.setup_golang_service(website_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/processes")
def list_go_processes(current_user: User = Depends(get_current_user)):
    """List running Go processes."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.list_go_processes()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/processes/{name}/status")
def get_go_service_status(name: str, current_user: User = Depends(get_current_user)):
    """Get status of a Go systemd service."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.get_go_service_status(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/processes/{name}/restart")
def restart_go_service(name: str, current_user: User = Depends(get_current_user)):
    """Restart a Go systemd service."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.restart_go_service(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/processes/{name}/stop")
def stop_go_service(name: str, current_user: User = Depends(get_current_user)):
    """Stop a Go systemd service."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.stop_go_service(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/processes/{name}/logs")
def get_go_logs(
    name: str,
    lines: int = Query(default=100, ge=10, le=5000),
    current_user: User = Depends(get_current_user)
):
    """Get logs for a Go systemd service."""
    ensure_role(current_user.role, Role.admin)
    try:
        return golang.get_go_logs(name, lines)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
