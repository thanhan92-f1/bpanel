"""
PHP Versions Management API Router

Provides REST API endpoints for managing multiple PHP versions,
extensions, configurations, and FPM pools.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.services import php_versions


router = APIRouter(prefix="/php", tags=["php-versions"])


# =============================================================================
# Version Management
# =============================================================================

@router.get("/versions")
def list_installed_php_versions(current_user: User = Depends(get_current_user)):
    """
    List all installed PHP versions on the system.
    """
    ensure_role(current_user.role, Role.admin)
    return php_versions.list_installed_php_versions()


@router.get("/versions/available")
def list_available_php_versions(current_user: User = Depends(get_current_user)):
    """
    List available PHP versions from Ondrej PPA.
    """
    ensure_role(current_user.role, Role.admin)
    return php_versions.list_available_php_versions()


@router.post("/versions/{version}/install")
def install_php_version(version: str, current_user: User = Depends(get_current_user)):
    """
    Install a specific PHP version.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        result = php_versions.install_php_version(version)
        if not result.get("success", False) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/versions/{version}")
def remove_php_version(version: str, current_user: User = Depends(get_current_user)):
    """
    Remove a PHP version from the system.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        result = php_versions.remove_php_version(version)
        if not result.get("success", False) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# =============================================================================
# Extension Management
# =============================================================================

@router.get("/{version}/extensions")
def list_php_extensions(version: str, current_user: User = Depends(get_current_user)):
    """
    List all extensions for a PHP version.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        return php_versions.get_php_extensions(version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{version}/extensions/{ext}/install")
def install_php_extension(
    version: str,
    ext: str,
    current_user: User = Depends(get_current_user)
):
    """
    Install a PHP extension for a specific version.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        result = php_versions.install_php_extension(version, ext)
        if not result.get("success", False) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{version}/extensions/{ext}")
def remove_php_extension(
    version: str,
    ext: str,
    current_user: User = Depends(get_current_user)
):
    """
    Remove a PHP extension from a specific version.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        result = php_versions.remove_php_extension(version, ext)
        if not result.get("success", False) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# =============================================================================
# Configuration Management
# =============================================================================

@router.get("/{version}/config")
def get_php_config(version: str, current_user: User = Depends(get_current_user)):
    """
    Get current php.ini configuration for a PHP version.
    Returns all configuration options including upload limits, optimization settings, etc.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        return php_versions.get_php_config(version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class PhpConfigUpdateRequest:
    """Request model for PHP configuration update."""

    def __init__(
        self,
        # Upload & Timeout Limits
        upload_max_filesize: str = "128M",
        post_max_size: str = "128M",
        max_execution_time: int = 300,
        max_input_time: int = 600,
        max_input_vars: int = 10000,
        memory_limit: str = "512M",
        # Disabled Functions
        disable_functions: list = None,
        # Optimization Settings
        opcache_enable: bool = True,
        opcache_memory_consumption: int = 128,
        opcache_max_accelerated_files: int = 10000,
        opcache_validate_timestamps: bool = True,
        realpath_cache_size: str = "4096K",
        # Session Configuration
        session_save_handler: str = "files",
        session_save_path: str = "/var/lib/php/sessions",
        session_gc_maxlifetime: int = 1440,
        # Logging
        error_reporting: str = "E_ALL & ~E_DEPRECATED & ~E_STRICT",
        error_log: str = None,
        log_errors: bool = True,
        display_errors: str = "Off",
        slowlog: str = None,
        request_slowlog_timeout: str = "10s",
    ):
        self.upload_max_filesize = upload_max_filesize
        self.post_max_size = post_max_size
        self.max_execution_time = max_execution_time
        self.max_input_time = max_input_time
        self.max_input_vars = max_input_vars
        self.memory_limit = memory_limit
        self.disable_functions = disable_functions or []
        self.opcache_enable = opcache_enable
        self.opcache_memory_consumption = opcache_memory_consumption
        self.opcache_max_accelerated_files = opcache_max_accelerated_files
        self.opcache_validate_timestamps = opcache_validate_timestamps
        self.realpath_cache_size = realpath_cache_size
        self.session_save_handler = session_save_handler
        self.session_save_path = session_save_path
        self.session_gc_maxlifetime = session_gc_maxlifetime
        self.error_reporting = error_reporting
        self.error_log = error_log
        self.log_errors = log_errors
        self.display_errors = display_errors
        self.slowlog = slowlog
        self.request_slowlog_timeout = request_slowlog_timeout


@router.put("/{version}/config")
def update_php_config(
    version: str,
    # Upload & Timeout Limits
    upload_max_filesize: str = Query(default="128M"),
    post_max_size: str = Query(default="128M"),
    max_execution_time: int = Query(default=300),
    max_input_time: int = Query(default=600),
    max_input_vars: int = Query(default=10000),
    memory_limit: str = Query(default="512M"),
    # Disabled Functions
    disable_functions: str = Query(default=""),
    # Optimization Settings
    opcache_enable: bool = Query(default=True),
    opcache_memory_consumption: int = Query(default=128),
    opcache_max_accelerated_files: int = Query(default=10000),
    opcache_validate_timestamps: bool = Query(default=True),
    realpath_cache_size: str = Query(default="4096K"),
    # Session Configuration
    session_save_handler: str = Query(default="files"),
    session_save_path: str = Query(default="/var/lib/php/sessions"),
    session_gc_maxlifetime: int = Query(default=1440),
    # Logging
    error_reporting: str = Query(default="E_ALL & ~E_DEPRECATED & ~E_STRICT"),
    error_log: str = Query(default=None),
    log_errors: bool = Query(default=True),
    display_errors: str = Query(default="Off"),
    slowlog: str = Query(default=None),
    request_slowlog_timeout: str = Query(default="10s"),
    current_user: User = Depends(get_current_user)
):
    """
    Update php.ini settings for a PHP version.

    Supports the following configuration options:

    **Upload & Timeout Limits:**
    - upload_max_filesize: Maximum upload file size (e.g., "128M", "1024M")
    - post_max_size: Maximum POST data size
    - max_execution_time: Maximum script execution time in seconds
    - max_input_time: Maximum time for input parsing
    - max_input_vars: Maximum number of input variables
    - memory_limit: PHP memory limit

    **Disabled Functions:**
    - disable_functions: Comma-separated list of functions to disable

    **Optimization Settings:**
    - opcache_enable: Enable/disable OPcache
    - opcache_memory_consumption: OPcache memory in MB
    - opcache_max_accelerated_files: Maximum number of files to cache
    - opcache_validate_timestamps: Check file timestamps for changes
    - realpath_cache_size: Realpath cache size

    **Session Configuration:**
    - session_save_handler: Session handler (files, redis, memcached)
    - session_save_path: Session save path
    - session_gc_maxlifetime: Session garbage collection lifetime

    **Logging:**
    - error_reporting: Error reporting level
    - error_log: Error log file path
    - log_errors: Enable/disable error logging
    - display_errors: Enable/disable error display
    - slowlog: Slow query log path
    - request_slowlog_timeout: Slow request timeout
    """
    ensure_role(current_user.role, Role.admin)

    # Parse disable_functions from comma-separated string
    disable_functions_list = [f.strip() for f in disable_functions.split(",") if f.strip()] if disable_functions else []

    settings = {
        "upload_max_filesize": upload_max_filesize,
        "post_max_size": post_max_size,
        "max_execution_time": max_execution_time,
        "max_input_time": max_input_time,
        "max_input_vars": max_input_vars,
        "memory_limit": memory_limit,
        "disable_functions": disable_functions_list,
        "opcache.enable": "1" if opcache_enable else "0",
        "opcache.memory_consumption": str(opcache_memory_consumption),
        "opcache.max_accelerated_files": str(opcache_max_accelerated_files),
        "opcache.validate_timestamps": "1" if opcache_validate_timestamps else "0",
        "realpath_cache_size": realpath_cache_size,
        "session.save_handler": session_save_handler,
        "session.save_path": session_save_path,
        "session.gc_maxlifetime": str(session_gc_maxlifetime),
        "error_reporting": error_reporting,
        "log_errors": "1" if log_errors else "0",
        "display_errors": display_errors,
        "request_slowlog_timeout": request_slowlog_timeout,
    }

    # Add optional logging paths if provided
    if error_log:
        settings["error_log"] = error_log
    if slowlog:
        settings["slowlog"] = slowlog

    try:
        result = php_versions.update_php_config(version, settings)
        if not result.get("success", False) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# =============================================================================
# FPM Pool Management
# =============================================================================

@router.get("/{version}/fpm/pools")
def list_php_fpm_pools(version: str, current_user: User = Depends(get_current_user)):
    """
    List all FPM pool configurations for a PHP version.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        return php_versions.get_php_fpm_pools(version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class FpmPoolCreateRequest:
    """Request model for creating FPM pool."""

    def __init__(
        self,
        pool_name: str,
        # Pool Settings
        listen: str = None,
        listen_owner: str = "www-data",
        listen_group: str = "www-data",
        listen_mode: str = "0660",
        user: str = "www-data",
        group: str = "www-data",
        # Process Manager Settings
        pm: str = "dynamic",
        pm_max_children: int = 10,
        pm_start_servers: int = 2,
        pm_min_spare_servers: int = 1,
        pm_max_spare_servers: int = 3,
        pm_max_requests: int = 500,
        pm_process_idle_timeout: str = "10s",
        # Status & Logging
        pm_status_path: str = None,
        ping_path: str = None,
        slowlog: str = None,
        request_slowlog_timeout: str = "10s",
    ):
        self.pool_name = pool_name
        self.listen = listen
        self.listen_owner = listen_owner
        self.listen_group = listen_group
        self.listen_mode = listen_mode
        self.user = user
        self.group = group
        self.pm = pm
        self.pm_max_children = pm_max_children
        self.pm_start_servers = pm_start_servers
        self.pm_min_spare_servers = pm_min_spare_servers
        self.pm_max_spare_servers = pm_max_spare_servers
        self.pm_max_requests = pm_max_requests
        self.pm_process_idle_timeout = pm_process_idle_timeout
        self.pm_status_path = pm_status_path
        self.ping_path = ping_path
        self.slowlog = slowlog
        self.request_slowlog_timeout = request_slowlog_timeout


@router.post("/{version}/fpm/pools")
def create_php_fpm_pool(
    version: str,
    pool_name: str = Query(...),
    # Pool Settings
    listen: str = Query(default=None),
    listen_owner: str = Query(default="www-data"),
    listen_group: str = Query(default="www-data"),
    listen_mode: str = Query(default="0660"),
    user: str = Query(default="www-data"),
    group: str = Query(default="www-data"),
    # Process Manager Settings
    pm: str = Query(default="dynamic"),
    pm_max_children: int = Query(default=10),
    pm_start_servers: int = Query(default=2),
    pm_min_spare_servers: int = Query(default=1),
    pm_max_spare_servers: int = Query(default=3),
    pm_max_requests: int = Query(default=500),
    pm_process_idle_timeout: str = Query(default="10s"),
    # Status & Logging
    pm_status_path: str = Query(default=None),
    ping_path: str = Query(default=None),
    slowlog: str = Query(default=None),
    request_slowlog_timeout: str = Query(default="10s"),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new FPM pool configuration.

    **Pool Settings:**
    - pool_name: Unique name for the pool (alphanumeric, hyphens, underscores)
    - listen: Socket path or address:port
    - listen_owner/listen_group/listen_mode: Socket permissions
    - user/group: Unix user/group for the pool

    **Process Manager Settings:**
    - pm: Process manager type (dynamic, static, ondemand)
    - pm_max_children: Maximum number of child processes
    - pm_start_servers: Number of children created on startup (dynamic)
    - pm_min_spare_servers: Minimum idle processes (dynamic)
    - pm_max_spare_servers: Maximum idle processes (dynamic)
    - pm_max_requests: Requests per child before respawn
    - pm_process_idle_timeout: Idle timeout for ondemand manager

    **Status & Logging:**
    - pm_status_path: Path for status page
    - ping_path: Path for ping endpoint
    - slowlog: Slow query log path
    - request_slowlog_timeout: Slow request threshold
    """
    ensure_role(current_user.role, Role.admin)

    settings = {}
    if listen:
        settings["listen"] = listen
    settings["listen.owner"] = listen_owner
    settings["listen.group"] = listen_group
    settings["listen.mode"] = listen_mode
    settings["user"] = user
    settings["group"] = group
    settings["pm"] = pm
    settings["pm.max_children"] = str(pm_max_children)
    settings["pm.start_servers"] = str(pm_start_servers)
    settings["pm.min_spare_servers"] = str(pm_min_spare_servers)
    settings["pm.max_spare_servers"] = str(pm_max_spare_servers)
    settings["pm.max_requests"] = str(pm_max_requests)
    settings["pm.process_idle_timeout"] = pm_process_idle_timeout
    if pm_status_path:
        settings["pm.status_path"] = pm_status_path
    if ping_path:
        settings["ping.path"] = ping_path
    if slowlog:
        settings["slowlog"] = slowlog
    settings["request_slowlog_timeout"] = request_slowlog_timeout

    try:
        result = php_versions.create_php_fpm_pool(version, pool_name, settings)
        if not result.get("success", False) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{version}/fpm/pools/{pool_name}")
def update_php_fpm_pool(
    version: str,
    pool_name: str,
    # Pool Settings
    listen: str = Query(default=None),
    listen_owner: str = Query(default=None),
    listen_group: str = Query(default=None),
    listen_mode: str = Query(default=None),
    user: str = Query(default=None),
    group: str = Query(default=None),
    # Process Manager Settings
    pm: str = Query(default=None),
    pm_max_children: int = Query(default=None),
    pm_start_servers: int = Query(default=None),
    pm_min_spare_servers: int = Query(default=None),
    pm_max_spare_servers: int = Query(default=None),
    pm_max_requests: int = Query(default=None),
    pm_process_idle_timeout: str = Query(default=None),
    # Status & Logging
    pm_status_path: str = Query(default=None),
    ping_path: str = Query(default=None),
    slowlog: str = Query(default=None),
    request_slowlog_timeout: str = Query(default=None),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing FPM pool configuration.

    Only provided settings will be updated. Omit a setting to keep its current value.
    """
    ensure_role(current_user.role, Role.admin)

    settings = {}
    if listen is not None:
        settings["listen"] = listen
    if listen_owner is not None:
        settings["listen.owner"] = listen_owner
    if listen_group is not None:
        settings["listen.group"] = listen_group
    if listen_mode is not None:
        settings["listen.mode"] = listen_mode
    if user is not None:
        settings["user"] = user
    if group is not None:
        settings["group"] = group
    if pm is not None:
        settings["pm"] = pm
    if pm_max_children is not None:
        settings["pm.max_children"] = str(pm_max_children)
    if pm_start_servers is not None:
        settings["pm.start_servers"] = str(pm_start_servers)
    if pm_min_spare_servers is not None:
        settings["pm.min_spare_servers"] = str(pm_min_spare_servers)
    if pm_max_spare_servers is not None:
        settings["pm.max_spare_servers"] = str(pm_max_spare_servers)
    if pm_max_requests is not None:
        settings["pm.max_requests"] = str(pm_max_requests)
    if pm_process_idle_timeout is not None:
        settings["pm.process_idle_timeout"] = pm_process_idle_timeout
    if pm_status_path is not None:
        settings["pm.status_path"] = pm_status_path
    if ping_path is not None:
        settings["ping.path"] = ping_path
    if slowlog is not None:
        settings["slowlog"] = slowlog
    if request_slowlog_timeout is not None:
        settings["request_slowlog_timeout"] = request_slowlog_timeout

    if not settings:
        raise HTTPException(status_code=400, detail="No settings provided for update")

    try:
        result = php_versions.update_php_fpm_pool(version, pool_name, settings)
        if not result.get("success", False) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{version}/fpm/restart")
def restart_php_fpm(version: str, current_user: User = Depends(get_current_user)):
    """
    Restart PHP-FPM service for a specific version.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        result = php_versions.restart_php_fpm(version)
        if not result.get("success", False) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{version}/load")
def get_php_fpm_load(version: str, current_user: User = Depends(get_current_user)):
    """
    Get PHP-FPM status and load information.
    Returns process count, memory usage, and running status.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        return php_versions.get_php_fpm_load(version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# =============================================================================
# Logging & Diagnostics
# =============================================================================

@router.get("/{version}/slowlog")
def get_php_slow_log(
    version: str,
    lines: int = Query(default=100, ge=10, le=5000),
    current_user: User = Depends(get_current_user)
):
    """
    Get PHP-FPM slow query log for a version.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        return php_versions.get_php_slow_log(version, lines)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{version}/errorlog")
def get_php_error_log(
    version: str,
    lines: int = Query(default=100, ge=10, le=5000),
    current_user: User = Depends(get_current_user)
):
    """
    Get PHP-FPM error log for a version.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        return php_versions.get_php_error_log(version, lines)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{version}/phpinfo")
def get_phpinfo(version: str, current_user: User = Depends(get_current_user)):
    """
    Get phpinfo() output for a PHP version.
    Returns full PHP configuration information.
    """
    ensure_role(current_user.role, Role.admin)
    try:
        return php_versions.get_phpinfo(version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# =============================================================================
# Optimization
# =============================================================================

@router.post("/{version}/optimize")
def optimize_php_version(
    version: str,
    # Custom optimization settings (uses defaults if not provided)
    memory_limit: str = Query(default="512M"),
    opcache_memory: int = Query(default=256),
    opcache_max_files: int = Query(default=20000),
    opcache_validate_timestamps: bool = Query(default=False),
    realpath_cache_size: str = Query(default="4096K"),
    max_execution_time: int = Query(default=300),
    current_user: User = Depends(get_current_user)
):
    """
    Apply optimization settings for a PHP version.

    This endpoint applies recommended production optimization settings.
    Custom values can override the defaults.

    **Default Optimization Settings:**
    - opcache.enable: 1
    - opcache.memory_consumption: 256MB
    - opcache.max_accelerated_files: 20000
    - opcache.validate_timestamps: 0 (disabled for production)
    - realpath_cache_size: 4096K
    - max_execution_time: 300
    - memory_limit: 512M
    - display_errors: Off
    - log_errors: On
    """
    ensure_role(current_user.role, Role.admin)

    settings = {
        "memory_limit": memory_limit,
        "opcache.memory_consumption": str(opcache_memory),
        "opcache.max_accelerated_files": str(opcache_max_files),
        "opcache.validate_timestamps": "1" if opcache_validate_timestamps else "0",
        "realpath_cache_size": realpath_cache_size,
        "max_execution_time": str(max_execution_time),
        "display_errors": "Off",
        "log_errors": "1",
    }

    try:
        result = php_versions.optimize_php(version, settings)
        if not result.get("success", False) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
