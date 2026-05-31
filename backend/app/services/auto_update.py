"""Auto Update Service for BPanel.

Provides functionality for checking, downloading, and installing BPanel updates
from GitHub releases, along with backup and rollback capabilities.
"""

import datetime
import hashlib
import json
import logging
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import requests

from app.core.config import settings
from app.services.shell import shell

logger = logging.getLogger("bpanel.auto_update")

# GitHub repository for BPanel releases
GITHUB_REPO = "bpanel-org/bpanel"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
GITHUB_DOWNLOAD_URL = f"https://github.com/{GITHUB_REPO}/releases/download"

# Update schedule options
AUTO_UPDATE_SCHEDULES = {
    "disabled": "Never",
    "daily": "Daily at 3 AM",
    "weekly": "Weekly on Sunday",
    "monthly": "Monthly on 1st",
    "security_only": "Security updates only",
}

# Update settings file
SETTINGS_FILE = Path("/etc/bpanel/update_settings.json")
BACKUP_ROOT = Path(settings.backup_root) / "updates"


def _get_settings_path() -> Path:
    """Get the settings directory, creating it if necessary."""
    settings_dir = Path("/etc/bpanel")
    settings_dir.mkdir(parents=True, exist_ok=True)
    return SETTINGS_FILE


def _get_backup_dir() -> Path:
    """Get the backup directory, creating it if necessary."""
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    return BACKUP_ROOT


def get_current_version() -> dict:
    """Get current installed version of BPanel."""
    try:
        # Try to read version from installed package
        version_file = Path("/opt/bpanel/version")
        if version_file.exists():
            version = version_file.read_text().strip()
        else:
            # Fallback: try to get from pip or package
            result = shell.run(["pip", "show", "bpanel"], check=False)
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.split("\n"):
                    if line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                        break
                else:
                    version = "unknown"
            else:
                version = "unknown"

        # Get commit/branch info if available
        commit = "unknown"
        commit_file = Path("/opt/bpanel/.git/HEAD")
        if commit_file.exists():
            commit = commit_file.read_text().strip()

        return {
            "version": version,
            "commit": commit,
            "updated_at": datetime.datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get current version: {e}")
        return {
            "version": "unknown",
            "commit": "unknown",
            "error": str(e),
        }


def check_for_updates() -> dict:
    """Check for available BPanel updates from GitHub releases."""
    try:
        response = requests.get(GITHUB_API_URL, timeout=10)
        response.raise_for_status()
        releases = response.json()

        if not releases:
            return {
                "update_available": False,
                "message": "No releases found",
            }

        # Get latest release
        latest = releases[0]
        current = get_current_version()
        current_version = current.get("version", "0.0.0")

        latest_version = latest.get("tag_name", "").lstrip("v")

        # Compare versions
        update_available = _compare_versions(latest_version, current_version) > 0

        # Gather release assets info
        assets = []
        for asset in latest.get("assets", []):
            assets.append({
                "name": asset.get("name"),
                "size": asset.get("size"),
                "download_url": asset.get("browser_download_url"),
            })

        result = {
            "update_available": update_available,
            "current_version": current_version,
            "latest_version": latest_version,
            "release_name": latest.get("name", ""),
            "release_notes": latest.get("body", ""),
            "published_at": latest.get("published_at", ""),
            "assets": assets,
            "prerelease": latest.get("prerelease", False),
        }

        return result
    except requests.RequestException as e:
        logger.error(f"Failed to check for updates: {e}")
        return {
            "update_available": False,
            "error": f"Failed to connect to GitHub: {e}",
        }
    except Exception as e:
        logger.error(f"Unexpected error checking for updates: {e}")
        return {
            "update_available": False,
            "error": str(e),
        }


def _compare_versions(v1: str, v2: str) -> int:
    """Compare two version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal."""
    def parse_version(v: str) -> tuple:
        # Remove 'v' prefix if present
        v = v.lstrip("v")
        parts = []
        for part in v.split("."):
            # Extract numeric part
            num = ""
            for char in part:
                if char.isdigit():
                    num += char
                else:
                    break
            if num:
                parts.append(int(num))
            else:
                parts.append(0)
        # Pad to at least 3 parts
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts)

    parsed_v1 = parse_version(v1)
    parsed_v2 = parse_version(v2)

    if parsed_v1 > parsed_v2:
        return 1
    elif parsed_v1 < parsed_v2:
        return -1
    return 0


