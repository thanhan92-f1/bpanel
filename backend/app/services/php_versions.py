"""
PHP Version Management Service

Provides comprehensive management for multiple PHP versions from PHP 5.2 to PHP 8.5.
Supports installation, configuration, extension management, FPM pool configuration, and optimization.
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from app.services.shell import shell


# Supported PHP version range: 5.2 to 8.5
SUPPORTED_PHP_VERSIONS = [
    "5.2", "5.3", "5.4", "5.5", "5.6",
    "7.0", "7.1", "7.2", "7.3", "7.4",
    "8.0", "8.1", "8.2", "8.3", "8.4", "8.5"
]

# Common PHP extensions available for installation
COMMON_PHP_EXTENSIONS = [
    "cli", "fpm", "common", "mbstring", "xml", "yaml", "curl", "gd", "imagick",
    "mysql", "mysqli", "pdo", "pdo_mysql", "pgsql", "pdo_pgsql", "sqlite3", "pdo_sqlite",
    "zip", "bz2", "zlib", "memcached", "redis", "opcache", "apcu",
    "soap", "xmlrpc", "mcrypt", "bcmath", "gmp", "intl", "ldap",
    "imap", "snmp", "pspell", "tidy", "geoip", "raphf", "raphfe", "propro",
    "ssh2", "sockets", "event", "enchant", "haru", "k-taglib", "oauth",
    "pgi", "ps", "rdkafka", "stomp", "uv", "vips", "xdebug", "xhprof",
    "ioncube-loader", "sourceguardian", "suhosin", "uploadprogress",
]


def _validate_php_version(version: str) -> str:
    """Validate that a PHP version is supported."""
    if version not in SUPPORTED_PHP_VERSIONS:
        raise ValueError(f"Unsupported PHP version: {version}. Supported versions: {SUPPORTED_PHP_VERSIONS}")
    return version


def _safe_ini_value(value: str) -> str:
    """Sanitize PHP ini value to prevent injection."""
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError("Invalid PHP ini value")
    return value


def _get_php_service_name(version: str) -> str:
    """Get the PHP-FPM service name for a version."""
    return f"php{version}-fpm"


def _get_php_config_paths(version: str) -> dict:
    """Get configuration file paths for a PHP version."""
    return {
        "php_ini": f"/etc/php/{version}/fpm/php.ini",
        "pool_dir": f"/etc/php/{version}/fpm/pool.d",
        "conf_d": f"/etc/php/{version}/fpm/conf.d",
    }


# =============================================================================
# Version Management
# =============================================================================

def list_installed_php_versions() -> dict:
    """
    List all installed PHP versions on the system.
    Returns dict with list of installed versions and their status.
    """
    installed = []

    for version in SUPPORTED_PHP_VERSIONS:
        php_bin = f"/usr/bin/php{version}"
        fpm_service = _get_php_service_name(version)

        # Check if PHP binary exists
        result = shell.run(["test", "-f", php_bin], check=False)
        php_installed = result.returncode == 0

        # Check if FPM service exists
        service_check = shell.run(["systemctl", "list-unit-files", f"{fpm_service}.service"], check=False)
        service_installed = fpm_service in service_check.stdout

        # Check service status if installed
        fpm_running = False
        fpm_status = "unknown"
        if service_installed:
            status_result = shell.run(["systemctl", "is-active", fpm_service], check=False)
            fpm_running = status_result.stdout.strip() == "active"
            fpm_status = "running" if fpm_running else "stopped"

        # Get PHP version info if installed
        php_version_info = None
        if php_installed:
            try:
                version_result = shell.run(["php", version, "-v"], check=False)
                if version_result.returncode == 0:
                    first_line = version_result.stdout.splitlines()[0] if version_result.stdout else ""
                    php_version_info = first_line
            except Exception:
                pass

        installed.append({
            "version": version,
            "php_installed": php_installed,
            "fpm_installed": service_installed,
            "fpm_running": fpm_running,
            "fpm_status": fpm_status,
            "php_version_string": php_version_info,
            "config_path": f"/etc/php/{version}/fpm/php.ini" if php_installed else None,
        })

    return {
        "installed_versions": [v for v in installed if v["php_installed"]],
        "all_versions": installed,
        "count": len([v for v in installed if v["php_installed"]])
    }


def list_available_php_versions() -> dict:
    """
    List available PHP versions from Ondrej PPA.
    Returns both available and installed versions.
    """
    try:
        # Check if Ondrej PPA is available
        result = shell.run(["apt-cache", "search", "^php[0-9]"], check=False)

        available = []
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                # Parse packages like "php8.3-fpm - PHP 8.3 FPM"
                match = re.match(r"^(php[\d.]+)-(\S+)", line)
                if match:
                    version = match.group(1).replace("php", "")
                    package_type = match.group(2)
                    pkg_name = match.group(0)

                    if package_type == "fpm":
                        available.append({
                            "version": version,
                            "package": pkg_name,
                            "type": "fpm",
                            "description": line.split("-", 2)[-1] if "-" in line else ""
                        })

        # Check which are already installed
        installed_result = list_installed_php_versions()
        installed_versions = {v["version"] for v in installed_result["all_versions"] if v["php_installed"]}

        for av in available:
            av["installed"] = av["version"] in installed_versions

        return {
            "available_versions": available,
            "supported_range": {
                "min": "5.2",
                "max": "8.5"
            },
            "ppa_source": "ondrej/php"
        }
    except Exception as e:
        return {
            "available_versions": [],
            "error": str(e),
            "supported_range": {"min": "5.2", "max": "8.5"}
        }


def install_php_version(version: str) -> dict:
    """
    Install a specific PHP version from Ondrej PPA.
    Installs both CLI and FPM packages.
    """
    version = _validate_php_version(version)

    try:
        # Check if already installed
        php_bin = f"/usr/bin/php{version}"
        if shell.run(["test", "-f", php_bin], check=False).returncode == 0:
            return {
                "version": version,
                "success": True,
                "message": f"PHP {version} is already installed",
                "already_installed": True
            }

        # Update package list
        shell.run(["apt-get", "update"], check=True)

        # Install PHP version packages
        packages = [
            f"php{version}-cli",
            f"php{version}-fpm",
            f"php{version}-common",
            f"php{version}-mysql",
            f"php{version}-xml",
            f"php{version}-mbstring",
            f"php{version}-zip",
            f"php{version}-curl",
            f"php{version}-gd",
        ]

        for package in packages:
            result = shell.run(
                ["apt-get", "install", "-y", package],
                check=False
            )
            if result.returncode != 0:
                # Package might not exist for this version
                pass

        # Enable and start FPM service
        service_name = _get_php_service_name(version)
        shell.run(["systemctl", "enable", service_name], check=False)
        shell.run(["systemctl", "start", service_name], check=False)

        return {
            "version": version,
            "success": True,
            "message": f"PHP {version} installed successfully",
            "service": service_name,
            "packages": packages
        }
    except Exception as e:
        return {
            "version": version,
            "success": False,
            "error": str(e)
        }


def remove_php_version(version: str) -> dict:
    """
    Remove a specific PHP version.
    """
    version = _validate_php_version(version)

    try:
        # Stop and disable FPM service
        service_name = _get_php_service_name(version)
        shell.run(["systemctl", "stop", service_name], check=False)
        shell.run(["systemctl", "disable", service_name], check=False)

        # Remove packages
        packages = [
            f"php{version}-cli",
            f"php{version}-fpm",
            f"php{version}-common",
            f"php{version}-mysql",
            f"php{version}-xml",
            f"php{version}-mbstring",
            f"php{version}-zip",
            f"php{version}-curl",
            f"php{version}-gd",
        ]

        for package in packages:
            shell.run(["apt-get", "remove", "-y", package], check=False)

        return {
            "version": version,
            "success": True,
            "message": f"PHP {version} removed successfully"
        }
    except Exception as e:
        return {
            "version": version,
            "success": False,
            "error": str(e)
        }


# =============================================================================
# Extension Management
# =============================================================================

def get_php_extensions(version: str) -> dict:
    """
    List all available and installed extensions for a PHP version.
    """
    version = _validate_php_version(version)

    try:
        # Get list of compiled-in modules
        result = shell.run(["php", version, "-m"], check=False)
        loaded_extensions = set()
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and not line.startswith("["):
                    loaded_extensions.add(line.lower())

        # Check for common extensions availability
        available = []
        for ext in COMMON_PHP_EXTENSIONS:
            package_name = f"php{version}-{ext}"
            check = shell.run(["dpkg", "-s", package_name], check=False)
            package_installed = check.returncode == 0

            available.append({
                "extension": ext,
                "package": package_name,
                "installed": ext.lower() in loaded_extensions,
                "package_installed": package_installed,
                "available": True
            })

        return {
            "version": version,
            "extensions": available,
            "loaded_count": len(loaded_extensions),
            "available_count": len(available)
        }
    except Exception as e:
        return {
            "version": version,
            "extensions": [],
            "error": str(e)
        }


def install_php_extension(version: str, extension: str) -> dict:
    """
    Install a PHP extension for a specific version.
    """
    version = _validate_php_version(version)
    extension = _safe_ini_value(extension)

    try:
        package_name = f"php{version}-{extension}"

        # Check if package exists
        result = shell.run(["apt-cache", "show", package_name], check=False)
        if result.returncode != 0:
            return {
                "version": version,
                "extension": extension,
                "success": False,
                "error": f"Package {package_name} not found"
            }

        # Install the package
        shell.run(["apt-get", "install", "-y", package_name], check=True)

        # Restart PHP-FPM to load the extension
        restart_php_fpm(version)

        return {
            "version": version,
            "extension": extension,
            "success": True,
            "message": f"Extension {extension} installed for PHP {version}"
        }
    except Exception as e:
        return {
            "version": version,
            "extension": extension,
            "success": False,
            "error": str(e)
        }


def remove_php_extension(version: str, extension: str) -> dict:
    """
    Remove a PHP extension for a specific version.
    """
    version = _validate_php_version(version)
    extension = _safe_ini_value(extension)

    try:
        package_name = f"php{version}-{extension}"

        # Remove the package
        shell.run(["apt-get", "remove", "-y", package_name], check=True)

        # Restart PHP-FPM
        restart_php_fpm(version)

        return {
            "version": version,
            "extension": extension,
            "success": True,
            "message": f"Extension {extension} removed from PHP {version}"
        }
    except Exception as e:
        return {
            "version": version,
            "extension": extension,
            "success": False,
            "error": str(e)
        }


# =============================================================================
# Configuration Management
# =============================================================================

def get_php_config(version: str) -> dict:
    """
    Get current php.ini settings for a PHP version.
    Returns all configuration options as a dictionary.
    """
    version = _validate_php_version(version)

    # Default configuration values
    config = {
        "version": version,
        "config_file": f"/etc/php/{version}/fpm/php.ini",
        # Upload & Timeout Limits
        "upload_max_filesize": "128M",
        "post_max_size": "128M",
        "max_execution_time": "300",
        "max_input_time": "600",
        "max_input_vars": "10000",
        "memory_limit": "512M",
        # Disabled Functions
        "disable_functions": [],
        # Optimization Settings
        "opcache.enable": "1",
        "opcache.memory_consumption": "128",
        "opcache.max_accelerated_files": "10000",
        "opcache.validate_timestamps": "1",
        "realpath_cache_size": "4096K",
        # Session Configuration
        "session.save_handler": "files",
        "session.save_path": "/var/lib/php/sessions",
        "session.gc_maxlifetime": "1440",
        # Logging
        "error_reporting": "E_ALL & ~E_DEPRECATED & ~E_STRICT",
        "error_log": f"/var/log/php/{version}-fpm-error.log",
        "log_errors": "1",
        "display_errors": "Off",
        "slowlog": f"/var/log/php/{version}-fpm-slow.log",
        "request_slowlog_timeout": "10s",
    }

    # Read configuration from php.ini
    php_ini_path = Path(f"/etc/php/{version}/fpm/php.ini")
    if php_ini_path.exists():
        content = php_ini_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(";") or "=" not in line:
                continue
            key, value = [part.strip() for part in line.split("=", 1)]
            if key in config:
                config[key] = value

    # Read additional config from conf.d
    conf_d_path = Path(f"/etc/php/{version}/fpm/conf.d")
    if conf_d_path.exists():
        for conf_file in sorted(conf_d_path.glob("*.ini")):
            if conf_file.name.startswith("99-"):
                continue  # Skip bpanel managed files
            content = conf_file.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith(";") or "=" not in line:
                    continue
                key, value = [part.strip() for part in line.split("=", 1)]
                if key in config:
                    config[key] = value

    # Parse disable_functions from array format
    if isinstance(config["disable_functions"], str):
        config["disable_functions"] = [
            f.strip() for f in config["disable_functions"].split(",") if f.strip()
        ]

    return config


def update_php_config(version: str, settings: dict) -> dict:
    """
    Update php.ini settings for a PHP version.
    Creates/updates a separate config file in conf.d for bpanel-managed settings.
    """
    version = _validate_php_version(version)

    try:
        paths = _get_php_config_paths(version)
        conf_file = Path(f"/etc/php/{version}/fpm/conf.d/99-bpanel.ini")

        # Build configuration content
        lines = [
            "; BPanel Managed PHP Configuration",
            "; Auto-generated - Do not edit manually",
            "",
        ]

        # Process each setting
        for key, value in settings.items():
            if key in ("version", "config_file"):
                continue

            if key == "disable_functions":
                if isinstance(value, list):
                    value = ",".join(value)
                lines.append(f"{key} = {value}")
            elif isinstance(value, bool):
                lines.append(f"{key} = {'On' if value else 'Off'}")
            elif isinstance(value, int):
                lines.append(f"{key} = {value}")
            else:
                lines.append(f"{key} = {_safe_ini_value(str(value))}")

        # Write configuration file
        conf_file.parent.mkdir(parents=True, exist_ok=True)
        conf_file.write_text("\n".join(lines), encoding="utf-8")

        # Restart PHP-FPM
        restart_php_fpm(version)

        return {
            "version": version,
            "success": True,
            "config_file": str(conf_file),
            "settings_updated": list(settings.keys())
        }
    except Exception as e:
        return {
            "version": version,
            "success": False,
            "error": str(e)
        }


def optimize_php(version: str, settings: dict) -> dict:
    """
    Apply optimization settings for a PHP version.
    Combines multiple optimization options for production use.
    """
    version = _validate_php_version(version)

    # Default optimization settings
    optimization_defaults = {
        "opcache.enable": "1",
        "opcache.memory_consumption": "256",
        "opcache.max_accelerated_files": "20000",
        "opcache.validate_timestamps": "0",
        "realpath_cache_size": "4096K",
        "realpath_cache_ttl": "600",
        "max_execution_time": "300",
        "max_input_time": "600",
        "memory_limit": "512M",
        "display_errors": "Off",
        "log_errors": "1",
    }

    # Apply custom settings over defaults
    final_settings = {**optimization_defaults, **settings}

    return update_php_config(version, final_settings)


# =============================================================================
# FPM Pool Management
# =============================================================================

def get_php_fpm_pools(version: str) -> dict:
    """
    List FPM pool configurations for a PHP version.
    """
    version = _validate_php_version(version)

    pools = []
    pool_dir = Path(f"/etc/php/{version}/fpm/pool.d")

    if pool_dir.exists():
        for pool_file in pool_dir.glob("*.conf"):
            pool_name = pool_file.stem
            content = pool_file.read_text(encoding="utf-8", errors="ignore")

            pool_config = {
                "name": pool_name,
                "file": str(pool_file),
                "enabled": True,
                "settings": {}
            }

            # Parse key settings
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith(";") or line.startswith("["):
                    continue
                if "=" in line:
                    key, value = [part.strip() for part in line.split("=", 1)]
                    pool_config["settings"][key] = value

            pools.append(pool_config)

    return {
        "version": version,
        "pools": pools,
        "pool_count": len(pools)
    }


def create_php_fpm_pool(version: str, pool_name: str, settings: dict) -> dict:
    """
    Create a new FPM pool configuration.
    """
    version = _validate_php_version(version)
    pool_name = _safe_ini_value(pool_name)

    # Validate pool name
    if not re.match(r"^[a-zA-Z0-9_-]+$", pool_name):
        return {
            "version": version,
            "pool_name": pool_name,
            "success": False,
            "error": "Invalid pool name. Use only alphanumeric characters, hyphens, and underscores."
        }

    try:
        pool_dir = Path(f"/etc/php/{version}/fpm/pool.d")
        pool_dir.mkdir(parents=True, exist_ok=True)

        pool_file = pool_dir / f"{pool_name}.conf"

        if pool_file.exists():
            return {
                "version": version,
                "pool_name": pool_name,
                "success": False,
                "error": f"Pool {pool_name} already exists"
            }

        # Default pool configuration
        default_settings = {
            "listen": f"/var/run/php/php{version}-fpm-{pool_name}.sock",
            "listen.owner": "www-data",
            "listen.group": "www-data",
            "listen.mode": "0660",
            "user": "www-data",
            "group": "www-data",
            "pm": "dynamic",
            "pm.max_children": "10",
            "pm.start_servers": "2",
            "pm.min_spare_servers": "1",
            "pm.max_spare_servers": "3",
            "pm.max_requests": "500",
            "pm.process_idle_timeout": "10s",
            "pm.status_path": f"/status-{pool_name}",
            "ping.path": f"/ping-{pool_name}",
            "slowlog": f"/var/log/php/{version}-fpm-{pool_name}-slow.log",
            "request_slowlog_timeout": "10s",
        }

        # Merge with custom settings
        final_settings = {**default_settings, **settings}

        # Generate pool configuration
        lines = [
            f"[{pool_name}]",
            "",
        ]
        for key, value in final_settings.items():
            lines.append(f"{key} = {value}")

        pool_file.write_text("\n".join(lines), encoding="utf-8")

        # Test configuration
        test_result = shell.run(
            [f"/usr/sbin/php-fpm{version}", "-t", "-y", str(pool_file)],
            check=False
        )
        if test_result.returncode != 0:
            pool_file.unlink()
            return {
                "version": version,
                "pool_name": pool_name,
                "success": False,
                "error": f"Configuration test failed: {test_result.stderr}"
            }

        # Restart PHP-FPM
        restart_php_fpm(version)

        return {
            "version": version,
            "pool_name": pool_name,
            "success": True,
            "pool_file": str(pool_file),
            "settings": final_settings
        }
    except Exception as e:
        return {
            "version": version,
            "pool_name": pool_name,
            "success": False,
            "error": str(e)
        }


def update_php_fpm_pool(version: str, pool_name: str, settings: dict) -> dict:
    """
    Update an existing FPM pool configuration.
    """
    version = _validate_php_version(version)
    pool_name = _safe_ini_value(pool_name)

    try:
        pool_file = Path(f"/etc/php/{version}/fpm/pool.d/{pool_name}.conf")

        if not pool_file.exists():
            return {
                "version": version,
                "pool_name": pool_name,
                "success": False,
                "error": f"Pool {pool_name} not found"
            }

        # Read existing configuration
        content = pool_file.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()

        # Update settings
        for key, value in settings.items():
            found = False
            new_lines = []
            for line in lines:
                if line.strip().startswith(f"{key} ="):
                    new_lines.append(f"{key} = {value}")
                    found = True
                else:
                    new_lines.append(line)

            if found:
                lines = new_lines
            else:
                # Add new setting
                lines.append(f"{key} = {value}")

        # Write updated configuration
        pool_file.write_text("\n".join(lines), encoding="utf-8")

        # Restart PHP-FPM
        restart_php_fpm(version)

        return {
            "version": version,
            "pool_name": pool_name,
            "success": True,
            "pool_file": str(pool_file),
            "settings_updated": list(settings.keys())
        }
    except Exception as e:
        return {
            "version": version,
            "pool_name": pool_name,
            "success": False,
            "error": str(e)
        }


def restart_php_fpm(version: str) -> dict:
    """
    Restart PHP-FPM service for a specific version.
    """
    version = _validate_php_version(version)

    try:
        service_name = _get_php_service_name(version)

        # Check if service exists
        check = shell.run(["systemctl", "list-unit-files", f"{service_name}.service"], check=False)
        if service_name not in check.stdout:
            return {
                "version": version,
                "success": False,
                "error": f"PHP-FPM service for version {version} not found"
            }

        # Restart the service
        result = shell.run(["systemctl", "restart", service_name], check=False)

        if result.returncode != 0:
            return {
                "version": version,
                "success": False,
                "error": result.stderr
            }

        return {
            "version": version,
            "service": service_name,
            "success": True,
            "message": f"PHP-FPM {version} restarted successfully"
        }
    except Exception as e:
        return {
            "version": version,
            "success": False,
            "error": str(e)
        }


def get_php_fpm_load(version: str) -> dict:
    """
    Get PHP-FPM status and load information.
    Uses the FPM status page to get process information.
    """
    version = _validate_php_version(version)

    try:
        service_name = _get_php_service_name(version)

        # Check if service is running
        status_result = shell.run(["systemctl", "is-active", service_name], check=False)
        running = status_result.stdout.strip() == "active"

        # Get process info
        processes = []
        ps_result = shell.run(
            ["ps", "aux"],
            check=False
        )
        if ps_result.returncode == 0:
            for line in ps_result.stdout.splitlines():
                if f"php-fpm: pool" in line and f"{version}" in line:
                    parts = line.split()
                    if len(parts) >= 11:
                        processes.append({
                            "pid": parts[1],
                            "user": parts[0],
                            "cpu": parts[2],
                            "memory": parts[3],
                            "command": " ".join(parts[10:])
                        })

        # Get memory info
        memory_info = {}
        for proc in processes:
            try:
                pid = proc["pid"]
                mem_result = shell.run(
                    ["cat", f"/proc/{pid}/status"],
                    check=False
                )
                if mem_result.returncode == 0:
                    for line in mem_result.stdout.splitlines():
                        if line.startswith("VmRSS:"):
                            memory_info[pid] = line.split()[1] + " kB"
                            break
            except Exception:
                pass

        # Get process count
        process_count = len(processes)

        return {
            "version": version,
            "service": service_name,
            "running": running,
            "process_count": process_count,
            "processes": processes[:20],  # Limit to 20 processes
            "memory_info": memory_info
        }
    except Exception as e:
        return {
            "version": version,
            "success": False,
            "error": str(e)
        }


# =============================================================================
# Logging & Diagnostics
# =============================================================================

def get_php_slow_log(version: str, lines: int = 100) -> dict:
    """
    Get PHP-FPM slow query log for a version.
    """
    version = _validate_php_version(version)

    try:
        slowlog_paths = [
            f"/var/log/php/{version}-fpm-slow.log",
            f"/var/log/php{version}-fpm-slow.log",
            f"/var/log/php-fpm{version}-slow.log",
        ]

        log_content = ""
        log_path = None

        for path in slowlog_paths:
            if Path(path).exists():
                log_path = path
                result = shell.run(["tail", "-n", str(lines), path], check=False)
                if result.returncode == 0:
                    log_content = result.stdout
                break

        return {
            "version": version,
            "slowlog_path": log_path,
            "lines": lines,
            "content": log_content,
            "exists": log_path is not None
        }
    except Exception as e:
        return {
            "version": version,
            "error": str(e),
            "content": ""
        }


def get_phpinfo(version: str) -> dict:
    """
    Get phpinfo() output for a PHP version.
    """
    version = _validate_php_version(version)

    try:
        # Check if PHP is installed
        result = shell.run(["php", version, "-i"], check=False)
        if result.returncode != 0:
            return {
                "version": version,
                "success": False,
                "error": f"PHP {version} not installed"
            }

        return {
            "version": version,
            "success": True,
            "phpinfo": result.stdout,
            "lines": len(result.stdout.splitlines())
        }
    except Exception as e:
        return {
            "version": version,
            "success": False,
            "error": str(e)
        }


def get_php_error_log(version: str, lines: int = 100) -> dict:
    """
    Get PHP-FPM error log for a version.
    """
    version = _validate_php_version(version)

    try:
        error_log_paths = [
            f"/var/log/php/{version}-fpm-error.log",
            f"/var/log/php{version}-fpm-error.log",
            f"/var/log/php-fpm/error.log",
        ]

        log_content = ""
        log_path = None

        for path in error_log_paths:
            if Path(path).exists():
                log_path = path
                result = shell.run(["tail", "-n", str(lines), path], check=False)
                if result.returncode == 0:
                    log_content = result.stdout
                break

        return {
            "version": version,
            "errorlog_path": log_path,
            "lines": lines,
            "content": log_content,
            "exists": log_path is not None
        }
    except Exception as e:
        return {
            "version": version,
            "error": str(e),
            "content": ""
        }
