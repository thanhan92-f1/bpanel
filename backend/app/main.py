import logging
import os
import time
from collections import defaultdict
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, auto_update, backup_enhanced, cron_jobs, databases, docker, firewall, ftp, golang, logs, maintenance, mailserver, monitor, nginx_proxy, nodejs, panel_settings as panel_settings_api, php_versions, phpmyadmin, python_project, services, settings, terminal, updates, users, waf, webserver, websites, wordpress_toolkit
from app.core.config import settings
from app.core.database import run_migrations
from app.services import panel_settings as panel_brand_settings

run_migrations()

# Secure default umask: files get 644 (-rw-r--r--), dirs get 755 (rwxr-xr-x)
os.umask(0o022)

logger = logging.getLogger("bpanel")


# Rate limiting configuration
class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.requests = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client_id."""
        now = time.time()
        minute_ago = now - 60

        with self.lock:
            # Clean old requests
            self.requests[client_id] = [
                t for t in self.requests[client_id] if t > minute_ago
            ]

            # Check rate limit
            if len(self.requests[client_id]) >= self.requests_per_minute:
                return False

            # Check burst limit
            recent = [t for t in self.requests[client_id] if t > now - 1]
            if len(recent) >= self.burst_size:
                return False

            # Record request
            self.requests[client_id].append(now)
            return True


rate_limiter = RateLimiter(requests_per_minute=60, burst_size=10)

app = FastAPI(title="BPanel API", version="0.1.0")

# Refuse to start in production with unsafe defaults.
if settings.app_env.lower() == "production":
    if settings.command_dry_run:
        raise RuntimeError(
            "COMMAND_DRY_RUN must be False in production. "
            "Set COMMAND_DRY_RUN=false in the environment."
        )

cors_origins = settings.cors_origins
if not cors_origins and settings.app_env != "production":
    cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled request error: %s %s", request.method, request.url.path)
    if settings.app_env.lower() == "production":
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "accelerometer=(), autoplay=(), camera=(), display-capture=(), encrypted-media=(), "
        "fullscreen=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), midi=(), "
        "payment=(), usb=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'",
    )
    if settings.app_env.lower() == "production":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware to prevent API abuse."""
    # Skip rate limiting for health check and static files
    path = request.url.path
    if path in ["/api/health"] or path.startswith("/assets/") or path.startswith("/favicon"):
        return await call_next(request)

    # Get client identifier (prefer X-Forwarded-For if behind proxy)
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"

    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
            headers={"Retry-After": "60"},
        )

    return await call_next(request)


app.include_router(auth.router, prefix="/api")
app.include_router(auto_update.router, prefix="/api")
app.include_router(backup_enhanced.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(websites.router, prefix="/api")
app.include_router(databases.router, prefix="/api")
app.include_router(firewall.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(updates.router, prefix="/api")
app.include_router(waf.router, prefix="/api")
app.include_router(maintenance.router, prefix="/api")
app.include_router(panel_settings_api.router, prefix="/api")
app.include_router(terminal.router, prefix="/api")
app.include_router(wordpress_toolkit.router, prefix="/api")
app.include_router(docker.router, prefix="/api")
app.include_router(ftp.router, prefix="/api")
app.include_router(mailserver.router, prefix="/api")
app.include_router(nodejs.router, prefix="/api")
app.include_router(php_versions.router, prefix="/api")
app.include_router(phpmyadmin.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")
app.include_router(cron_jobs.router, prefix="/api")
app.include_router(golang.router, prefix="/api")
app.include_router(python_project.router, prefix="/api")
app.include_router(nginx_proxy.router, prefix="/api")
app.include_router(webserver.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(logs.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "name": panel_brand_settings.current_settings().get("app_name") or "BPanel"}


frontend_dist = Path(settings.frontend_dist)
assets_dir = frontend_dist / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/favicon.png", include_in_schema=False)
def favicon():
    custom = panel_brand_settings.current_settings().get("favicon_url") or ""
    if custom.startswith("/brand-assets/"):
        filename = custom.split("/brand-assets/", 1)[1].split("?", 1)[0]
        path, media_type = panel_brand_settings.asset_path(filename)
        return FileResponse(path, media_type=media_type)
    path = frontend_dist / "favicon.png"
    if path.exists():
        return FileResponse(path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/brand-assets/{filename}", include_in_schema=False)
def brand_asset(filename: str):
    path, media_type = panel_brand_settings.asset_path(filename)
    return FileResponse(path, media_type=media_type)


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    """Serve the built React app directly from FastAPI on the panel port."""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    index = frontend_dist / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"detail": "Frontend build not found", "path": str(index)}