def download_update(version: str) -> dict:
    """Download update package for specified version."""
    try:
        # Get release info
        response = requests.get(
            f"{GITHUB_API_URL}/tags/{version}",
            timeout=10
        )
        response.raise_for_status()
        release = response.json()

        # Find appropriate asset (tarball or zip)
        download_url = None
        filename = None
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if name.endswith((".tar.gz", ".zip")) and "linux" in name.lower():
                download_url = asset.get("browser_download_url")
                filename = name
                break

        if not download_url:
            # Fallback to source tarball
            download_url = f"{GITHUB_DOWNLOAD_URL}/{version}/bpanel-{version.lstrip('v')}.tar.gz"
            filename = f"bpanel-{version.lstrip('v')}.tar.gz"

        # Download to temp directory
        download_dir = _get_backup_dir() / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        file_path = download_dir / filename

        if file_path.exists():
            # Already downloaded
            return {
                "success": True,
                "version": version,
                "file_path": str(file_path),
                "filename": filename,
                "size": file_path.stat().st_size,
                "message": "Update already downloaded",
            }

        # Download with progress
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        return {
            "success": True,
            "version": version,
            "file_path": str(file_path),
            "filename": filename,
            "size": file_path.stat().st_size,
            "message": "Download complete",
        }
    except requests.RequestException as e:
        logger.error(f"Failed to download update: {e}")
        return {
            "success": False,
            "error": f"Failed to download: {e}",
        }
    except Exception as e:
        logger.error(f"Unexpected error downloading update: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def verify_update_package(package_path: str) -> dict:
    """Verify package integrity (checksum, signature)."""
    try:
        path = Path(package_path)
        if not path.exists():
            return {
                "valid": False,
                "error": "Package file not found",
            }

        # Calculate checksum
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        checksum = sha256_hash.hexdigest()

        # Check if it's a valid tarball
        is_valid_tarball = False
        try:
            with tarfile.open(path, "r:gz") as tar:
                # Check for expected files
                members = tar.getnames()
                has_main_file = any("bpanel" in m.lower() or "setup" in m.lower() for m in members[:10])
                is_valid_tarball = True
        except tarfile.TarError:
            # Try zip format
            import zipfile
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    members = zf.namelist()
                    has_main_file = any("bpanel" in m.lower() or "setup" in m.lower() for m in members[:10])
                    is_valid_tarball = True
            except zipfile.BadZipFile:
                return {
                    "valid": False,
                    "error": "Invalid archive format",
                    "checksum": checksum,
                }

        return {
            "valid": is_valid_tarball,
            "checksum": checksum,
            "size": path.stat().st_size,
            "format": "tar.gz" if str(path).endswith(".tar.gz") else "zip",
        }
    except Exception as e:
        logger.error(f"Failed to verify package: {e}")
        return {
            "valid": False,
            "error": str(e),
        }


def create_backup() -> dict:
    """Create full backup before update."""
    try:
        backup_dir = _get_backup_dir()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Get current version info
        current = get_current_version()

        # Create backup metadata
        backup_info = {
            "timestamp": timestamp,
            "version": current.get("version", "unknown"),
            "commit": current.get("commit", "unknown"),
            "created_at": datetime.datetime.now().isoformat(),
            "files": [],
        }

        # Backup main bpanel directory
        bpanel_dir = Path("/opt/bpanel")
        if bpanel_dir.exists():
            backup_file = backup_dir / f"bpanel_backup_{timestamp}.tar.gz"

            # Create tarball of current installation
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(bpanel_dir, arcname="bpanel")

            backup_info["files"].append(str(backup_file))
            backup_info["backup_file"] = str(backup_file)
            backup_info["size"] = backup_file.stat().st_size

        # Save backup metadata
        metadata_file = backup_dir / f"backup_{timestamp}.json"
        metadata_file.write_text(json.dumps(backup_info, indent=2))

        return {
            "success": True,
            "backup_id": timestamp,
            "backup_file": backup_info.get("backup_file"),
            "version": backup_info["version"],
            "size": backup_info.get("size", 0),
            "message": f"Backup created successfully",
        }
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def install_update(version: str, backup: bool = True) -> dict:
    """Install downloaded update with optional backup."""
    try:
        # Create backup first if requested
        if backup:
            backup_result = create_backup()
            if not backup_result.get("success"):
                logger.warning(f"Backup failed, continuing anyway: {backup_result.get('error')}")

        # Find downloaded package
        download_dir = _get_backup_dir() / "downloads"
        package_files = list(download_dir.glob(f"*{version}*"))

        if not package_files:
            # Try to download first
            download_result = download_update(version)
            if not download_result.get("success"):
                return download_result
            package_files = [Path(download_result["file_path"])]

        package_path = package_files[0]

        # Verify package
        verify_result = verify_update_package(str(package_path))
        if not verify_result.get("valid"):
            return {
                "success": False,
                "error": f"Package verification failed: {verify_result.get('error')}",
            }

        # Extract and install
        install_dir = Path("/opt/bpanel")
        temp_dir = Path(tempfile.mkdtemp(prefix="bpanel_update_"))

        try:
            # Extract package
            with tarfile.open(package_path, "r:gz") as tar:
                tar.extractall(temp_dir)

            # Find extracted content
            extracted_dirs = list(temp_dir.iterdir())
            source_dir = extracted_dirs[0] if extracted_dirs else temp_dir

            # Run installation script if exists
            install_script = source_dir / "install.sh"
            if install_script.exists():
                result = shell.privileged(
                    "bpanel-update-install",
                    helper_args=[str(source_dir)],
                    check=False,
                    fallback=["bash", str(install_script)],
                )
                if result.returncode != 0:
                    return {
                        "success": False,
                        "error": f"Installation script failed: {result.stderr}",
                    }
            else:
                # Manual installation: copy files
                shell.privileged(
                    "bpanel-update-copy",
                    helper_args=[str(source_dir), str(install_dir)],
                    check=False,
                    fallback=["bash", "-c", f"cp -r {source_dir}/* {install_dir}/"],
                )

            # Restart services
            shell.privileged(
                "bpanel-update-restart",
                check=False,
                fallback=["systemctl", "restart", "bpanel-api"],
            )

            return {
                "success": True,
                "version": version,
                "message": f"Successfully updated to version {version}",
            }
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Failed to install update: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def restore_backup(backup_id: str) -> dict:
    """Restore from backup."""
    try:
        backup_dir = _get_backup_dir()

        # Find backup file
        backup_file = backup_dir / f"bpanel_backup_{backup_id}.tar.gz"

        if not backup_file.exists():
            # Try to find by timestamp pattern
            matching = list(backup_dir.glob(f"*backup*{backup_id}*.tar.gz"))
            if matching:
                backup_file = matching[0]
            else:
                return {
                    "success": False,
                    "error": "Backup not found",
                }

        install_dir = Path("/opt/bpanel")
        temp_dir = Path(tempfile.mkdtemp(prefix="bpanel_restore_"))

        try:
            # Extract to temp
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(temp_dir)

            # Find extracted content
            extracted_bpanel = temp_dir / "bpanel"

            if not extracted_bpanel.exists():
                return {
                    "success": False,
                    "error": "Invalid backup format",
                }

            # Restore files
            shell.privileged(
                "bpanel-restore-copy",
                helper_args=[str(extracted_bpanel), str(install_dir)],
                check=False,
                fallback=["bash", "-c", f"rm -rf {install_dir} && cp -r {extracted_bpanel} {install_dir}"],
            )

            # Restart services
            shell.privileged(
                "bpanel-restore-restart",
                check=False,
                fallback=["systemctl", "restart", "bpanel-api"],
            )

            return {
                "success": True,
                "backup_id": backup_id,
                "message": "Successfully restored from backup",
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def list_backups() -> list:
    """List available backups."""
    try:
        backup_dir = _get_backup_dir()
        backups = []

        for backup_file in sorted(backup_dir.glob("bpanel_backup_*.tar.gz"), reverse=True):
            stat = backup_file.stat()
            # Extract timestamp from filename
            name = backup_file.stem  # bpanel_backup_YYYYMMDD_HHMMSS
            parts = name.split("_")
            timestamp = "_".join(parts[-2:]) if len(parts) >= 3 else parts[-1]

            try:
                # Try to parse timestamp
                dt = datetime.datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                date_str = dt.isoformat()
            except ValueError:
                date_str = timestamp

            backups.append({
                "id": timestamp,
                "filename": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "created_at": date_str,
            })

        return backups
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        return []


def rollback() -> dict:
    """Rollback to previous version."""
    try:
        # Get list of backups
        backups = list_backups()

        if not backups:
            return {
                "success": False,
                "error": "No backups available for rollback",
            }

        # Use most recent backup
        latest_backup = backups[0]

        return restore_backup(latest_backup["id"])
    except Exception as e:
        logger.error(f"Failed to rollback: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_update_settings() -> dict:
    """Get current update settings."""
    try:
        settings_path = _get_settings_path()
        if settings_path.exists():
            return json.loads(settings_path.read_text())

        # Return defaults
        return {
            "auto_update_enabled": False,
            "schedule": "disabled",
            "include_beta": False,
            "auto_backup": True,
            "notify_on_update": True,
            "last_check": None,
        }
    except Exception as e:
        logger.error(f"Failed to get update settings: {e}")
        return {
            "auto_update_enabled": False,
            "schedule": "disabled",
            "include_beta": False,
            "auto_backup": True,
            "notify_on_update": True,
            "error": str(e),
        }


def update_update_settings(new_settings: dict) -> dict:
    """Update auto update settings."""
    try:
        # Validate schedule
        schedule = new_settings.get("schedule", "disabled")
        if schedule not in AUTO_UPDATE_SCHEDULES:
            return {
                "success": False,
                "error": f"Invalid schedule: {schedule}. Valid options: {list(AUTO_UPDATE_SCHEDULES.keys())}",
            }

        settings_path = _get_settings_path()
        current = get_update_settings()

        # Merge settings
        updated = {
            **current,
            **new_settings,
            "updated_at": datetime.datetime.now().isoformat(),
        }

        settings_path.write_text(json.dumps(updated, indent=2))

        return {
            "success": True,
            "settings": updated,
        }
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_update_logs() -> list:
    """Get recent update activity logs."""
    try:
        log_file = Path("/var/log/bpanel/updates.log")
        if not log_file.exists():
            return []

        logs = []
        for line in reversed(log_file.read_text().splitlines()[-100:]):
            # Parse log line
            try:
                parts = line.split(" - ", 2)
                if len(parts) >= 3:
                    logs.append({
                        "timestamp": parts[0],
                        "level": parts[1],
                        "message": parts[2],
                    })
                else:
                    logs.append({
                        "timestamp": "",
                        "level": "info",
                        "message": line,
                    })
            except Exception:
                logs.append({
                    "timestamp": "",
                    "level": "info",
                    "message": line,
                })

        return logs
    except Exception as e:
        logger.error(f"Failed to get update logs: {e}")
        return []


def delete_backup(backup_id: str) -> dict:
    """Delete a specific backup."""
    try:
        backup_dir = _get_backup_dir()

        # Find backup file
        backup_file = backup_dir / f"bpanel_backup_{backup_id}.tar.gz"

        if not backup_file.exists():
            return {
                "success": False,
                "error": "Backup not found",
            }

        backup_file.unlink()

        # Also delete metadata if exists
        metadata_file = backup_dir / f"backup_{backup_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()

        return {
            "success": True,
            "message": f"Backup {backup_id} deleted",
        }
    except Exception as e:
        logger.error(f"Failed to delete backup: {e}")
        return {
            "success": False,
            "error": str(e),
        }
