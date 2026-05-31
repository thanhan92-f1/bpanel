"""
System Monitor API Router - Provides endpoints for real-time system monitoring.
"""

from fastapi import APIRouter, Depends
from app.services import monitor
from app.api.deps import get_current_user
from app.models.entities import User

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/load")
def get_load_average(current_user: User = Depends(get_current_user)):
    """Get system load average (1, 5, 15 minutes) and CPU count."""
    return monitor.get_load_average()


@router.get("/cpu")
def get_cpu_usage(current_user: User = Depends(get_current_user)):
    """Get detailed CPU usage breakdown (user, system, idle, iowait, steal)."""
    return monitor.get_cpu_usage()


@router.get("/memory")
def get_memory_usage(current_user: User = Depends(get_current_user)):
    """Get memory usage statistics (total, used, free, available, buffers, cached, percent)."""
    return monitor.get_memory_usage()


@router.get("/swap")
def get_swap_usage(current_user: User = Depends(get_current_user)):
    """Get swap usage statistics."""
    return monitor.get_swap_usage()


@router.get("/disk-io")
def get_disk_io(current_user: User = Depends(get_current_user)):
    """Get disk I/O statistics per disk device."""
    return monitor.get_disk_io()


@router.get("/network-io")
def get_network_io(current_user: User = Depends(get_current_user)):
    """Get network I/O statistics per interface."""
    return monitor.get_network_io()


@router.get("/disk-usage")
def get_disk_usage(current_user: User = Depends(get_current_user)):
    """Get disk usage per mount point."""
    return monitor.get_disk_usage()


@router.get("/cpu-info")
def get_cpu_info(current_user: User = Depends(get_current_user)):
    """Get CPU model and core information."""
    return monitor.get_cpu_info()


@router.get("/system-info")
def get_system_info(current_user: User = Depends(get_current_user)):
    """Get overall system information (hostname, OS, uptime, kernel)."""
    return monitor.get_system_info()


@router.get("/processes")
def get_process_list(current_user: User = Depends(get_current_user)):
    """Get top processes by CPU usage."""
    return monitor.get_process_list()


@router.get("/all")
def get_all_metrics(current_user: User = Depends(get_current_user)):
    """Get all monitoring metrics in one call for dashboard display."""
    return monitor.get_all_metrics()
