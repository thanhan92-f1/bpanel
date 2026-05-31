"""
Nginx Reverse Proxy Management Service.

Provides easy proxy setup with SSL, templates, and configuration management.
"""

import json
import re
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.shell import CommandResult, shell

# Configuration paths
PROXY_CONFIG_DIR = Path(settings.nginx_sites_available) / "proxy"
LETSENCRYPT_DIR = "/etc/letsencrypt/live"

# Proxy configuration storage
PROXY_CONFIG_FILE = Path("/var/lib/bpanel/proxy_configs.json")

# Preset Templates with configurations
TEMPLATES = {
    "default": {
        "name": "Default Proxy",
        "connect_timeout": "60s",
        "send_timeout": "60s",
        "read_timeout": "60s",
    },
    "websocket": {
        "name": "WebSocket Proxy",
        "connect_timeout": "600s",
        "send_timeout": "600s",
        "read_timeout": "600s",
        "extra": """
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;""",
    },
    "php": {
        "name": "PHP/FastCGI Proxy",
        "connect_timeout": "60s",
        "send_timeout": "60s",
        "read_timeout": "300s",
    },
    "nodejs": {
        "name": "Node.js Proxy",
        "connect_timeout": "30s",
        "send_timeout": "300s",
        "read_timeout": "300s",
    },
    "static": {
        "name": "Static Files",
        "connect_timeout": "10s",
        "send_timeout": "60s",
        "read_timeout": "60s",
        "extra": """
    expires 7d;
    add_header Cache-Control "public, immutable";""",
    },
    "python": {
        "name": "Python/Flask/Django",
        "connect_timeout": "60s",
        "send_timeout": "300s",
        "read_timeout": "300s",
    },
    "go": {
        "name": "Go Application",
        "connect_timeout": "30s",
        "send_timeout": "300s",
        "read_timeout": "300s",
    },
    "java": {
        "name": "Java Application",
        "connect_timeout": "120s",
        "send_timeout": "300s",
        "read_timeout": "300s",
    },
}

# Proxy Template
PROXY_TEMPLATE = """# BPanel Proxy Config - {domain}
# Generated: {timestamp}

server {{
    listen 80;
    server_name {domain};

    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {domain};

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # HTTP/2 Optimization
    http2_push_preload on;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    # Proxy Settings
    location / {{
        proxy_pass {target_url};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout {connect_timeout};
        proxy_send_timeout {send_timeout};
        proxy_read_timeout {read_timeout};

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        {extra_directives}
    }}

    # Health Check Endpoint
    location /health {{
        access_log off;
        return 200 "OK";
        add_header Content-Type text/plain;
    }}

    # Logs
    access_log /var/log/nginx/{domain}.access.log;
    error_log /var/log/nginx/{domain}.error.log;
}}
"""

# Basic HTTP Template (no SSL)
PROXY_TEMPLATE_NO_SSL = """# BPanel Proxy Config - {domain}
# Generated: {timestamp}

server {{
    listen 80;
    server_name {domain};

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    # Proxy Settings
    location / {{
        proxy_pass {target_url};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout {connect_timeout};
        proxy_send_timeout {send_timeout};
        proxy_read_timeout {read_timeout};

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        {extra_directives}
    }}

    # Health Check Endpoint
    location /health {{
        access_log off;
        return 200 "OK";
        add_header Content-Type text/plain;
    }}

    # Logs
    access_log /var/log/nginx/{domain}.access.log;
    error_log /var/log/nginx/{domain}.error.log;
}}
"""

# Rate Limiting Template
RATE_LIMIT_CONFIG = """
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=proxy_limit:10m rate={rate_limit}r/s;
    limit_req zone=proxy_limit burst={burst} nodelay;
"""

# Domain validation regex
DOMAIN_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+")


def _validate_domain(domain: str) -> str:
    """Validate and normalize domain name."""
    safe_domain = (domain or "").strip().lower()
    if not DOMAIN_RE.fullmatch(safe_domain):
        raise ValueError("Invalid domain format")
    return safe_domain


