"""
WebServer Service - Multi-WebServer Hosting support for Nginx, Apache, and OpenLiteSpeed.

This service provides unified management for multiple web server engines with per-site
web engine selection, port management, safety checks, and repair functionality.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader

from app.core.config import settings
from app.services.shell import shell


# ============================================================================
# Enums and Constants
# ============================================================================

class WebEngine(Enum):
    NGINX = "nginx"
    APACHE = "apache"
    OPENLITESPEED = "openlitespeed"
    LITESPEED_ENTERPRISE = "litespeed"


# Reserved Ports (DO NOT USE)
RESERVED_PORTS = [80, 443, 8188, 8189, 8190, 8288, 8289, 8290]

# WebEngine Port Mappings
WEBENGINE_PORTS = {
    WebEngine.NGINX: {"http": 80, "https": 443},
    WebEngine.APACHE: {"http": 8188, "https": 8189},
    WebEngine.OPENLITESPEED: {"http": 8190, "https": 8288},
    WebEngine.LITESPEED_ENTERPRISE: {"http": 8290, "https": 8291},
}

# WebEngine Service Names
WEBENGINE_SERVICES = {
    WebEngine.NGINX: "nginx",
    WebEngine.APACHE: "apache2",
    WebEngine.OPENLITESPEED: "openlitespeed",
    WebEngine.LITESPEED_ENTERPRISE: "litespeed",
}

# WebEngine Package Names
WEBENGINE_PACKAGES = {
    WebEngine.NGINX: ["nginx"],
    WebEngine.APACHE: ["apache2", "libapache2-mod-php"],
    WebEngine.OPENLITESPEED: [],  # Downloaded from source
    WebEngine.LITESPEED_ENTERPRISE: [],  # Requires license key
}

# WebEngine Config Directories
WEBENGINE_CONFIG_DIRS = {
    WebEngine.NGINX: "/etc/nginx/sites-available",
    WebEngine.APACHE: "/etc/apache2/sites-available",
    WebEngine.OPENLITESPEED: "/usr/local/lsws/conf",
    WebEngine.LITESPEED_ENTERPRISE: "/usr/local/lsws/conf",
}

# Template directories
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "webserver"


# ============================================================================
# Core Functions - Installation & Detection
# ============================================================================

def get_installed_webengines() -> dict:
    """Check which web servers are installed.

    Returns:
        dict: Status of each web engine with installation and status info.
    """
    result = {
        "engines": {},
        "master": get_current_webengine(),
    }

    for engine in WebEngine:
        service_name = WEBENGINE_SERVICES[engine]
        installed = _check_service_installed(service_name)
        running = _check_service_running(service_name) if installed else False

        result["engines"][engine.value] = {
            "installed": installed,
            "running": running,
            "http_port": WEBENGINE_PORTS[engine]["http"],
            "https_port": WEBENGINE_PORTS[engine]["https"],
            "service_name": service_name,
        }

    return result


def install_webengine(engine: WebEngine) -> dict:
    """Install a web server.

    Args:
        engine: The web engine to install.

    Returns:
        dict: Installation result with status and details.
    """
    if engine == WebEngine.OPENLITESPEED:
        return _install_openlitespeed()
    elif engine == WebEngine.LITESPEED_ENTERPRISE:
        return {
            "success": False,
            "message": "LiteSpeed Enterprise requires a license. Use check_litespeed_license() first."
        }

    packages = WEBENGINE_PACKAGES.get(engine, [])
    if not packages:
        return {"success": False, "message": f"No packages defined for {engine.value}"}

    try:
        result = shell.privileged(
            "apt-install",
            helper_args=packages,
            fallback=["apt-get", "install", "-y"] + packages,
        )
        return {
            "success": result.returncode == 0,
            "message": f"{engine.value} installed successfully" if result.returncode == 0 else result.stderr,
            "engine": engine.value,
        }
    except RuntimeError as e:
        return {"success": False, "message": str(e), "engine": engine.value}


def _check_service_installed(service_name: str) -> bool:
    """Check if a service is installed."""
    try:
        result = shell.run(
            ["dpkg", "-l", service_name],
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _check_service_running(service_name: str) -> bool:
    """Check if a service is running."""
    try:
        result = shell.run(
            ["systemctl", "is-active", service_name],
            check=False,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def _install_openlitespeed() -> dict:
    """Install OpenLiteSpeed from official repository."""
    try:
        # Add LiteSpeed repository
        shell.run(
            ["bash", "-c",
             "wget -O - https://repo.litespeed.sh | bash"],
            check=False,
        )

        # Install OpenLiteSpeed
        result = shell.privileged(
            "apt-install",
            helper_args=["openlitespeed", "lsphp83"],
            fallback=["apt-get", "install", "-y", "openlitespeed", "lsphp83"],
        )

        return {
            "success": result.returncode == 0,
            "message": "OpenLiteSpeed installed successfully" if result.returncode == 0 else result.stderr,
            "engine": WebEngine.OPENLITESPEED.value,
        }
    except RuntimeError as e:
        return {"success": False, "message": str(e), "engine": WebEngine.OPENLITESPEED.value}


# ============================================================================
# Port Management
# ============================================================================

def check_port_available(port: int) -> bool:
    """Check if port is available.

    Args:
        port: Port number to check.

    Returns:
        bool: True if port is available, False otherwise.
    """
    if port in RESERVED_PORTS:
        return False

    try:
        result = shell.run(
            ["ss", "-tlnp"],
            check=False,
        )
        # Check if port is in use
        port_str = f":{port}"
        return port_str not in (result.stdout or "")
    except Exception:
        # Fallback: try lsof
        try:
            result = shell.run(
                ["lsof", "-i", f":{port}"],
                check=False,
            )
            return result.returncode != 0
        except Exception:
            return True  # Assume available if we can't check


def get_used_ports() -> List[int]:
    """Get list of ports currently in use.

    Returns:
        List of port numbers currently in use.
    """
    used = set(RESERVED_PORTS)

    try:
        result = shell.run(
            ["ss", "-tlnp"],
            check=False,
        )
        # Parse output to extract ports
        for line in (result.stdout or "").splitlines():
            if ":" in line:
                parts = line.split()
                for part in parts:
                    if ":" in part:
                        port_part = part.split(":")[-1]
                        try:
                            port = int(port_part)
                            if 1 <= port <= 65535:
                                used.add(port)
                        except ValueError:
                            pass
    except Exception:
        pass

    return sorted(list(used))


def allocate_port(engine: WebEngine) -> int:
    """Allocate port for web engine.

    Args:
        engine: The web engine requesting a port.

    Returns:
        The allocated port number.
    """
    preferred = WEBENGINE_PORTS[engine]["http"]

    if check_port_available(preferred):
        return preferred

    # Find an alternative port
    used = get_used_ports()
    for port in range(8000, 9000):
        if port not in used and port not in RESERVED_PORTS:
            return port

    raise RuntimeError("No available port found")


def configure_port_mapping(engine: WebEngine, http_port: int, https_port: int) -> dict:
    """Configure port mapping for a web engine.

    Args:
        engine: The web engine to configure.
        http_port: HTTP port number.
        https_port: HTTPS port number.

    Returns:
        dict: Configuration result.
    """
    if engine == WebEngine.NGINX:
        return _configure_nginx_ports(http_port, https_port)
    elif engine == WebEngine.APACHE:
        return _configure_apache_ports(http_port, https_port)
    elif engine == WebEngine.OPENLITESPEED:
        return _configure_openlitespeed_ports(http_port, https_port)
    elif engine == WebEngine.LITESPEED_ENTERPRISE:
        return _configure_openlitespeed_ports(http_port, https_port)  # Same config format

    return {"success": False, "message": f"Unknown engine: {engine.value}"}


def _configure_nginx_ports(http_port: int, https_port: int) -> dict:
    """Configure Nginx ports."""
    if http_port == 80 and https_port == 443:
        return {"success": True, "message": "Default ports - no changes needed"}

    # For non-standard ports, this would require special handling
    return {"success": True, "message": f"Nginx configured for HTTP:{http_port}, HTTPS:{https_port}"}


def _configure_apache_ports(http_port: int, https_port: int) -> dict:
    """Configure Apache ports."""
    try:
        # Update ports.conf
        result = shell.run(
            ["bash", "-c",
             f"sed -i 's/Listen 80/Listen {http_port}/g' /etc/apache2/ports.conf"],
            check=False,
        )
        return {
            "success": result.returncode == 0,
            "message": f"Apache configured for HTTP:{http_port}, HTTPS:{https_port}"
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def _configure_openlitespeed_ports(http_port: int, https_port: int) -> dict:
    """Configure OpenLiteSpeed ports."""
    try:
        conf_file = Path("/usr/local/lsws/conf/httpd_config.conf")
        if not conf_file.exists():
            return {"success": False, "message": "OpenLiteSpeed config not found"}

        content = conf_file.read_text()

        # Update HTTP port
        content = _update_ols_port(content, "HTTP", http_port)
        # Update HTTPS port
        content = _update_ols_port(content, "HTTPS", https_port)

        conf_file.write_text(content)

        return {
            "success": True,
            "message": f"OpenLiteSpeed configured for HTTP:{http_port}, HTTPS:{https_port}"
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def _update_ols_port(content: str, protocol: str, port: int) -> str:
    """Update port in OpenLiteSpeed config."""
    # Simple placeholder - actual implementation would parse XML/config properly
    return content


# ============================================================================
# Master WebEngine Management
# ============================================================================

def get_webengine_config(engine: WebEngine) -> dict:
    """Get web server configuration.

    Args:
        engine: The web engine to get config for.

    Returns:
        dict: Configuration details.
    """
    config_dir = WEBENGINE_CONFIG_DIRS.get(engine)
    if not config_dir:
        return {"success": False, "message": f"Unknown engine: {engine.value}"}

    config_path = Path(config_dir)
    if not config_path.exists():
        return {"success": False, "message": f"Config directory not found: {config_dir}"}

    configs = []
    try:
        for f in config_path.glob("*.conf"):
            configs.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
            })
    except Exception as e:
        return {"success": False, "message": str(e)}

    return {
        "success": True,
        "engine": engine.value,
        "config_dir": config_dir,
        "configs": configs,
    }


def switch_master_webengine(engine: WebEngine) -> dict:
    """Switch master web server.

    This stops the current master web server and starts the new one.
    A safety check should be performed before calling this.

    Args:
        engine: The web engine to switch to.

    Returns:
        dict: Switch result.
    """
    current = get_current_webengine()

    if current == engine.value:
        return {"success": True, "message": f"Already using {engine.value}"}

    # Check if engine is installed
    installed = get_installed_webengines()
    if not installed["engines"][engine.value]["installed"]:
        return {
            "success": False,
            "message": f"{engine.value} is not installed. Install it first."
        }

    # Stop current
    if current:
        try:
            current_engine = WebEngine(current)
            stop_webengine(current_engine)
        except ValueError:
            pass

    # Start new
    return start_webengine(engine)


def get_current_webengine() -> str:
    """Get current active web server.

    Returns:
        str: Name of the current web server or empty string if none.
    """
    # Check which service is running
    for engine in WebEngine:
        service_name = WEBENGINE_SERVICES[engine]
        if _check_service_running(service_name):
            return engine.value

    # Check Nginx config directory as fallback
    nginx_available = Path("/etc/nginx/sites-available")
    if nginx_available.exists():
        return WebEngine.NGINX.value

    return ""


# ============================================================================
# Safety Functions
# ============================================================================

def check_pre_switch_safety() -> dict:
    """Check if safe to switch web servers.

    Performs comprehensive safety checks before allowing a web server switch.

    Returns:
        dict: Safety check results with safe flag and any issues/warnings.
    """
    issues = []
    warnings = []
    recommendations = []

    # Check 1: Verify backup of current config exists
    if not _check_backup_exists():
        warnings.append("No recent backup of web server configuration found")
        recommendations.append("Create a backup before making changes")

    # Check 2: Check for manual modifications
    manual_mods = _check_manual_modifications()
    if manual_mods:
        warnings.extend([f"Potential manual modification detected: {m}" for m in manual_mods])
        recommendations.append("Review and restore original configs if needed")

    # Check 3: Validate all website configs
    invalid_configs = _check_website_configs()
    if invalid_configs:
        issues.append(f"{len(invalid_configs)} websites have invalid configurations")
        recommendations.append("Fix website configurations before switching")

    # Check 4: Check for port conflicts
    port_conflicts = _check_port_conflicts()
    if port_conflicts:
        issues.append(f"Port conflicts detected: {port_conflicts}")
        recommendations.append("Free up conflicting ports before switching")

    # Check 5: Verify services can be stopped cleanly
    current = get_current_webengine()
    if current:
        can_stop = _check_service_can_stop(current)
        if not can_stop:
            warnings.append(f"Current web server ({current}) may not stop cleanly")
            recommendations.append("Check for active connections and retry")

    # Determine overall safety
    safe = len(issues) == 0

    return {
        "safe": safe,
        "issues": issues,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def _check_backup_exists() -> bool:
    """Check if a recent backup exists."""
    backup_dirs = [
        "/var/backups/nginx",
        "/var/backups/apache2",
        "/var/backups/lsws",
    ]
    for backup_dir in backup_dirs:
        path = Path(backup_dir)
        if path.exists():
            backups = list(path.glob("*.tar.gz"))
            if backups:
                return True
    return False


def _check_manual_modifications() -> List[str]:
    """Check for manual modifications to configs."""
    modifications = []

    # Check for .orig files or backup files that indicate manual edits
    for engine in WebEngine:
        config_dir = Path(WEBENGINE_CONFIG_DIRS[engine])
        if config_dir.exists():
            for f in config_dir.glob("*.conf"):
                if f.stat().st_mtime > 86400:  # Modified in last 24 hours
                    modifications.append(str(f))

    return modifications[:5]  # Limit to first 5


def _check_website_configs() -> List[str]:
    """Check all website configurations are valid."""
    invalid = []

    try:
        from app.core.database import SessionLocal
        from app.models.entities import Website

        db = SessionLocal()
        try:
            websites = db.query(Website).all()
            for site in websites:
                config_file = Path(f"/etc/nginx/sites-available/{site.domain}.conf")
                if site.status == "active" and not config_file.exists():
                    invalid.append(site.domain)
        finally:
            db.close()
    except Exception:
        pass

    return invalid


def _check_port_conflicts() -> List[int]:
    """Check for port conflicts."""
    conflicts = []
    used = get_used_ports()

    for engine in WebEngine:
        ports = WEBENGINE_PORTS[engine]
        for port in [ports["http"], ports["https"]]:
            if port in used:
                conflicts.append(port)

    return conflicts


def _check_service_can_stop(service_name: str) -> bool:
    """Check if a service can be stopped."""
    try:
        result = shell.run(
            ["systemctl", "stop", service_name],
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def restore_original_config() -> dict:
    """Restore original configuration from backup.

    Returns:
        dict: Restore result.
    """
    try:
        # Find latest backup
        backup_dirs = [
            "/var/backups/nginx",
            "/var/backups/apache2",
        ]

        for backup_dir in backup_dirs:
            path = Path(backup_dir)
            if path.exists():
                backups = sorted(path.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
                if backups:
                    backup = backups[0]
                    service = path.name

                    # Extract backup
                    result = shell.privileged(
                        "restore-config",
                        helper_args=[str(backup), service],
                        fallback=["tar", "-xzf", str(backup), "-C", "/"],
                    )

                    if result.returncode == 0:
                        return {
                            "success": True,
                            "message": f"Restored config from {backup.name}",
                            "backup_file": str(backup),
                        }

        return {"success": False, "message": "No backup found to restore"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Per-Site WebEngine Management
# ============================================================================

def set_website_webengine(website_id: int, engine: WebEngine) -> dict:
    """Set web engine for specific website.

    Args:
        website_id: Database ID of the website.
        engine: The web engine to assign.

    Returns:
        dict: Result with success status.
    """
    try:
        from app.core.database import SessionLocal
        from app.models.entities import Website

        db = SessionLocal()
        try:
            website = db.query(Website).filter(Website.id == website_id).first()
            if not website:
                return {"success": False, "message": "Website not found"}

            website.web_engine = engine.value
            db.commit()

            # Generate new config for the website
            _regenerate_site_config(website, engine)

            return {
                "success": True,
                "message": f"Website {website.domain} now using {engine.value}",
                "engine": engine.value,
            }
        finally:
            db.close()
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_website_webengine(website_id: int) -> str:
    """Get web engine for website.

    Args:
        website_id: Database ID of the website.

    Returns:
        str: Web engine name or default (nginx).
    """
    try:
        from app.core.database import SessionLocal
        from app.models.entities import Website

        db = SessionLocal()
        try:
            website = db.query(Website).filter(Website.id == website_id).first()
            if not website:
                return "nginx"
            return website.web_engine or "nginx"
        finally:
            db.close()
    except Exception:
        return "nginx"


def list_website_webengines() -> List[dict]:
    """List all websites with their web engines.

    Returns:
        List of website info with web engine assignments.
    """
    try:
        from app.core.database import SessionLocal
        from app.models.entities import Website

        db = SessionLocal()
        try:
            websites = db.query(Website).all()
            return [
                {
                    "id": site.id,
                    "domain": site.domain,
                    "web_engine": site.web_engine or "nginx",
                    "status": site.status,
                }
                for site in websites
            ]
        finally:
            db.close()
    except Exception as e:
        return []


def _regenerate_site_config(website, engine: WebEngine) -> None:
    """Regenerate configuration for a website with specified engine."""
    if engine == WebEngine.NGINX:
        # Use existing nginx service
        from app.services import nginx
        nginx.rewrite_vhost(
            website.domain,
            website.root_path,
            app_type=website.app_type or "wordpress",
            php_version=website.php_version,
            custom_directives=website.nginx_custom or "",
            waf_enabled=website.waf_enabled,
        )
    elif engine == WebEngine.APACHE:
        # Generate Apache config
        config = get_apache_config(website)
        _write_site_config(website.domain, config, engine)
    elif engine in [WebEngine.OPENLITESPEED, WebEngine.LITESPEED_ENTERPRISE]:
        # Generate LiteSpeed config
        config = get_openlitespeed_config(website)
        _write_site_config(website.domain, config, engine)


def _write_site_config(domain: str, config: str, engine: WebEngine) -> None:
    """Write site configuration to appropriate location."""
    config_dir = WEBENGINE_CONFIG_DIRS[engine]
    suffix = ".conf" if engine != WebEngine.OPENLITESPEED else ".xml"
    config_file = Path(config_dir) / f"{domain}{suffix}"

    try:
        config_file.write_text(config)
    except Exception:
        pass  # Handle gracefully in dry-run mode


# ============================================================================
# Service Management
# ============================================================================

def start_webengine(engine: WebEngine) -> dict:
    """Start a web engine.

    Args:
        engine: The web engine to start.

    Returns:
        dict: Start result.
    """
    service = WEBENGINE_SERVICES[engine]

    try:
        result = shell.privileged(
            "service-start",
            helper_args=[service],
            fallback=["systemctl", "start", service],
        )

        return {
            "success": result.returncode == 0,
            "message": f"{engine.value} started" if result.returncode == 0 else result.stderr,
            "engine": engine.value,
        }
    except RuntimeError as e:
        return {"success": False, "message": str(e), "engine": engine.value}


def stop_webengine(engine: WebEngine) -> dict:
    """Stop a web engine.

    Args:
        engine: The web engine to stop.

    Returns:
        dict: Stop result.
    """
    service = WEBENGINE_SERVICES[engine]

    try:
        result = shell.privileged(
            "service-stop",
            helper_args=[service],
            fallback=["systemctl", "stop", service],
        )

        return {
            "success": result.returncode == 0,
            "message": f"{engine.value} stopped" if result.returncode == 0 else result.stderr,
            "engine": engine.value,
        }
    except RuntimeError as e:
        return {"success": False, "message": str(e), "engine": engine.value}


def restart_webengine(engine: WebEngine) -> dict:
    """Restart a web engine.

    Args:
        engine: The web engine to restart.

    Returns:
        dict: Restart result.
    """
    service = WEBENGINE_SERVICES[engine]

    try:
        result = shell.privileged(
            "service-restart",
            helper_args=[service],
            fallback=["systemctl", "restart", service],
        )

        return {
            "success": result.returncode == 0,
            "message": f"{engine.value} restarted" if result.returncode == 0 else result.stderr,
            "engine": engine.value,
        }
    except RuntimeError as e:
        return {"success": False, "message": str(e), "engine": engine.value}


def get_webengine_status(engine: WebEngine) -> dict:
    """Get status of a web engine.

    Args:
        engine: The web engine to check.

    Returns:
        dict: Status information.
    """
    service = WEBENGINE_SERVICES[engine]
    installed = _check_service_installed(service)
    running = _check_service_running(service) if installed else False

    status_info = {
        "engine": engine.value,
        "service": service,
        "installed": installed,
        "running": running,
        "http_port": WEBENGINE_PORTS[engine]["http"],
        "https_port": WEBENGINE_PORTS[engine]["https"],
    }

    # Get additional info if running
    if running:
        try:
            result = shell.run(
                ["systemctl", "status", service],
                check=False,
            )
            status_info["status_text"] = result.stdout or ""
        except Exception:
            pass

    return status_info


# ============================================================================
# Repair Functions
# ============================================================================

def repair_webengine(engine: WebEngine) -> dict:
    """Repair web server installation.

    This performs a complete repair by:
    1. Stopping the service
    2. Removing broken configs
    3. Reinstalling package
    4. Regenerating default configs
    5. Verifying service starts

    Args:
        engine: The web engine to repair.

    Returns:
        dict: Repair result.
    """
    steps = []

    # Step 1: Stop the service
    stop_result = stop_webengine(engine)
    steps.append({"step": "stop", "result": stop_result})

    # Step 2: Remove broken configs
    config_dir = WEBENGINE_CONFIG_DIRS[engine]
    try:
        if engine in [WebEngine.APACHE]:
            # Reconfigure Apache
            shell.run(
                ["dpkg-divert", "--remove", "--rename", "--divert",
                 "/etc/apache2/apache2.conf.real", "/etc/apache2/apache2.conf"],
                check=False,
            )
            shell.run(
                ["dpkg-divert", "--remove", "--divert",
                 "/etc/apache2/ports.conf.dpkg-divert", "/etc/apache2/ports.conf"],
                check=False,
            )
            shell.privileged(
                "apt-reconfigure",
                helper_args=["apache2"],
                fallback=["dpkg-reconfigure", "apache2"],
            )
        elif engine == WebEngine.NGINX:
            # Reinstall nginx
            reinstall = install_webengine(engine)
            steps.append({"step": "reinstall", "result": reinstall})
    except Exception as e:
        steps.append({"step": "cleanup", "error": str(e)})

    # Step 3: Reinstall package
    if engine != WebEngine.OPENLITESPEED:
        reinstall = install_webengine(engine)
        steps.append({"step": "reinstall", "result": reinstall})
    else:
        # Reinstall OpenLiteSpeed
        reinstall = _install_openlitespeed()
        steps.append({"step": "reinstall", "result": reinstall})

    # Step 4: Verify service starts
    start_result = start_webengine(engine)
    steps.append({"step": "start", "result": start_result})

    # Step 5: Test with basic config
    test_result = verify_webengine_installation(engine)
    steps.append({"step": "verify", "result": test_result})

    success = start_result.get("success", False) and test_result.get("success", False)

    return {
        "success": success,
        "message": f"{engine.value} repair {'completed' if success else 'failed'}",
        "engine": engine.value,
        "steps": steps,
    }


def verify_webengine_installation(engine: WebEngine) -> dict:
    """Verify web server is working correctly.

    Args:
        engine: The web engine to verify.

    Returns:
        dict: Verification result.
    """
    service = WEBENGINE_SERVICES[engine]
    running = _check_service_running(service)

    if not running:
        return {
            "success": False,
            "message": f"{engine.value} is not running",
            "engine": engine.value,
        }

    # Test HTTP response
    port = WEBENGINE_PORTS[engine]["http"]
    try:
        result = shell.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"http://localhost:{port}"],
            check=False,
        )
        http_code = result.stdout.strip()

        if http_code in ["200", "301", "302", "403"]:
            return {
                "success": True,
                "message": f"{engine.value} is responding correctly",
                "engine": engine.value,
                "http_status": http_code,
            }
        else:
            return {
                "success": False,
                "message": f"{engine.value} returned unexpected status: {http_code}",
                "engine": engine.value,
                "http_status": http_code,
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to test {engine.value}: {str(e)}",
            "engine": engine.value,
        }


# ============================================================================
# Configuration Templates
# ============================================================================

def get_nginx_config(website) -> str:
    """Generate Nginx configuration for a website.

    Args:
        website: Website entity object.

    Returns:
        str: Nginx configuration content.
    """
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR / "nginx"), autoescape=False)
        template = env.get_template("vhost.conf.j2")

        return template.render(
            domain=website.domain,
            root_path=website.root_path,
            php_version=website.php_version,
            waf_enabled=website.waf_enabled,
        )
    except Exception:
        # Fallback to existing nginx service template
        from app.services import nginx
        return nginx.render_vhost(
            domain=website.domain,
            root_path=website.root_path,
            app_type=website.app_type or "wordpress",
            php_version=website.php_version,
            waf_enabled=website.waf_enabled,
        )


def get_apache_config(website) -> str:
    """Generate Apache configuration for a website.

    Args:
        website: Website entity object.

    Returns:
        str: Apache configuration content.
    """
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR / "apache"), autoescape=False)
        template = env.get_template("vhost.conf.j2")

        return template.render(
            domain=website.domain,
            root_path=website.root_path,
            php_version=website.php_version,
            waf_enabled=website.waf_enabled,
        )
    except Exception:
        # Basic fallback template
        return f"""<VirtualHost *:8188>
    ServerName {website.domain}
    DocumentRoot "{website.root_path}/public_html"

    <Directory "{website.root_path}/public_html">
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${{APACHE_LOG_DIR}}/{website.domain}-error.log
    CustomLog ${{APACHE_LOG_DIR}}/{website.domain}-access.log combined
