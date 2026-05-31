"""
System Monitor Service - Real-time resource monitoring for BPanel.
Reads system metrics from /proc filesystem and other sources.
"""

import os
import time
from typing import Any


def _read_file(path: str) -> str | None:
    """Read a file and return its contents, or None if not accessible."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, IOError):
        return None


def get_load_average() -> dict:
    """
    Get system load average (1, 5, 15 minutes).
    Reads from /proc/loadavg.
    Returns: {"1min": 0.5, "5min": 0.3, "15min": 0.2, "cpus": 4}
    """
    content = _read_file("/proc/loadavg")
    if not content:
        return {"1min": 0.0, "5min": 0.0, "15min": 0.0, "cpus": os.cpu_count() or 1}

    parts = content.strip().split()
    if len(parts) < 4:
        return {"1min": 0.0, "5min": 0.0, "15min": 0.0, "cpus": os.cpu_count() or 1}

    try:
        return {
            "1min": float(parts[0]),
            "5min": float(parts[1]),
            "15min": float(parts[2]),
            "cpus": os.cpu_count() or 1,
        }
    except (ValueError, IndexError):
        return {"1min": 0.0, "5min": 0.0, "15min": 0.0, "cpus": os.cpu_count() or 1}


def _read_cpu_times() -> dict:
    """Read CPU time values from /proc/stat."""
    content = _read_file("/proc/stat")
    if not content:
        return {"user": 0, "nice": 0, "system": 0, "idle": 0, "iowait": 0, "irq": 0, "softirq": 0, "steal": 0}

    lines = content.strip().split("\n")
    if not lines:
        return {"user": 0, "nice": 0, "system": 0, "idle": 0, "iowait": 0, "irq": 0, "softirq": 0, "steal": 0}

    fields = lines[0].split()
    if not fields or fields[0] != "cpu":
        return {"user": 0, "nice": 0, "system": 0, "idle": 0, "iowait": 0, "irq": 0, "softirq": 0, "steal": 0}

    values = [int(f) for f in fields[1:] if f.isdigit()]
    return {
        "user": values[0] if len(values) > 0 else 0,
        "nice": values[1] if len(values) > 1 else 0,
        "system": values[2] if len(values) > 2 else 0,
        "idle": values[3] if len(values) > 3 else 0,
        "iowait": values[4] if len(values) > 4 else 0,
        "irq": values[5] if len(values) > 5 else 0,
        "softirq": values[6] if len(values) > 6 else 0,
        "steal": values[7] if len(values) > 7 else 0,
    }


def get_cpu_usage() -> dict:
    """
    Get detailed CPU usage breakdown.
    Reads from /proc/stat and calculates usage between two samples.
    Returns: {"user": 10, "system": 5, "idle": 85, "iowait": 0, "steal": 0}
    """
    sample_time = 0.1  # 100ms sampling interval

    # First sample
    start = _read_cpu_times()
    time.sleep(sample_time)

    # Second sample
    end = _read_cpu_times()

    # Calculate deltas
    user_delta = end["user"] - start["user"]
    nice_delta = end["nice"] - start["nice"]
    system_delta = end["system"] - start["system"]
    idle_delta = end["idle"] - start["idle"]
    iowait_delta = end["iowait"] - start["iowait"]
    irq_delta = end["irq"] - start["irq"]
    softirq_delta = end["softirq"] - start["softirq"]
    steal_delta = end["steal"] - start["steal"]

    total_delta = user_delta + nice_delta + system_delta + idle_delta + iowait_delta + irq_delta + softirq_delta + steal_delta

    if total_delta <= 0:
        return {"user": 0, "system": 0, "idle": 100, "iowait": 0, "steal": 0}

    # Calculate percentages
    user_pct = round((user_delta / total_delta) * 100, 1)
    system_pct = round((system_delta / total_delta) * 100, 1)
    idle_pct = round((idle_delta / total_delta) * 100, 1)
    iowait_pct = round((iowait_delta / total_delta) * 100, 1)
    steal_pct = round((steal_delta / total_delta) * 100, 1)

    return {
        "user": max(0.0, min(100.0, user_pct)),
        "system": max(0.0, min(100.0, system_pct)),
        "idle": max(0.0, min(100.0, idle_pct)),
        "iowait": max(0.0, min(100.0, iowait_pct)),
        "steal": max(0.0, min(100.0, steal_pct)),
    }


def get_memory_usage() -> dict:
    """
    Get memory usage statistics.
    Reads from /proc/meminfo.
    Returns: {"total": 16384, "used": 8192, "free": 4096, "available": 8192, "buffers": 2048, "cached": 4096, "percent": 50}
    """
    content = _read_file("/proc/meminfo")
    if not content:
        return {"total": 0, "used": 0, "free": 0, "available": 0, "buffers": 0, "cached": 0, "percent": 0}

    values: dict[str, int] = {}
    for line in content.strip().split("\n"):
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        parts = rest.strip().split()
        if parts and parts[0].isdigit():
            # Values in /proc/meminfo are in kB
            values[key] = int(parts[0]) * 1024

    total = values.get("MemTotal", 0)
    free = values.get("MemFree", 0)
    available = values.get("MemAvailable", free)
    buffers = values.get("Buffers", 0)
    cached = values.get("Cached", 0)

    # Calculate used memory (total - available, as per modern Linux)
    used = max(0, total - available)
    percent = round((used / total) * 100, 1) if total > 0 else 0.0

    return {
        "total": total,
        "used": used,
        "free": free,
        "available": available,
        "buffers": buffers,
        "cached": cached,
        "percent": percent,
    }


def get_swap_usage() -> dict:
    """
    Get swap usage statistics.
    Reads from /proc/meminfo.
    Returns: {"total": 8192, "used": 1024, "free": 7168, "percent": 12.5}
    """
    content = _read_file("/proc/meminfo")
    if not content:
        return {"total": 0, "used": 0, "free": 0, "percent": 0}

    values: dict[str, int] = {}
    for line in content.strip().split("\n"):
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        parts = rest.strip().split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0]) * 1024

    total = values.get("SwapTotal", 0)
    free = values.get("SwapFree", 0)
    used = max(0, total - free)
    percent = round((used / total) * 100, 1) if total > 0 else 0.0

    return {
        "total": total,
        "used": used,
        "free": free,
        "percent": percent,
    }


def get_disk_io() -> dict:
    """
    Get disk I/O statistics.
    Reads from /proc/diskstats.
    Returns: {"sda": {"reads": 1000, "writes": 500, "read_bytes": 4096000, "write_bytes": 2048000}, ...}
    """
    content = _read_file("/proc/diskstats")
    if not content:
        return {}

    disks: dict[str, dict[str, int]] = {}
    for line in content.strip().split("\n"):
        if not line.strip():
            continue
        fields = line.split()
        # Format: device_name reads completed merged reads_sectors_ms time_spent_reads writes_merged writes_sectors_ms time_spent_writes
        # Linux kernel 4.18+ has 20 fields, earlier versions have 14
        if len(fields) < 14:
            continue

        device = fields[2]  # Device name (e.g., sda, nvme0n1)

        # Skip partitions and loop devices, include only whole disks
        if device.startswith("loop") or device.startswith("ram"):
            continue

        try:
            # Field indices for sector counts
            # reads_completed = fields[3] (actually sectors read)
            # writes_completed = fields[7] (actually sectors written)
            reads = int(fields[3])  # Sectors read
            writes = int(fields[7])  # Sectors written

            # Sector size is typically 512 bytes
            sector_size = 512

            disks[device] = {
                "reads": reads,
                "writes": writes,
                "read_bytes": reads * sector_size,
                "write_bytes": writes * sector_size,
            }
        except (ValueError, IndexError):
            continue

    return disks


def get_network_io() -> dict:
    """
    Get network I/O statistics.
    Reads from /proc/net/dev.
    Returns: {"eth0": {"rx_bytes": 1000, "tx_bytes": 500, "rx_packets": 100, "tx_packets": 50}, ...}
    """
    content = _read_file("/proc/net/dev")
    if not content:
        return {}

    interfaces: dict[str, dict[str, int]] = {}
    lines = content.strip().split("\n")

    # Skip header lines (first two lines)
    for line in lines[2:]:
        if ":" not in line:
            continue

        name, data = line.split(":", 1)
        name = name.strip()
        if name == "lo":  # Skip loopback
            continue

        fields = data.split()
        if len(fields) < 10:
            continue

        try:
            interfaces[name] = {
                "rx_bytes": int(fields[0]),
                "rx_packets": int(fields[1]),
                "rx_errors": int(fields[2]),
                "tx_bytes": int(fields[8]),
                "tx_packets": int(fields[9]),
                "tx_errors": int(fields[10]),
            }
        except (ValueError, IndexError):
            continue

    return interfaces


def get_disk_usage() -> dict:
    """
    Get disk usage per mount point.
    Uses shutil.disk_usage for each mount point.
    Returns: {"/": {"total": 100, "used": 50, "free": 50, "percent": 50}, ...}
    """
    try:
        import shutil

        usage = shutil.disk_usage("/")
        total = usage.total
        used = usage.used
        free = usage.free
        percent = round((used / total) * 100, 1) if total > 0 else 0.0

        return {
            "/": {
                "total": total,
                "used": used,
                "free": free,
                "percent": percent,
            }
        }
    except Exception:
        return {"/": {"total": 0, "used": 0, "free": 0, "percent": 0}}


def get_cpu_info() -> dict:
    """
    Get CPU model and core information.
    Reads from /proc/cpuinfo.
    Returns: {"model": "Intel Xeon", "cores": 4, "threads": 8}
    """
    content = _read_file("/proc/cpuinfo")
    if not content:
        return {"model": "Unknown", "cores": os.cpu_count() or 1, "threads": os.cpu_count() or 1}

    model_name = "Unknown"
    physical_ids = set()
    cores_per_socket = 0
    processor_count = 0

    for line in content.strip().split("\n"):
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if key == "model name":
            model_name = value
        elif key == "physical id":
            physical_ids.add(value)
        elif key == "cpu cores":
            try:
                cores_per_socket = int(value)
            except ValueError:
                pass
        elif key == "processor":
            try:
                processor_count = max(processor_count, int(value) + 1)
            except ValueError:
                pass

    num_sockets = len(physical_ids) if physical_ids else 1

    # Calculate cores and threads
    if cores_per_socket > 0:
        cores = cores_per_socket * num_sockets
    else:
        # Fallback: assume single socket with processor count as threads
        cores = processor_count

    threads = processor_count if processor_count > 0 else os.cpu_count() or 1

    return {
        "model": model_name,
        "cores": cores,
        "threads": threads,
    }


def get_system_info() -> dict:
    """
    Get overall system information.
    Returns: {"hostname": "server1", "os": "Ubuntu 22.04", "uptime": "5 days", "kernel": "5.15.0"}
    """
    hostname = os.uname().nodename if hasattr(os, "uname") else "Unknown"

    # Get OS info
    os_content = _read_file("/etc/os-release")
    os_name = "Linux"
    if os_content:
        for line in os_content.strip().split("\n"):
            if line.startswith("PRETTY_NAME="):
                os_name = line.split("=", 1)[1].strip('"')
                break

    kernel = os.uname().release if hasattr(os, "uname") else "Unknown"

    # Get uptime
    uptime_str = "Unknown"
    uptime_content = _read_file("/proc/uptime")
    if uptime_content:
        try:
            uptime_seconds = float(uptime_content.split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)

            if days > 0:
                uptime_str = f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''}"
            elif hours > 0:
                uptime_str = f"{hours} hour{'s' if hours != 1 else ''}, {minutes} min"
            else:
                uptime_str = f"{minutes} min"
        except (ValueError, IndexError):
            pass

    return {
        "hostname": hostname,
        "os": os_name,
        "uptime": uptime_str,
        "kernel": kernel,
    }


def get_process_list() -> list:
    """
    Get top processes by CPU/Memory.
    Returns: [{"pid": 1, "name": "systemd", "cpu": 0.1, "mem": 0.5}, ...]
    """
    try:
        import subprocess

        # Get top processes by CPU and memory
        result = subprocess.run(
            ["ps", "aux", "--no-headers"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return []

        processes = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue

            parts = line.split(None, 10)
            if len(parts) < 11:
                continue

            try:
                pid = int(parts[1])
                cpu = float(parts[2])
                mem = float(parts[3])
                name = parts[10] if len(parts) > 10 else parts[10][:50]

                processes.append({
                    "pid": pid,
                    "name": name[:50] if name else "unknown",
                    "cpu": round(cpu, 1),
                    "mem": round(mem, 1),
                })
            except (ValueError, IndexError):
                continue

        # Sort by CPU usage descending and take top 15
        processes.sort(key=lambda x: x["cpu"], reverse=True)
        return processes[:15]
    except Exception:
        return []


def get_all_metrics() -> dict:
    """
    Get all monitoring metrics in one call.
    Returns combined metrics for dashboard.
    """
    load = get_load_average()
    cpu = get_cpu_usage()
    memory = get_memory_usage()
    swap = get_swap_usage()
    disk_io = get_disk_io()
    network_io = get_network_io()
    disk_usage = get_disk_usage()
    cpu_info = get_cpu_info()
    system_info = get_system_info()
    processes = get_process_list()

    return {
        "load": load,
        "cpu": cpu,
        "memory": memory,
        "swap": swap,
        "disk_io": disk_io,
        "network_io": network_io,
        "disk_usage": disk_usage,
        "cpu_info": cpu_info,
        "system_info": system_info,
        "processes": processes,
        "timestamp": time.time(),
    }
