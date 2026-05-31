"""Docker management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.schemas.schemas import DockerImagePull, DockerContainerAction
from app.services import docker

router = APIRouter(prefix="/docker", tags=["docker"])


@router.get("/status")
def get_status(current_user: User = Depends(get_current_user)):
    """Get Docker daemon status."""
    ensure_role(current_user.role, Role.admin)
    return docker.get_docker_status()


@router.get("/containers")
def list_containers(
    all_containers: bool = Query(True, description="Include stopped containers"),
    current_user: User = Depends(get_current_user),
):
    """List all Docker containers."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.list_containers(all_containers=all_containers)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/containers/{container_id}/stats")
def get_container_stats(container_id: str, current_user: User = Depends(get_current_user)):
    """Get statistics for a container."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.get_container_stats(container_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.post("/containers/{container_id}/start")
def start_container(container_id: str, current_user: User = Depends(get_current_user)):
    """Start a container."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.start_container(container_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/containers/{container_id}/stop")
def stop_container(container_id: str, current_user: User = Depends(get_current_user)):
    """Stop a container."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.stop_container(container_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/containers/{container_id}/restart")
def restart_container(container_id: str, current_user: User = Depends(get_current_user)):
    """Restart a container."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.restart_container(container_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/containers/{container_id}/logs")
def get_container_logs(
    container_id: str,
    lines: int = Query(100, ge=1, le=5000),
    timestamps: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    """Get logs for a container."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.get_container_logs(container_id, lines=lines, timestamps=timestamps)
    except RuntimeError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.delete("/containers/{container_id}")
def delete_container(container_id: str, force: bool = Query(False), current_user: User = Depends(get_current_user)):
    """Remove a container."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.remove_container(container_id, force=force)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/images")
def list_images(current_user: User = Depends(get_current_user)):
    """List all Docker images."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.list_images()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/images/pull")
def pull_image(payload: DockerImagePull, current_user: User = Depends(get_current_user)):
    """Pull a Docker image."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.pull_image(payload.image_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/images/{image_id}")
def delete_image(image_id: str, force: bool = Query(False), current_user: User = Depends(get_current_user)):
    """Remove a Docker image."""
    ensure_role(current_user.role, Role.admin)
    try:
        return docker.remove_image(image_id, force=force)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
