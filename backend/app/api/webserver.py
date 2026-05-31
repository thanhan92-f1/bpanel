"""
WebServer API Router - Multi-WebServer Hosting management endpoints.

Provides endpoints for managing multiple web servers (Nginx, Apache, OpenLiteSpeed)
with per-site web engine selection, port management, safety checks, and repair functions.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Role, ensure_role
from app.models.entities import User, Website
from app.schemas.schemas import WebsiteOut
from app.services import webserver as webserver_service
from app.services.audit import log_action
from app.core.database import get_db


router = APIRouter(prefix="/webserver", tags=["webserver"])


def _parse_webengine(engine: str) -> webserver_service.WebEngine:
    """Parse web engine string to enum."""
    try:
        return webserver_service.WebEngine(engine.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid web engine: {engine}. Valid options: nginx, apache, openlitespeed, litespeed"
        )


# =============================================================================
# Master WebEngine Endpoints
# =============================================================================

@router.get("/engines")
def get_installed_engines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all installed web engines and their status."""
    ensure_role(current_user.role, Role.admin)
    return webserver_service.get_installed_webengines()


@router.get("/current")
def get_current_engine(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the currently active web engine."""
    ensure_role(current_user.role, Role.admin)
    current = webserver_service.get_current_webengine()
    return {"current": current}


@router.post("/switch")
def switch_engine(
    engine: str,
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Switch master web server to a different engine.

    WARNING: This will stop the current web server and start the new one.
    Run safety check first to ensure it's safe to switch.
    """
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)

    # Perform safety check before switching
    safety = webserver_service.check_pre_switch_safety()
    if not safety["safe"] and safety["issues"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Safety check failed. Review issues before switching.",
                "issues": safety["issues"],
                "warnings": safety["warnings"],
            }
        )

    result = webserver_service.switch_master_webengine(web_engine)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "switch_webengine", engine, request=request)
    return result


@router.get("/config/{engine}")
def get_engine_config(
    engine: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get configuration for a specific web engine."""
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)
    return webserver_service.get_webengine_config(web_engine)


@router.post("/install/{engine}")
def install_engine(
    engine: str,
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Install a web server engine."""
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)
    result = webserver_service.install_webengine(web_engine)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "install_webengine", engine, request=request)
    return result


# =============================================================================
# Safety Endpoints
# =============================================================================

@router.get("/safety-check")
def safety_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Perform safety check before web server switch.

    Returns:
        - safe: bool - Whether it's safe to proceed
        - issues: List[str] - Critical issues that must be resolved
        - warnings: List[str] - Non-critical warnings
        - recommendations: List[str] - Suggested actions
    """
    ensure_role(current_user.role, Role.admin)
    return webserver_service.check_pre_switch_safety()


@router.post("/restore")
def restore_config(
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore original configuration from backup."""
    ensure_role(current_user.role, Role.admin)
    result = webserver_service.restore_original_config()

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "restore_webserver_config", "restore", request=request)
    return result


# =============================================================================
# Per-Site WebEngine Endpoints
# =============================================================================

@router.get("/websites")
def list_website_engines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all websites with their assigned web engines."""
    ensure_role(current_user.role, Role.admin)
    return webserver_service.list_website_webengines()


@router.put("/websites/{website_id}/engine")
def set_website_engine(
    website_id: int,
    engine: str,
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set web engine for a specific website."""
    ensure_role(current_user.role, Role.admin)

    # Verify website exists
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    web_engine = _parse_webengine(engine)

    # Check if engine is installed
    installed = webserver_service.get_installed_webengines()
    if not installed["engines"][engine.lower()]["installed"]:
        raise HTTPException(
            status_code=400,
            detail=f"{engine} is not installed. Install it first."
        )

    result = webserver_service.set_website_webengine(website_id, web_engine)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "set_website_webengine", f"{website.domain}:{engine}", request=request)
    return result


