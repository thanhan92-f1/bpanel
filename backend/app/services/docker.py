"""
Docker management service.

Provides functions to interact with Docker daemon for container and image management.
"""

import logging
from typing import Optional

import docker
from docker.errors import APIError, DockerException, NotFound

logger = logging.getLogger("bpanel")


def _get_client():
    """Get Docker client with error handling."""
    try:
        return docker.from_env()
    except DockerException as exc:
        logger.error("Failed to connect to Docker daemon: %s", exc)
        raise RuntimeError("Docker is not running or not installed") from exc


def get_docker_status() -> dict:
    """Check if Docker is running and get basic info."""
    try:
        client = _get_client()
        info = client.info()
        return {
            "running": True,
            "version": info.get("ServerVersion", "unknown"),
            "containers": info.get("Containers", 0),
            "images": info.get("Images", 0),
            "operating_system": info.get("OperatingSystem", "unknown"),
            "architecture": info.get("Architecture", "unknown"),
        }
    except (DockerException, RuntimeError) as exc:
        logger.warning("Docker status check failed: %s", exc)
        return {"running": False, "error": str(exc)}


def list_containers(all_containers: bool = True) -> list[dict]:
    """List all containers."""
    try:
        client = _get_client()
        containers = client.containers.list(all=all_containers)
        return [
            {
                "id": c.id,
                "short_id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "status": c.status,
                "state": c.attrs.get("State", {}).get("Status", "unknown"),
                "created": c.attrs.get("Created", "unknown"),
                "ports": [
                    {"private": p.get("PrivatePort"), "public": p.get("PublicPort"), "type": p.get("Type")}
                    for p in c.ports
                ],
            }
            for c in containers
        ]
    except (DockerException, RuntimeError) as exc:
        logger.error("Failed to list containers: %s", exc)
        raise RuntimeError(f"Failed to list containers: {exc}") from exc


def get_container_stats(container_id: str) -> dict:
    """Get stats for a specific container."""
    try:
        client = _get_client()
        container = client.containers.get(container_id)
        stats = container.stats(stream=False)
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        cpu_percent = 0.0
        if system_delta > 0:
            cpu_percent = round((cpu_delta / system_delta) * len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [0])) * 100, 2)
        memory_usage = stats["memory_stats"].get("usage", 0)
        memory_limit = stats["memory_stats"].get("limit", 1)
        memory_percent = round((memory_usage / memory_limit) * 100, 2) if memory_limit > 0 else 0
        networks = stats.get("networks", {})
        rx_bytes = sum(net.get("rx_bytes", 0) for net in networks.values())
        tx_bytes = sum(net.get("tx_bytes", 0) for net in networks.values())
        return {
            "id": container.short_id,
            "name": container.name,
            "cpu_percent": cpu_percent,
            "memory_usage": memory_usage,
            "memory_limit": memory_limit,
            "memory_percent": memory_percent,
            "network_rx": rx_bytes,
            "network_tx": tx_bytes,
        }
    except NotFound:
        raise RuntimeError(f"Container not found: {container_id}") from None
    except (DockerException, RuntimeError) as exc:
        logger.error("Failed to get container stats: %s", exc)
        raise RuntimeError(f"Failed to get container stats: {exc}") from exc


def start_container(container_id: str) -> dict:
    """Start a container."""
    try:
        client = _get_client()
        container = client.containers.get(container_id)
        container.start()
        return {"id": container.short_id, "name": container.name, "status": "started"}
    except NotFound:
        raise RuntimeError(f"Container not found: {container_id}") from None
    except (DockerException, RuntimeError) as exc:
        logger.error("Failed to start container %s: %s", container_id, exc)
        raise RuntimeError(f"Failed to start container: {exc}") from exc


def stop_container(container_id: str, timeout: int = 10) -> dict:
    """Stop a container."""
    try:
        client = _get_client()
        container = client.containers.get(container_id)
        container.stop(timeout=timeout)
        return {"id": container.short_id, "name": container.name, "status": "stopped"}
    except NotFound:
        raise RuntimeError(f"Container not found: {container_id}") from None
    except (DockerException, RuntimeError) as exc:
        logger.error("Failed to stop container %s: %s", container_id, exc)
        raise RuntimeError(f"Failed to stop container: {exc}") from exc


def restart_container(container_id: str, timeout: int = 10) -> dict:
    """Restart a container."""
    try:
        client = _get_client()
        container = client.containers.get(container_id)
        container.restart(timeout=timeout)
        return {"id": container.short_id, "name": container.name, "status": "restarted"}
    except NotFound:
        raise RuntimeError(f"Container not found: {container_id}") from None
    except (DockerException, RuntimeError) as exc:
        logger.error("Failed to restart container %s: %s", container_id, exc)
        raise RuntimeError(f"Failed to restart container: {exc}") from exc


def get_container_logs(container_id: str, lines: int = 100, timestamps: bool = False) -> dict:
    """Get logs for a specific container."""
    try:
        client = _get_client()
        container = client.containers.get(container_id)
        logs = container.logs(tail=lines, timestamps=timestamps, stream=False)
        if isinstance(logs, bytes):
            logs = logs.decode("utf-8", errors="replace")
        return {"id": container.short_id, "name": container.name, "lines": lines, "logs": logs}
    except NotFound:
        raise RuntimeError(f"Container not found: {container_id}") from None
    except (DockerException, RuntimeError) as exc:
        logger.error("Failed to get container logs: %s", exc)
        raise RuntimeError(f"Failed to get container logs: {exc}") from exc


def list_images() -> list[dict]:
    """List all Docker images."""
    try:
        client = _get_client()
        images = client.images.list()
        return [
            {
                "id": img.id,
                "short_id": img.short_id,
                "tags": img.tags if img.tags else [],
                "size": img.attrs.get("Size", 0),
                "created": img.attrs.get("Created", "unknown"),
            }
            for img in images
        ]
    except (DockerException, RuntimeError) as exc:
        logger.error("Failed to list images: %s", exc)
        raise RuntimeError(f"Failed to list images: {exc}") from exc


def pull_image(image_name: str) -> dict:
    """Pull a Docker image."""
    try:
        client = _get_client()
        result = client.images.pull(image_name)
        return {"image": image_name, "status": "pulled", "id": result.get("Id", "")}
    except APIError as exc:
        logger.error("Failed to pull image %s: %s", image_name, exc)
        raise RuntimeError(f"Failed to pull image: {exc}") from exc
    except (DockerException, RuntimeError) as exc:
        logger.error("Failed to pull image %s: %s", image_name, exc)
        raise RuntimeError(f"Failed to pull image: {exc}") from exc


def remove_container(container_id: str, force: bool = False) -> dict:
    """Remove a container."""
    try:
        client = _get_client()
        container = client.containers.get(container_id)
        container.remove(force=force)
        return {"id": container_id, "status": "removed"}
    except NotFound:
        raise RuntimeError(f"Container not found: {container_id}") from None
    except (DockerException, RuntimeError) as exc:
        logger.error("Failed to remove container %s: %s", container_id, exc)
        raise RuntimeError(f"Failed to remove container: {exc}") from exc


def remove_image(image_id: str, force: bool = False) -> dict:
    """Remove a Docker image."""
    try:
        client = _get_client()
        client.images.remove(image_id, force=force)
        return {"id": image_id, "status": "removed"}
    except NotFound:
        raise RuntimeError(f"Image not found: {image_id}") from None
    except APIError as exc:
        logger.error("Failed to remove image %s: %s", image_id, exc)
        raise RuntimeError(f"Failed to remove image: {exc}") from exc