def _ensure_config_dir() -> None:
    """Ensure proxy config directory exists."""
    PROXY_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PROXY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_proxy_configs() -> dict:
    """Load proxy configurations from storage."""
    _ensure_config_dir()
    if not PROXY_CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(PROXY_CONFIG_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return {}


def _save_proxy_configs(configs: dict) -> None:
    """Save proxy configurations to storage."""
    _ensure_config_dir()
    PROXY_CONFIG_FILE.write_text(json.dumps(configs, indent=2))


def _config_path(domain: str) -> Path:
    """Get the nginx config file path for a domain."""
    return PROXY_CONFIG_DIR / f"{domain}.conf"


def _detect_target_app(target_url: str) -> str:
    """Auto-detect the application type based on target URL and port."""
    from urllib.parse import urlparse
    parsed = urlparse(target_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    detection_map = {
        3000: "nodejs",
        3001: "nodejs",
        5000: "python",
        5001: "python",
        8000: "python",
        8080: "java",
        8443: "java",
        9000: "php",
    }
    return detection_map.get(port, "default")


def list_proxy_configs() -> list[dict]:
    """List all proxy configurations."""
    configs = _load_proxy_configs()
    result = []
    for domain, config in configs.items():
        config_path = _config_path(domain)
        result.append({
            "domain": domain,
            "target_url": config.get("target_url", ""),
            "ssl": config.get("ssl", True),
            "template": config.get("template", "default"),
            "rate_limit": config.get("rate_limit"),
            "enabled": config_path.exists(),
            "created_at": config.get("created_at"),
            "updated_at": config.get("updated_at"),
        })
    return result


def create_proxy_config(
    domain: str,
    target_url: str,
    ssl: bool = True,
    options: dict = None,
) -> dict:
    """Create a new proxy configuration."""
    options = options or {}
    safe_domain = _validate_domain(domain)

    # Check if config already exists
    configs = _load_proxy_configs()
    if safe_domain in configs:
        raise ValueError(f"Proxy config for {safe_domain} already exists")

    # Detect template if not specified
    template_name = options.get("template", _detect_target_app(target_url))
    if template_name not in TEMPLATES:
        template_name = "default"

    template_config = TEMPLATES[template_name].copy()
    template_config["name"] = template_name

    # Get template values with defaults
    connect_timeout = options.get("connect_timeout", template_config.get("connect_timeout", "60s"))
    send_timeout = options.get("send_timeout", template_config.get("send_timeout", "60s"))
    read_timeout = options.get("read_timeout", template_config.get("read_timeout", "60s"))
    extra = template_config.get("extra", "")

    # Handle rate limiting
    rate_limit = options.get("rate_limit")
    if rate_limit:
        burst = options.get("burst", 20)
        rate_limit_config = RATE_LIMIT_CONFIG.format(
            rate_limit=rate_limit,
            burst=burst
        )
        extra += rate_limit_config

    # Get target URL with proper scheme
    if not target_url.startswith(("http://", "https://")):
        target_url = "http://" + target_url

    # Format target URL to ensure trailing slash
    if not target_url.endswith("/"):
        target_url += "/"

    from datetime import datetime
    timestamp = datetime.utcnow().isoformat()

    # Generate nginx config
    if ssl:
        config_content = PROXY_TEMPLATE.format(
            domain=safe_domain,
            target_url=target_url.rstrip("/"),
            timestamp=timestamp,
            connect_timeout=connect_timeout,
            send_timeout=send_timeout,
            read_timeout=read_timeout,
            extra_directives=extra.strip() if extra else "",
        )
    else:
        config_content = PROXY_TEMPLATE_NO_SSL.format(
            domain=safe_domain,
            target_url=target_url.rstrip("/"),
            timestamp=timestamp,
            connect_timeout=connect_timeout,
            send_timeout=send_timeout,
            read_timeout=read_timeout,
            extra_directives=extra.strip() if extra else "",
        )

    # Save nginx config
    config_path = _config_path(safe_domain)
    if not settings.command_dry_run:
        _ensure_config_dir()
        config_path.write_text(config_content, encoding="utf-8")
        _enable_config(safe_domain)
    else:
        # In dry run mode, just return the config content
        pass

    # Save proxy config metadata
    configs[safe_domain] = {
        "target_url": target_url,
        "ssl": ssl,
        "template": template_name,
        "rate_limit": rate_limit,
        "connect_timeout": connect_timeout,
        "send_timeout": send_timeout,
        "read_timeout": read_timeout,
        "created_at": timestamp,
        "updated_at": timestamp,
        "config_content": config_content if settings.command_dry_run else None,
    }
    _save_proxy_configs(configs)

    # Reload nginx
    if not settings.command_dry_run:
        reload_nginx()

    return {
        "domain": safe_domain,
        "target_url": target_url,
        "ssl": ssl,
        "template": template_name,
        "rate_limit": rate_limit,
        "enabled": True,
        "config_path": str(config_path),
    }


def update_proxy_config(
    domain: str,
    target_url: str = None,
    ssl: bool = None,
    options: dict = None,
) -> dict:
    """Update an existing proxy configuration."""
    options = options or {}
    safe_domain = _validate_domain(domain)

    configs = _load_proxy_configs()
    if safe_domain not in configs:
        raise ValueError(f"Proxy config for {safe_domain} not found")

    current_config = configs[safe_domain]
    template_name = options.get("template", current_config.get("template", "default"))

    if template_name not in TEMPLATES:
        template_name = "default"

    template_config = TEMPLATES[template_name].copy()

    # Update values
    new_target = target_url if target_url else current_config["target_url"]
    new_ssl = ssl if ssl is not None else current_config["ssl"]

    # Add scheme if missing
    if not new_target.startswith(("http://", "https://")):
        new_target = "http://" + new_target
    if not new_target.endswith("/"):
        new_target += "/"

    connect_timeout = options.get("connect_timeout", template_config.get("connect_timeout", "60s"))
    send_timeout = options.get("send_timeout", template_config.get("send_timeout", "60s"))
    read_timeout = options.get("read_timeout", template_config.get("read_timeout", "60s"))
    extra = template_config.get("extra", "")

    # Handle rate limiting
    rate_limit = options.get("rate_limit", current_config.get("rate_limit"))
    if rate_limit:
        burst = options.get("burst", 20)
        rate_limit_config = RATE_LIMIT_CONFIG.format(
            rate_limit=rate_limit,
            burst=burst
        )
        extra += rate_limit_config

    from datetime import datetime
    timestamp = datetime.utcnow().isoformat()

    # Generate nginx config
    if new_ssl:
        config_content = PROXY_TEMPLATE.format(
            domain=safe_domain,
            target_url=new_target.rstrip("/"),
            timestamp=timestamp,
            connect_timeout=connect_timeout,
            send_timeout=send_timeout,
            read_timeout=read_timeout,
            extra_directives=extra.strip() if extra else "",
        )
    else:
        config_content = PROXY_TEMPLATE_NO_SSL.format(
            domain=safe_domain,
            target_url=new_target.rstrip("/"),
            timestamp=timestamp,
            connect_timeout=connect_timeout,
            send_timeout=send_timeout,
            read_timeout=read_timeout,
            extra_directives=extra.strip() if extra else "",
        )

    # Save nginx config
    config_path = _config_path(safe_domain)
    if not settings.command_dry_run:
        config_path.write_text(config_content, encoding="utf-8")
    else:
        pass

    # Update proxy config metadata
    configs[safe_domain].update({
        "target_url": new_target,
        "ssl": new_ssl,
        "template": template_name,
        "rate_limit": rate_limit,
        "connect_timeout": connect_timeout,
        "send_timeout": send_timeout,
        "read_timeout": read_timeout,
        "updated_at": timestamp,
        "config_content": config_content if settings.command_dry_run else None,
    })
    _save_proxy_configs(configs)

    # Reload nginx
    if not settings.command_dry_run:
        reload_nginx()

    return {
        "domain": safe_domain,
        "target_url": new_target,
        "ssl": new_ssl,
        "template": template_name,
        "rate_limit": rate_limit,
        "enabled": True,
        "config_path": str(config_path),
    }


def delete_proxy_config(domain: str) -> dict:
    """Delete a proxy configuration."""
    safe_domain = _validate_domain(domain)

    configs = _load_proxy_configs()
    if safe_domain not in configs:
        raise ValueError(f"Proxy config for {safe_domain} not found")

    config_path = _config_path(safe_domain)

    # Remove nginx config
    if not settings.command_dry_run:
        _disable_config(safe_domain)
        if config_path.exists():
            config_path.unlink()

    # Remove from configs
    del configs[safe_domain]
    _save_proxy_configs(configs)

    # Reload nginx
    if not settings.command_dry_run:
        reload_nginx()

    return {
        "domain": safe_domain,
        "deleted": True,
    }


def get_proxy_config(domain: str) -> Optional[dict]:
    """Get a specific proxy configuration."""
    safe_domain = _validate_domain(domain)

    configs = _load_proxy_configs()
    if safe_domain not in configs:
        return None

    config = configs[safe_domain]
    config_path = _config_path(safe_domain)

    result = {
        "domain": safe_domain,
        "target_url": config.get("target_url", ""),
        "ssl": config.get("ssl", True),
        "template": config.get("template", "default"),
        "rate_limit": config.get("rate_limit"),
        "enabled": config_path.exists(),
        "created_at": config.get("created_at"),
        "updated_at": config.get("updated_at"),
    }

    # Include SSL status if SSL is enabled
    if config.get("ssl"):
        result["ssl_status"] = get_ssl_status(safe_domain)

    return result


def _enable_config(domain: str) -> None:
    """Enable nginx config by creating symlink if needed."""
    enabled_dir = Path(settings.nginx_sites_available)
    config_path = _config_path(domain)
    if config_path.exists():
        # Config is already in the sites-available directory
        shell.privileged(
            "nginx-test",
            check=False,
            fallback=["nginx", "-t"]
        )


def _disable_config(domain: str) -> None:
    """Disable nginx config."""
    pass


# SSL Management Functions

def setup_ssl(domain: str, letsencrypt: bool = True) -> dict:
    """Setup SSL for a domain."""
    safe_domain = _validate_domain(domain)

    if not letsencrypt:
        raise ValueError("Only Let's Encrypt is supported at this time")

    # Check if domain config exists
    configs = _load_proxy_configs()
    if safe_domain not in configs:
        raise ValueError(f"Proxy config for {safe_domain} not found")

    # Get SSL email if configured
    email = settings.ssl_email or ""
    helper_args = [safe_domain]
    if email:
        helper_args.append(email)

    # Run certbot
    result = shell.privileged(
        "certbot-issue",
        helper_args=helper_args,
        check=False,
        fallback=[
            "certbot", "certonly", "--nginx", "-d", safe_domain,
            "--non-interactive", "--agree-tos", "--redirect",
            *(["--email", email] if email else ["--register-unsafely-without-email"])
        ]
    )

    if result.returncode != 0:
        return {
            "domain": safe_domain,
            "success": False,
            "error": result.stderr or result.stdout or "SSL setup failed",
        }

    # Update config to enable SSL
    configs[safe_domain]["ssl"] = True
    _save_proxy_configs(configs)

    # Regenerate config with SSL
    update_proxy_config(safe_domain, options={"ssl": True})

    return {
        "domain": safe_domain,
        "success": True,
        "ssl_type": "letsencrypt",
        "cert_path": f"{LETSENCRYPT_DIR}/{safe_domain}/fullchain.pem",
    }


def renew_ssl(domain: str) -> dict:
    """Renew SSL certificate for a domain."""
    safe_domain = _validate_domain(domain)

    result = shell.privileged(
        "certbot-renew-domain",
        helper_args=[safe_domain],
        check=False,
        fallback=["certbot", "renew", "--cert-name", safe_domain, "--quiet"]
    )

    if result.returncode != 0:
        return {
            "domain": safe_domain,
            "success": False,
            "renewed": False,
            "error": result.stderr or result.stdout or "SSL renewal failed",
        }

    return {
        "domain": safe_domain,
        "success": True,
        "renewed": True,
    }


def auto_ssl_setup(domain: str) -> dict:
    """Automatically setup SSL with Let's Encrypt for a domain."""
    safe_domain = _validate_domain(domain)

    # First ensure we have a basic HTTP config
    configs = _load_proxy_configs()
    if safe_domain not in configs:
        # Create basic config
        create_proxy_config(safe_domain, f"http://localhost:8080", ssl=False)

    # Try to setup SSL
    ssl_result = setup_ssl(safe_domain, letsencrypt=True)

    if ssl_result.get("success"):
        return ssl_result

    # If SSL setup failed, check if it's because certs don't exist yet
    cert_path = Path(f"{LETSENCRYPT_DIR}/{safe_domain}")
    if not cert_path.exists():
        return {
            "domain": safe_domain,
            "success": False,
            "error": "Please ensure the domain DNS is pointing to this server and port 80 is accessible",
            "pending_verification": True,
        }

    return ssl_result


def get_ssl_status(domain: str) -> dict:
    """Get SSL status for a domain."""
    safe_domain = _validate_domain(domain)

    cert_path = Path(f"{LETSENCRYPT_DIR}/{safe_domain}/fullchain.pem")
    key_path = Path(f"{LETSENCRYPT_DIR}/{safe_domain}/privkey.pem")

    if not cert_path.exists():
        return {
            "domain": safe_domain,
            "enabled": False,
            "provider": None,
            "expires": None,
            "days_remaining": None,
        }

    # Get certificate info
    result = shell.privileged(
        "openssl-x509",
        helper_args=["-noout", "-dates", "-subject", "-issuer"],
        check=False,
        fallback=["openssl", "x509", "-noout", "-dates", "-subject", "-issuer", "-in", str(cert_path)]
    )

    from datetime import datetime
    expires = None
    days_remaining = None

    if result.returncode == 0:
        output = result.stdout or ""
        for line in output.splitlines():
            if "notAfter=" in line:
                date_str = line.split("notAfter=")[1].strip()
                try:
                    expires = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                    days_remaining = (expires - datetime.utcnow()).days
                except ValueError:
                    pass

    return {
        "domain": safe_domain,
        "enabled": True,
        "provider": "letsencrypt",
        "cert_path": str(cert_path),
        "key_path": str(key_path),
        "expires": expires.isoformat() if expires else None,
        "days_remaining": days_remaining,
        "auto_renewal": True,
    }


# Template Functions

def list_proxy_templates() -> dict:
    """List available proxy templates."""
    return {
        "templates": [
            {
                "id": key,
                "name": value["name"],
                "connect_timeout": value.get("connect_timeout", "60s"),
                "send_timeout": value.get("send_timeout", "60s"),
                "read_timeout": value.get("read_timeout", "60s"),
                "has_extra": "extra" in value,
            }
            for key, value in TEMPLATES.items()
        ]
    }


def create_from_template(domain: str, template: str, options: dict = None) -> dict:
    """Create a proxy configuration from a template."""
    options = options or {}
    safe_domain = _validate_domain(domain)

    if template not in TEMPLATES:
        raise ValueError(f"Unknown template: {template}")

    # Detect target if not provided
    target_url = options.get("target_url", f"http://localhost:8080")
    ssl = options.get("ssl", True)

    options["template"] = template

    return create_proxy_config(safe_domain, target_url, ssl=ssl, options=options)


# Nginx Configuration Functions

def test_nginx_config() -> dict:
    """Test nginx configuration."""
    result = shell.privileged(
        "nginx-test",
        check=False,
        fallback=["nginx", "-t"]
    )

    return {
        "success": result.returncode == 0,
        "output": result.stdout or result.stderr or "",
        "returncode": result.returncode,
    }


def reload_nginx() -> dict:
    """Reload nginx configuration."""
    result = shell.privileged(
        "nginx-reload",
        check=False,
        fallback=["systemctl", "reload", "nginx"]
    )

    if result.returncode != 0:
        return {
            "success": False,
            "error": result.stderr or result.stdout or "Nginx reload failed",
        }

    return {
        "success": True,
        "message": "Nginx reloaded successfully",
    }


def restart_nginx() -> dict:
    """Restart nginx service."""
    result = shell.privileged(
        "nginx-restart",
        check=False,
        fallback=["systemctl", "restart", "nginx"]
    )

    if result.returncode != 0:
        return {
            "success": False,
            "error": result.stderr or result.stdout or "Nginx restart failed",
        }

    return {
        "success": True,
        "message": "Nginx restarted successfully",
    }


def get_nginx_status() -> dict:
    """Get nginx service status."""
    result = shell.privileged(
        "nginx-status",
        check=False,
        fallback=["systemctl", "is-active", "nginx"]
    )

    active = result.returncode == 0 and "active" in (result.stdout or "").lower()

    # Get additional info
    test_result = shell.privileged(
        "nginx-test",
        check=False,
        fallback=["nginx", "-t"]
    )
    config_valid = test_result.returncode == 0

    return {
        "running": active,
        "config_valid": config_valid,
        "config_valid_output": test_result.stdout or test_result.stderr or "",
    }