@router.get("/websites/{website_id}/engine")
def get_website_engine(
    website_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get web engine assigned to a website."""
    ensure_role(current_user.role, Role.admin)

    # Verify website exists
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    engine = webserver_service.get_website_webengine(website_id)
    return {"website_id": website_id, "engine": engine}


# =============================================================================
# Port Management Endpoints
# =============================================================================

@router.get("/ports")
def get_ports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of ports currently in use."""
    ensure_role(current_user.role, Role.admin)
    used = webserver_service.get_used_ports()
    reserved = webserver_service.RESERVED_PORTS

    return {
        "used_ports": used,
        "reserved_ports": reserved,
        "webengine_ports": webserver_service.WEBENGINE_PORTS,
    }


@router.post("/ports/allocate")
def allocate_port(
    engine: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allocate a port for a web engine."""
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)

    try:
        port = webserver_service.allocate_port(web_engine)
        return {"engine": engine, "port": port}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ports/configure")
def configure_ports(
    engine: str,
    http_port: int,
    https_port: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure port mapping for a web engine."""
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)

    if not (1 <= http_port <= 65535 and 1 <= https_port <= 65535):
        raise HTTPException(status_code=400, detail="Ports must be between 1 and 65535")

    result = webserver_service.configure_port_mapping(web_engine, http_port, https_port)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "configure_webengine_ports", f"{engine}:{http_port},{https_port}")
    return result


# =============================================================================
# Service Control Endpoints
# =============================================================================

@router.get("/{engine}/status")
def get_status(
    engine: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status of a web engine."""
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)
    return webserver_service.get_webengine_status(web_engine)


@router.post("/{engine}/start")
def start_engine(
    engine: str,
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a web engine."""
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)
    result = webserver_service.start_webengine(web_engine)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "start_webengine", engine, request=request)
    return result


@router.post("/{engine}/stop")
def stop_engine(
    engine: str,
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stop a web engine."""
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)
    result = webserver_service.stop_webengine(web_engine)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "stop_webengine", engine, request=request)
    return result


@router.post("/{engine}/restart")
def restart_engine(
    engine: str,
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restart a web engine."""
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)
    result = webserver_service.restart_webengine(web_engine)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "restart_webengine", engine, request=request)
    return result


@router.post("/{engine}/repair")
def repair_engine(
    engine: str,
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Repair a web engine installation.

    This will:
    1. Stop the service
    2. Remove broken configs
    3. Reinstall package
    4. Regenerate default configs
    5. Verify service starts
    """
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)
    result = webserver_service.repair_webengine(web_engine)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "repair_webengine", engine, request=request)
    return result


@router.post("/{engine}/verify")
def verify_engine(
    engine: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify a web engine is working correctly."""
    ensure_role(current_user.role, Role.admin)
    web_engine = _parse_webengine(engine)
    return webserver_service.verify_webengine_installation(web_engine)


# =============================================================================
# LiteSpeed Enterprise Endpoints
# =============================================================================

@router.get("/litespeed/license")
def check_litespeed_license(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check LiteSpeed Enterprise license status."""
    ensure_role(current_user.role, Role.admin)
    return webserver_service.check_litespeed_license()


@router.post("/litespeed/install")
def install_litespeed_enterprise(
    license_key: str,
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Install LiteSpeed Enterprise with a license key."""
    ensure_role(current_user.role, Role.admin)

    if not license_key or len(license_key) < 10:
        raise HTTPException(status_code=400, detail="Invalid license key")

    result = webserver_service.install_litespeed_enterprise(license_key)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    log_action(db, current_user.id, "install_litespeed_enterprise", "litespeed", request=request)
    return result


# =============================================================================
# Configuration Template Endpoints
# =============================================================================

@router.get("/templates/{engine}/{website_id}")
def get_site_config_template(
    engine: str,
    website_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the configuration template for a website with specified engine.

    This generates a preview of the configuration that would be applied
    if the website were switched to the specified engine.
    """
    ensure_role(current_user.role, Role.admin)

    # Verify website exists
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    web_engine = _parse_webengine(engine)

    # Check if engine is installed
    installed = webserver_service.get_installed_webengines()
    if not installed["engines"][engine.lower()]["installed"]:
        raise HTTPException(
            status_code=400,
            detail=f"{engine} is not installed."
        )

    # Generate config based on engine
    if web_engine == webserver_service.WebEngine.NGINX:
        config = webserver_service.get_nginx_config(website)
    elif web_engine == webserver_service.WebEngine.APACHE:
        config = webserver_service.get_apache_config(website)
    elif web_engine == webserver_service.WebEngine.OPENLITESPEED:
        config = webserver_service.get_openlitespeed_config(website)
    elif web_engine == webserver_service.WebEngine.LITESPEED_ENTERPRISE:
        config = webserver_service.get_litespeed_config(website)
    else:
        raise HTTPException(status_code=400, detail="Unknown engine")

    return {
        "website_id": website_id,
        "domain": website.domain,
        "engine": engine,
        "config": config,
    }
