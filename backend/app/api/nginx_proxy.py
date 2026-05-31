"""
Nginx Reverse Proxy Management API Router.

Provides endpoints for managing reverse proxy configurations with SSL support.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.services import nginx_proxy
from app.services.audit import log_action


router = APIRouter(prefix="/nginx-proxy", tags=["nginx-proxy"])


# Request/Response Models

class ProxyConfigCreate(BaseModel):
    domain: str = Field(..., description="Domain name for the proxy")
    target_url: str = Field(..., description="Target URL to proxy to")
    ssl: bool = Field(default=True, description="Enable SSL (Let's Encrypt)")
    options: Optional[dict] = Field(
        default=None,
        description="Additional options: template, connect_timeout, send_timeout, read_timeout, rate_limit, burst"
    )


class ProxyConfigUpdate(BaseModel):
    target_url: Optional[str] = Field(default=None, description="New target URL")
    ssl: Optional[bool] = Field(default=None, description="Enable/disable SSL")
    options: Optional[dict] = Field(
        default=None,
        description="Additional options: template, connect_timeout, send_timeout, read_timeout, rate_limit, burst"
    )


class SSLSetup(BaseModel):
    letsencrypt: bool = Field(default=True, description="Use Let's Encrypt for SSL")


class TemplateCreate(BaseModel):
    domain: str = Field(..., description="Domain name")
    template: str = Field(..., description="Template name to use")
    target_url: Optional[str] = Field(default=None, description="Target URL (auto-detected if not provided)")
    ssl: bool = Field(default=True, description="Enable SSL")
    options: Optional[dict] = Field(default=None, description="Additional options")


class ProxyConfigResponse(BaseModel):
    domain: str
    target_url: str
    ssl: bool
    template: Optional[str] = None
    rate_limit: Optional[int] = None
    enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    ssl_status: Optional[dict] = None


class SSLStatusResponse(BaseModel):
    domain: str
    enabled: bool
    provider: Optional[str] = None
    expires: Optional[str] = None
    days_remaining: Optional[int] = None
    cert_path: Optional[str] = None


class TemplateInfo(BaseModel):
    id: str
    name: str
    connect_timeout: str
    send_timeout: str
    read_timeout: str
    has_extra: bool


class TemplateListResponse(BaseModel):
    templates: list[TemplateInfo]


class NginxStatusResponse(BaseModel):
    running: bool
    config_valid: bool
    config_valid_output: str


# Error helper
def _command_error(result):
    return (result.stderr or result.stdout or f"Command failed with code {result.returncode}").strip()


# Proxy Configs Endpoints

@router.get("/configs", response_model=list[ProxyConfigResponse])
def list_proxy_configs(
    current_user: User = Depends(get_current_user),
):
    """List all proxy configurations."""
    ensure_role(current_user.role, Role.admin)
    return nginx_proxy.list_proxy_configs()


@router.post("/configs", response_model=ProxyConfigResponse)
def create_proxy_config(
    payload: ProxyConfigCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Create a new proxy configuration."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = nginx_proxy.create_proxy_config(
            domain=payload.domain,
            target_url=payload.target_url,
            ssl=payload.ssl,
            options=payload.options or {},
        )
        log_action(
            None,
            current_user.id,
            "create_proxy_config",
            payload.domain,
            request=request,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/configs/{domain}", response_model=ProxyConfigResponse)
def get_proxy_config(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Get a specific proxy configuration."""
    ensure_role(current_user.role, Role.admin)
    result = nginx_proxy.get_proxy_config(domain)
    if result is None:
        raise HTTPException(status_code=404, detail="Proxy config not found")
    return result