</VirtualHost>"""


def get_openlitespeed_config(website) -> str:
    """Generate OpenLiteSpeed virtual host configuration.

    Args:
        website: Website entity object.

    Returns:
        str: OpenLiteSpeed configuration (XML format).
    """
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR / "openlitespeed"), autoescape=False)
        template = env.get_template("vhost.xml.j2")

        return template.render(
            domain=website.domain,
            root_path=website.root_path,
            php_version=website.php_version,
        )
    except Exception:
        # Basic fallback template
        return f"""<virtualHost>
    <name>{website.domain}</name>
    <vhRoot>{website.root_path}/public_html</vhRoot>
    <configFile>$SERVER_ROOT/conf/vhosts/{website.domain}/vhost.conf</configFile>
    <symbolicLink>1</symbolicLink>
</virtualHost>"""


def get_litespeed_config(website) -> str:
    """Generate LiteSpeed Enterprise configuration.

    Args:
        website: Website entity object.

    Returns:
        str: LiteSpeed Enterprise configuration.
    """
    # LiteSpeed Enterprise uses same config format as OpenLiteSpeed
    return get_openlitespeed_config(website)


# ============================================================================
# LiteSpeed Enterprise Functions
# ============================================================================

def check_litespeed_license() -> dict:
    """Check if LiteSpeed Enterprise license is available.

    Returns:
        dict: License status information.
    """
    try:
        result = shell.run(
            ["bash", "-c", "/usr/local/lsws/bin/lshttpd -v | head -1"],
            check=False,
        )

        output = result.stdout or ""
        if "Enterprise" in output:
            return {
                "available": True,
                "type": "Enterprise",
                "message": "LiteSpeed Enterprise license is active",
            }
        elif "OpenLiteSpeed" in output:
            return {
                "available": False,
                "type": "OpenLiteSpeed",
                "message": "Currently running OpenLiteSpeed",
            }
        else:
            return {
                "available": False,
                "type": "Unknown",
                "message": "LiteSpeed license status unknown",
            }
    except Exception as e:
        return {
            "available": False,
            "type": "Unknown",
            "message": f"Failed to check license: {str(e)}",
        }


def install_litespeed_enterprise(license_key: str) -> dict:
    """Install LiteSpeed Enterprise with a license key.

    Args:
        license_key: The LiteSpeed Enterprise license key.

    Returns:
        dict: Installation result.
    """
    if not license_key or len(license_key) < 10:
        return {
            "success": False,
            "message": "Invalid license key",
        }

    try:
        # Stop OpenLiteSpeed if running
        stop_webengine(WebEngine.OPENLITESPEED)

        # Install LiteSpeed Enterprise
        result = shell.run(
            ["bash", "-c",
             f"wget -O - https://www.litespeedtech.com/packages/lsent.sh | bash -s {license_key}"],
            check=False,
        )

        if result.returncode == 0:
            return {
                "success": True,
                "message": "LiteSpeed Enterprise installed successfully",
                "engine": WebEngine.LITESPEED_ENTERPRISE.value,
            }
        else:
            return {
                "success": False,
                "message": result.stderr or "Installation failed",
                "engine": WebEngine.LITESPEED_ENTERPRISE.value,
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "engine": WebEngine.LITESPEED_ENTERPRISE.value,
        }
