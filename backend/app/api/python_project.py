"""Python Project Management API Router"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.services import python_project

router = APIRouter(prefix="/python", tags=["python"])


@router.get("/version")
def get_python_version(current_user: User = Depends(get_current_user)):
    """Get the default Python version."""
    ensure_role(current_user.role, Role.admin)
    return python_project.get_python_version()


@router.get("/versions")
def list_python_versions(current_user: User = Depends(get_current_user)):
    """List installed Python versions."""
    ensure_role(current_user.role, Role.admin)
    return python_project.list_python_versions()


@router.post("/versions/{version}/install")
def install_python_version(version: str, current_user: User = Depends(get_current_user)):
    """Install a specific Python version."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.install_python_version(version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/venvs")
def list_venvs(current_user: User = Depends(get_current_user)):
    """List all virtual environments."""
    ensure_role(current_user.role, Role.admin)
    return python_project.list_venvs()


@router.post("/venv")
def create_venv(
    path: str = Query(..., description="Path to create the virtual environment"),
    python_version: str = Query(default="python3", description="Python version to use"),
    current_user: User = Depends(get_current_user)
):
    """Create a virtual environment."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.create_venv(path, python_version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/venv/{venv_id}")
def delete_venv(venv_id: int, current_user: User = Depends(get_current_user)):
    """Delete a virtual environment."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.delete_venv(venv_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/venv/{venv_id}")
def get_venv_info(venv_id: int, current_user: User = Depends(get_current_user)):
    """Get virtual environment info."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.get_venv_info(venv_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/venv/{venv_id}/packages")
def list_venv_packages(venv_id: int, current_user: User = Depends(get_current_user)):
    """List installed packages in virtual environment."""
    ensure_role(current_user.role, Role.admin)
    try:
        venv_info = python_project.get_venv_info(venv_id)
        return python_project.list_venv_packages(venv_info["path"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/venv/{venv_id}/packages")
def install_venv_package(
    venv_id: int,
    package: str = Query(..., description="Package name with optional version (e.g., 'requests' or 'flask==2.0.0')"),
    current_user: User = Depends(get_current_user)
):
    """Install a package in virtual environment."""
    ensure_role(current_user.role, Role.admin)
    try:
        venv_info = python_project.get_venv_info(venv_id)
        return python_project.install_venv_package(venv_info["path"], package)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/venv/{venv_id}/packages/{package}")
def uninstall_venv_package(
    venv_id: int,
    package: str,
    current_user: User = Depends(get_current_user)
):
    """Uninstall a package from virtual environment."""
    ensure_role(current_user.role, Role.admin)
    try:
        venv_info = python_project.get_venv_info(venv_id)
        return python_project.uninstall_venv_package(venv_info["path"], package)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/run")
def run_python_script(
    venv_path: str = Query(..., description="Path to virtual environment"),
    script: str = Query(..., description="Path to Python script"),
    args: str = Query(default="", description="Comma-separated arguments"),
    current_user: User = Depends(get_current_user)
):
    """Run a Python script in virtual environment."""
    ensure_role(current_user.role, Role.admin)
    try:
        args_list = [a.strip() for a in args.split(",") if a.strip()]
        return python_project.run_python_script(venv_path, script, args_list)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/test")
def test_python_project(
    path: str = Query(..., description="Path to Python project"),
    current_user: User = Depends(get_current_user)
):
    """Run pytest on a Python project."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.test_python_project(path)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/setup/{website_id}")
def setup_python_service(
    website_id: int,
    venv_path: str = Query(..., description="Path to virtual environment"),
    script: str = Query(default=None, description="Entry script path relative to document root"),
    current_user: User = Depends(get_current_user)
):
    """Setup Python app with systemd service for a website."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.setup_python_service(website_id, venv_path, script)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/processes")
def get_python_processes(current_user: User = Depends(get_current_user)):
    """List running Python processes."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.get_python_processes()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/processes/{name}/restart")
def restart_python_service(name: str, current_user: User = Depends(get_current_user)):
    """Restart a Python systemd service."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.restart_python_service(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/processes/{name}/stop")
def stop_python_service(name: str, current_user: User = Depends(get_current_user)):
    """Stop a Python systemd service."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.stop_python_service(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/processes/{name}/logs")
def get_python_logs(
    name: str,
    lines: int = Query(default=100, ge=10, le=5000),
    current_user: User = Depends(get_current_user)
):
    """Get logs for a Python systemd service."""
    ensure_role(current_user.role, Role.admin)
    try:
        return python_project.get_python_logs(name, lines)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