@router.put("/configs/{domain}", response_model=ProxyConfigResponse)
def update_proxy_config(
    domain: str,
    payload: ProxyConfigUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Update an existing proxy configuration."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = nginx_proxy.update_proxy_config(
            domain=domain,
            target_url=payload.target_url,
            ssl=payload.ssl,
            options=payload.options or {},
        )
        log_action(
            None,
            current_user.id,
            "update_proxy_config",
            domain,
            request=request,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/configs/{domain}")
def delete_proxy_config(
    domain: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Delete a proxy configuration."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = nginx_proxy.delete_proxy_config(domain)
        log_action(
            None,
            current_user.id,
            "delete_proxy_config",
            domain,
            request=request,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# SSL Endpoints

@router.post("/ssl/{domain}")
def setup_ssl(
    domain: str,
    payload: SSLSetup,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Setup SSL for a domain."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = nginx_proxy.setup_ssl(domain, letsencrypt=payload.letsencrypt)
        log_action(
            None,
            current_user.id,
            "setup_ssl",
            domain,
            request=request,
        )
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "SSL setup failed"))
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ssl/{domain}/renew")
def renew_ssl(
    domain: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Renew SSL certificate for a domain."""
    ensure_role(current_user.role, Role.admin)
    result = nginx_proxy.renew_ssl(domain)
    log_action(
        None,
        current_user.id,
        "renew_ssl",
        domain,
        request=request,
    )
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "SSL renewal failed"))
    return result


@router.get("/ssl/{domain}/status", response_model=SSLStatusResponse)
def get_ssl_status(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Get SSL status for a domain."""
    ensure_role(current_user.role, Role.admin)
    return nginx_proxy.get_ssl_status(domain)


@router.post("/ssl/auto/{domain}")
def auto_ssl_setup(
    domain: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Automatically setup SSL with Let's Encrypt for a domain."""
    ensure_role(current_user.role, Role.admin)
    try:
        result = nginx_proxy.auto_ssl_setup(domain)
        log_action(
            None,
            current_user.id,
            "auto_ssl_setup",
            domain,
            request=request,
        )
        if not result.get("success", False):
            error = result.get("error", "Auto SSL setup failed")
            pending = result.get("pending_verification", False)
            status_code = 202 if pending else 500
            raise HTTPException(status_code=status_code, detail=error)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Template Endpoints

@router.get("/templates", response_model=TemplateListResponse)
def list_proxy_templates(
    current_user: User = Depends(get_current_user),
):
    """List available proxy templates."""
    ensure_role(current_user.role, Role.admin)
    return nginx_proxy.list_proxy_templates()


@router.post("/templates/{template}", response_model=ProxyConfigResponse)
def create_from_template(
    template: str,
    payload: TemplateCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Create a proxy configuration from a template."""
    ensure_role(current_user.role, Role.admin)
    try:
        options = payload.options or {}
        if payload.target_url:
            options["target_url"] = payload.target_url
        if payload.ssl is not None:
            options["ssl"] = payload.ssl

        result = nginx_proxy.create_from_template(
            domain=payload.domain,
            template=template,
            options=options,
        )
        log_action(
            None,
            current_user.id,
            "create_proxy_from_template",
            f"{template}:{payload.domain}",
            request=request,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Nginx Management Endpoints

@router.get("/status", response_model=NginxStatusResponse)
def get_nginx_status(
    current_user: User = Depends(get_current_user),
):
    """Get nginx service status."""
    ensure_role(current_user.role, Role.admin)
    return nginx_proxy.get_nginx_status()


@router.post("/reload")
def reload_nginx(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Reload nginx configuration."""
    ensure_role(current_user.role, Role.admin)
    result = nginx_proxy.reload_nginx()
    log_action(
        None,
        current_user.id,
        "reload_nginx",
        "proxy_manager",
        request=request,
    )
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Nginx reload failed"))
    return result


@router.post("/restart")
def restart_nginx(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Restart nginx service."""
    ensure_role(current_user.role, Role.admin)
    result = nginx_proxy.restart_nginx()
    log_action(
        None,
        current_user.id,
        "restart_nginx",
        "proxy_manager",
        request=request,
    )
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Nginx restart failed"))
    return result


@router.post("/test")
def test_nginx_config(
    current_user: User = Depends(get_current_user),
):
    """Test nginx configuration."""
    ensure_role(current_user.role, Role.admin)
    result = nginx_proxy.test_nginx_config()
    if not result.get("success", False):
        raise HTTPException(
            status_code=400,
            detail={"message": "Nginx configuration test failed", "output": result.get("output", "")}
        )
    return result
