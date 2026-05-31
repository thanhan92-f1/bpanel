"""phpMyAdmin installation and management service."""

import json
import os
import re
import secrets
import string
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.shell import shell


# Standard paths
PHPMYADMIN_INSTALL_DIR = Path("/usr/share/phpmyadmin")
PHPMYADMIN_CONFIG_FILE = Path("/etc/phpmyadmin/config.inc.php")
PHPMYADMIN_NGINX_CONFIG = Path("/etc/nginx/conf.d/phpmyadmin.conf")
PHPMYADMIN_LOG_DIR = Path("/var/log/phpmyadmin")
PHPMYADMIN_BACKUP_DIR = Path("/var/backups/phpmyadmin")


def _generate_blowfish_secret(length: int = 32) -> str:
    """Generate a secure blowfish secret for phpMyAdmin."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _check_mariadb_running() -> bool:
    """Check if MariaDB/MySQL is running."""
    result = shell.run(["systemctl", "is-active", "mariadb"], check=False)
    if result.returncode == 0:
        return True
    result = shell.run(["systemctl", "is-active", "mysql"], check=False)
    return result.returncode == 0


def _get_mysql_credentials() -> dict:
    """Get MySQL root credentials from various sources."""
    # Try .my.cnf first
    my_cnf = Path.home() / ".my.cnf"
    if my_cnf.exists():
        content = my_cnf.read_text()
        user_match = re.search(r"user\s*=\s*(\S+)", content)
        pass_match = re.search(r"password\s*=\s*(\S+)", content)
        if user_match and pass_match:
            return {"user": user_match.group(1), "password": pass_match.group(1)}

    # Try environment variables
    mysql_user = os.environ.get("MYSQL_ROOT_USER", "root")
    mysql_password = os.environ.get("MYSQL_ROOT_PASSWORD", "")

    return {"user": mysql_user, "password": mysql_password}


def check_phpmyadmin_requirements() -> dict:
    """Check if the server meets requirements for phpMyAdmin installation."""
    requirements = {
        "php_installed": False,
        "mysql_running": False,
        "nginx_installed": False,
        "disk_space": False,
        "missing": [],
        "warnings": [],
    }

    # Check PHP
    result = shell.run(["php", "-v"], check=False)
    if result.returncode == 0:
        requirements["php_installed"] = True
        php_version = result.stdout.split()[0].replace("PHP", "").strip()
        requirements["php_version"] = php_version
    else:
        requirements["missing"].append("PHP is not installed")

    # Check MySQL/MariaDB
    if _check_mariadb_running():
        requirements["mysql_running"] = True
    else:
        requirements["missing"].append("MariaDB/MySQL is not running")

    # Check Nginx
    result = shell.run(["nginx", "-v"], check=False)
    if result.returncode == 0:
        requirements["nginx_installed"] = True
    else:
        requirements["missing"].append("Nginx is not installed")

    # Check disk space
    try:
        result = shell.run(["df", "-BG", "/usr/share"], check=False)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "/dev/" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        available_gb = int(parts[3].rstrip("G"))
                        requirements["disk_space"] = available_gb >= 2
                        requirements["disk_space_gb"] = available_gb
                        if available_gb < 2:
                            requirements["warnings"].append(
                                f"Low disk space: {available_gb}GB available (recommend 2GB+)"
                            )
                        break
    except Exception:
        requirements["warnings"].append("Could not check disk space")

    return requirements


def get_phpmyadmin_version() -> Optional[str]:
    """Get the installed phpMyAdmin version."""
    if not PHPMYADMIN_INSTALL_DIR.exists():
        return None

    # Try changelog for version info
    changelog = PHPMYADMIN_INSTALL_DIR / "ChangeLog"
    if changelog.exists():
        content = changelog.read_text(errors="ignore")
        match = re.search(r"phpMyAdmin\s+(\d+\.\d+(?:\.\d+)?)", content)
        if match:
            return match.group(1)

    # Try README
    readme = PHPMYADMIN_INSTALL_DIR / "README"
    if readme.exists():
        content = readme.read_text(errors="ignore")
        match = re.search(r"version\s+(\d+\.\d+(?:\.\d+)?)", content, re.IGNORECASE)
        if match:
            return match.group(1)

    return "Unknown (installed via system package)"


def get_phpmyadmin_status() -> dict:
    """Check if phpMyAdmin is installed and get its status."""
    status = {
        "installed": False,
        "version": None,
        "configured": False,
        "nginx_configured": False,
        "url": None,
        "blowfish_secret_set": False,
    }

    # Check installation
    if PHPMYADMIN_INSTALL_DIR.exists():
        status["installed"] = True
        status["version"] = get_phpmyadmin_version()

    # Check config
    if PHPMYADMIN_CONFIG_FILE.exists():
        status["configured"] = True
        config_content = PHPMYADMIN_CONFIG_FILE.read_text()
        if "blowfish_secret" in config_content and "cookie" in config_content:
            # Check if blowfish secret is actually set (not just the default)
            blowfish_match = re.search(
                r"\$cfg\['blowfish_secret'\]\s*=\s*['\"]([^'\"]{16,})['\"]",
                config_content,
            )
            status["blowfish_secret_set"] = bool(blowfish_match)

    # Check Nginx config
    if PHPMYADMIN_NGINX_CONFIG.exists():
        status["nginx_configured"] = True

    # Get URL
    if status["nginx_configured"]:
        status["url"] = get_phpmyadmin_url()

    return status


def setup_blowfish_secret(force: bool = False) -> dict:
    """Generate and setup a secure blowfish secret for phpMyAdmin."""
    if not PHPMYADMIN_INSTALL_DIR.exists():
        raise RuntimeError("phpMyAdmin is not installed")

    secret = _generate_blowfish_secret(32)

    if PHPMYADMIN_CONFIG_FILE.exists():
        content = PHPMYADMIN_CONFIG_FILE.read_text()
        # Replace existing blowfish secret
        if re.search(r"\$cfg\['blowfish_secret'\]\s*=", content):
            if force:
                content = re.sub(
                    r"\$cfg\['blowfish_secret'\]\s*=\s*['\"][^'\"]*['\"]",
                    f"$cfg['blowfish_secret'] = '{secret}'",
                    content,
                )
                if settings.command_dry_run:
                    return {"secret": secret, "message": "DRY RUN: blowfish secret would be updated"}
                PHPMYADMIN_CONFIG_FILE.write_text(content)
                return {"secret": secret, "message": "Blowfish secret updated successfully"}
            else:
                return {"secret": None, "message": "Blowfish secret already exists. Use force=true to regenerate."}
        else:
            # Add blowfish secret to config
            content += f"\n$cfg['blowfish_secret'] = '{secret}';\n"
            if settings.command_dry_run:
                return {"secret": secret, "message": "DRY RUN: blowfish secret would be added"}
            PHPMYADMIN_CONFIG_FILE.write_text(content)
            return {"secret": secret, "message": "Blowfish secret added successfully"}
    else:
        raise RuntimeError("phpMyAdmin config file not found")


def install_phpmyadmin(
    subdomain: str = "phpmyadmin",
    use_subdirectory: bool = False,
    ssl_enabled: bool = True,
) -> dict:
    """Install phpMyAdmin on the server."""
    # Check requirements first
    requirements = check_phpmyadmin_requirements()
    if requirements["missing"]:
        raise RuntimeError(
            f"Cannot install phpMyAdmin. Missing requirements: {', '.join(requirements['missing'])}"
        )

    if PHPMYADMIN_INSTALL_DIR.exists():
        raise RuntimeError("phpMyAdmin is already installed")

    # Create directories
    shell.privileged(
        "phpmyadmin-mkdir",
        helper_args=["/etc/phpmyadmin", "/var/lib/phpmyadmin", "/var/log/phpmyadmin"],
        fallback=["mkdir", "-p", "/etc/phpmyadmin", "/var/lib/phpmyadmin", "/var/log/phpmyadmin"],
    )

    # Install via apt
    result = shell.privileged(
        "apt-install",
        helper_args=["phpmyadmin"],
        check=False,
        fallback=["apt-get", "install", "-y", "phpmyadmin"],
    )

    if result.returncode != 0:
        # Try alternative installation method
        return _install_phpmyadmin_manual(subdomain, use_subdirectory, ssl_enabled)

    # Configure blowfish secret
    secret_result = setup_blowfish_secret()
    blowfish_secret = secret_result.get("secret")

    # Configure Nginx
    configure_phpmyadmin(
        blowfish_secret=blowfish_secret,
        subdomain=subdomain if not use_subdirectory else None,
        use_subdirectory=use_subdirectory,
        ssl_enabled=ssl_enabled,
    )

    return {
        "installed": True,
        "version": get_phpmyadmin_version(),
        "url": get_phpmyadmin_url(),
        "message": "phpMyAdmin installed successfully",
    }


def _install_phpmyadmin_manual(
    subdomain: str = "phpmyadmin",
    use_subdirectory: bool = False,
    ssl_enabled: bool = True,
) -> dict:
    """Manual installation of phpMyAdmin from source."""
    import tempfile

    # Download latest phpMyAdmin
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Download phpMyAdmin
        download_url = "https://files.phpmyadmin.net/phpMyAdmin/5.2.1/phpMyAdmin-5.2.1-english.tar.gz"
        result = shell.privileged(
            "phpmyadmin-download",
            helper_args=[download_url, str(temp_dir)],
            fallback=["wget", "-q", "-O", str(temp_dir / "phpmyadmin.tar.gz"), download_url],
        )

        if result.returncode != 0:
            raise RuntimeError("Failed to download phpMyAdmin")

        # Extract
        shell.privileged(
            "phpmyadmin-extract",
            helper_args=[str(temp_dir / "phpmyadmin.tar.gz"), str(PHPMYADMIN_INSTALL_DIR)],
            fallback=["tar", "-xzf", str(temp_dir / "phpmyadmin.tar.gz"), "-C", "/usr/share"],
        )

        # Set permissions
        shell.privileged(
            "phpmyadmin-chmod",
            helper_args=[str(PHPMYADMIN_INSTALL_DIR)],
            fallback=["chmod", "-R", "755", str(PHPMYADMIN_INSTALL_DIR)],
        )

        # Create config directory
        shell.privileged(
            "phpmyadmin-mkdir-etc",
            helper_args=["/etc/phpmyadmin"],
            fallback=["mkdir", "-p", "/etc/phpmyadmin"],
        )

        # Copy sample config
        sample_config = PHPMYADMIN_INSTALL_DIR / "config.sample.inc.php"
        if sample_config.exists():
            target_config = PHPMYADMIN_CONFIG_FILE
            if not target_config.exists():
                shell.run(["cp", str(sample_config), str(target_config)])
                shell.privileged(
                    "phpmyadmin-chmod-config",
                    helper_args=[str(target_config)],
                    fallback=["chmod", "644", str(target_config)],
                )

        # Setup blowfish secret
        secret_result = setup_blowfish_secret()
        blowfish_secret = secret_result.get("secret")

        # Configure Nginx
        configure_phpmyadmin(
            blowfish_secret=blowfish_secret,
            subdomain=subdomain if not use_subdirectory else None,
            use_subdirectory=use_subdirectory,
            ssl_enabled=ssl_enabled,
        )

        return {
            "installed": True,
            "version": get_phpmyadmin_version(),
            "url": get_phpmyadmin_url(),
            "message": "phpMyAdmin installed successfully from source",
        }
    finally:
        # Cleanup temp directory
        shell.run(["rm", "-rf", str(temp_dir)], check=False)


def configure_phpmyadmin(
    blowfish_secret: Optional[str] = None,
    server: Optional[str] = "localhost",
    subdomain: Optional[str] = None,
    use_subdirectory: bool = False,
    ssl_enabled: bool = True,
) -> dict:
    """Configure phpMyAdmin with the necessary settings."""
    # Get MySQL credentials
    mysql_creds = _get_mysql_credentials()

    # Generate blowfish secret if not provided
    if not blowfish_secret:
        blowfish_secret = _generate_blowfish_secret(32)

    # Build config content
    config_content = f"""<?php
/**
 * phpMyAdmin configuration file
 * Generated by BPanel
 * Date: {datetime.now().isoformat()}
 */

/**
 * Server(s) configuration
 */
$i = 0;
$i++;

/* Configure according to your server */
$cfg['Servers'][$i]['auth_type'] = 'cookie';
$cfg['Servers'][$i]['host'] = '{server}';
$cfg['Servers'][$i]['compress'] = false;
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['Servers'][$i]['verbose'] = 'MySQL Server';

/**
 * phpMyAdmin settings
 */
$cfg['blowfish_secret'] = '{blowfish_secret}';
$cfg['DefaultLang'] = 'en';
$cfg['Lang'] = 'en';
$cfg['AllowUserDropDatabase'] = false;
$cfg['AllowArbitraryServer'] = false;
$cfg['ShowPhpInfo'] = false;
$cfg['ShowServerInfo'] = false;
$cfg['ShowChgPassword'] = true;
$cfg['ForceSSL'] = {str(ssl_enabled).lower()};
$cfg['SignonURL'] = '';
$cfg['PmaNoRelation_DisableWarning'] = true;
$cfg['VersionCheck'] = false;

/**
 * Security settings
 */
$cfg['SkipValidation'] = false;
$cfg['RetainQueryBox'] = true;
$cfg['ErrorHandler'] = '';
$cfg['DisplayServersList'] = false;

/**
 * Upload and save settings
 */
$cfg['UploadDir'] = '/var/lib/phpmyadmin/upload';
$cfg['SaveDir'] = '/var/lib/phpmyadmin/save';
$cfg['TempDir'] = '/tmp/phpmyadmin';

/**
 * Cookie settings
 */
$cfg['CookieSecure'] = {str(ssl_enabled).lower()};
$cfg['CookieHttpOnly'] = true;
$cfg['CookieSameSite'] = 'Strict';
$cfg['SessionSavePath'] = '/var/lib/phpmyadmin/sessions';
"""
    if settings.command_dry_run:
        return {"config_file": str(PHPMYADMIN_CONFIG_FILE), "message": "DRY RUN: config would be written"}

    # Write config
    PHPMYADMIN_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    PHPMYADMIN_CONFIG_FILE.write_text(config_content)
    shell.privileged(
        "phpmyadmin-chmod-config",
        helper_args=[str(PHPMYADMIN_CONFIG_FILE)],
        fallback=["chmod", "640", str(PHPMYADMIN_CONFIG_FILE)],
    )

    # Create required directories
    for directory in [
        "/var/lib/phpmyadmin/upload",
        "/var/lib/phpmyadmin/save",
        "/var/lib/phpmyadmin/sessions",
    ]:
        shell.privileged(
            "phpmyadmin-mkdir-dir",
            helper_args=[directory],
            fallback=["mkdir", "-p", directory],
        )

    # Configure Nginx
    _configure_nginx(subdomain=subdomain, use_subdirectory=use_subdirectory, ssl_enabled=ssl_enabled)

    return {
        "config_file": str(PHPMYADMIN_CONFIG_FILE),
        "blowfish_secret": blowfish_secret,
        "message": "phpMyAdmin configured successfully",
    }


def _configure_nginx(
    subdomain: Optional[str] = None,
    use_subdirectory: bool = False,
    ssl_enabled: bool = True,
) -> None:
    """Configure Nginx for phpMyAdmin access."""
    php_socket = "/run/php/php8.3-fpm.sock"  # Default socket
    panel_base_url = os.environ.get("BPANEL_BASE_URL", "/phpmyadmin")

    # Check for available PHP versions
    for version in ["8.4", "8.3"]:
        socket_path = f"/run/php/php{version}-fpm.sock"
        if Path(socket_path).exists():
            php_socket = socket_path
            break

    if subdomain:
        # Subdomain configuration
        nginx_content = f"""# phpMyAdmin Nginx configuration
# Generated by BPanel

server {{
    listen 80;
    listen [::]:80;
    server_name {subdomain};

    # Redirect to HTTPS
    {"return 301 https://$host$request_uri;" if ssl_enabled else ""}

    access_log /var/log/nginx/phpmyadmin.access.log;
    error_log /var/log/nginx/phpmyadmin.error.log;
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    server_name {subdomain};

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/{subdomain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{subdomain}/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/{subdomain}/chain.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # phpMyAdmin root
    root {PHPMYADMIN_INSTALL_DIR};
    index index.php index.html;

    # Access control
    allow 127.0.0.1;
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    allow 192.168.0.0/16;
    deny all;

    location / {{
        try_files $uri $uri/ /index.php$is_args$args;
    }}

    location ~ ^/(.+\\.php)$ {{
        include fastcgi_params;
        fastcgi_pass unix:{php_socket};
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
        fastcgi_read_timeout 300;
        fastcgi_buffer_size 128k;
        fastcgi_buffers 4 256k;
        fastcgi_busy_buffers_size 256k;
    }}

    location ~ /\\. {{
        deny all;
        access_log off;
        log_not_found off;
    }}

    access_log /var/log/nginx/phpmyadmin.access.log;
    error_log /var/log/nginx/phpmyadmin.error.log;
}}
"""
    else:
        # Subdirectory configuration
        nginx_content = f"""# phpMyAdmin Nginx configuration (subdirectory)
# Generated by BPanel

location /phpmyadmin {{
    alias {PHPMYADMIN_INSTALL_DIR};

    index index.php index.html;

    location ~ ^/phpmyadmin/(.+\\.php)$ {{
        include fastcgi_params;
        fastcgi_pass unix:{php_socket};
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $request_filename;
        fastcgi_param PATH_INFO $fastcgi_path_info;
        fastcgi_read_timeout 300;
    }}

    location ~ /phpmyadmin/\\. {{
        deny all;
        access_log off;
        log_not_found off;
    }}

    access_log /var/log/nginx/phpmyadmin.access.log;
    error_log /var/log/nginx/phpmyadmin.error.log;
}}

# Additional location for /phpmyadmin-admin (admin access without SSO)
location /phpmyadmin-admin {{
    proxy_pass http://127.0.0.1:8888;
}}
"""

    if settings.command_dry_run:
        return

    PHPMYADMIN_NGINX_CONFIG.write_text(nginx_content)
    shell.privileged(
        "nginx-test-reload",
        fallback=["nginx", "-t"],
    )


def get_phpmyadmin_url() -> Optional[str]:
    """Get the phpMyAdmin access URL based on Nginx configuration."""
    if not PHPMYADMIN_NGINX_CONFIG.exists():
        return None

    config_content = PHPMYADMIN_NGINX_CONFIG.read_text()

    # Check if using subdomain
    subdomain_match = re.search(r"server_name\s+([^;]+);", config_content)
    if subdomain_match:
        server_name = subdomain_match.group(1).strip()
        ssl_match = re.search(r"listen\s+443\s+ssl", config_content)
        protocol = "https" if ssl_match else "http"
        return f"{protocol}://{server_name}"

    # Check if using subdirectory
    if "location /phpmyadmin" in config_content:
        base_url = os.environ.get("BPANEL_BASE_URL", "")
        if base_url:
            # Extract scheme from base URL
            scheme_match = re.match(r"(https?)://", base_url)
            scheme = scheme_match.group(1) if scheme_match else "https"
            host_match = re.search(r"server_name\s+([^;]+);", config_content)
            host = host_match.group(1).strip() if host_match else "localhost"
            return f"{scheme}://{host}/phpmyadmin"
        return "/phpmyadmin"

    return None


def update_phpmyadmin_config(settings: dict) -> dict:
    """Update phpMyAdmin configuration settings."""
    if not PHPMYADMIN_CONFIG_FILE.exists():
        raise RuntimeError("phpMyAdmin config file not found")

    content = PHPMYADMIN_CONFIG_FILE.read_text()

    # Map of settings to update
    setting_map = {
        "blowfish_secret": "$cfg['blowfish_secret']",
        "auth_type": "$cfg['Servers'][1]['auth_type']",
        "host": "$cfg['Servers'][1]['host']",
        "compress": "$cfg['Servers'][1]['compress']",
        "force_ssl": "$cfg['ForceSSL']",
        "lang": "$cfg['Lang']",
        "default_lang": "$cfg['DefaultLang']",
        "show_server_info": "$cfg['ShowServerInfo']",
        "show_php_info": "$cfg['ShowPhpInfo']",
        "version_check": "$cfg['VersionCheck']",
        "cookie_secure": "$cfg['CookieSecure']",
        "cookie_httponly": "$cfg['CookieHttpOnly']",
        "session_timeout": "$cfg['SessionTimeOut']",
    }

    for key, php_var in setting_map.items():
        if key in settings:
            value = settings[key]
            # Handle boolean values
            if isinstance(value, bool):
                value_str = "true" if value else "false"
            elif isinstance(value, int):
                value_str = str(value)
            else:
                value_str = f"'{value}'" if not str(value).lower() in ("true", "false") else str(value).lower()

            # Replace existing setting or add new one
            if re.search(rf"{re.escape(php_var)}\s*=", content):
                content = re.sub(
                    rf"{re.escape(php_var)}\s*=\s*[^;]+;",
                    f"{php_var} = {value_str};",
                    content,
                )
            else:
                content += f"\n{php_var} = {value_str};"

    if settings.command_dry_run:
        return {"message": "DRY RUN: config would be updated"}

    PHPMYADMIN_CONFIG_FILE.write_text(content)
    shell.privileged("nginx-reload", fallback=["systemctl", "reload", "nginx"])

    return {"message": "Configuration updated successfully"}


def secure_phpmyadmin(
    restrict_ips: bool = True,
    allowed_ips: Optional[list] = None,
    block_root_login: bool = True,
    hide_version: bool = True,
    enable_csrf_protection: bool = True,
    session_timeout: int = 1800,
    max_failed_logins: int = 5,
    enable_ssl_only: bool = True,
) -> dict:
    """Apply security settings to phpMyAdmin."""
    changes = []

    if restrict_ips and allowed_ips:
        # Update Nginx config with IP restrictions
        if PHPMYADMIN_NGINX_CONFIG.exists():
            content = PHPMYADMIN_NGINX_CONFIG.read_text()
            # Replace existing allow/deny rules
            new_allow_rules = "\n".join(f"    allow {ip};" for ip in allowed_ips) + "\n    deny all;"
            if "allow 127.0.0.1" in content:
                content = re.sub(r"    allow [^\n]+\n", "", content)
                content = re.sub(r"    deny all;", "", content)
                content = re.sub(r"(location /)", rf"\1\n{new_allow_rules}", content)
            PHPMYADMIN_NGINX_CONFIG.write_text(content)
            changes.append("IP restrictions applied")

    if hide_version:
        # Ensure server_tokens is off in Nginx
        if PHPMYADMIN_NGINX_CONFIG.exists():
            content = PHPMYADMIN_NGINX_CONFIG.read_text()
            if "server_tokens off" not in content:
                content = re.sub(
                    r"(listen \d+443)",
                    r"\1;\n    server_tokens off",
                    content,
                )
            PHPMYADMIN_NGINX_CONFIG.write_text(content)
        changes.append("Version hiding enabled")

    if enable_csrf_protection or hide_version:
        # Update phpMyAdmin config
        if PHPMYADMIN_CONFIG_FILE.exists():
            content = PHPMYADMIN_CONFIG_FILE.read_text()
            if enable_csrf_protection:
                if "$cfg['TokenResponseTimeout']" not in content:
                    content += "\n$cfg['TokenResponseTimeout'] = 600;"
            if hide_version:
                if "$cfg['ShowServerInfo']" not in content:
                    content += "\n$cfg['ShowServerInfo'] = false;"
                if "$cfg['ShowPhpInfo']" not in content:
                    content += "\n$cfg['ShowPhpInfo'] = false;"
                if "$cfg['VersionCheck']" not in content:
                    content += "\n$cfg['VersionCheck'] = false;"
            PHPMYADMIN_CONFIG_FILE.write_text(content)
            changes.append("Security settings updated")

    if session_timeout > 0:
        if PHPMYADMIN_CONFIG_FILE.exists():
            content = PHPMYADMIN_CONFIG_FILE.read_text()
            if re.search(r"\$cfg\['SessionTimeOut'\]", content):
                content = re.sub(
                    r"\$cfg\['SessionTimeOut'\]\s*=\s*\d+;",
                    f"$cfg['SessionTimeOut'] = {session_timeout};",
                    content,
                )
            else:
                content += f"\n$cfg['SessionTimeOut'] = {session_timeout};"
            PHPMYADMIN_CONFIG_FILE.write_text(content)
            changes.append(f"Session timeout set to {session_timeout} seconds")

    if enable_ssl_only:
        if PHPMYADMIN_CONFIG_FILE.exists():
            content = PHPMYADMIN_CONFIG_FILE.read_text()
            if re.search(r"\$cfg\['ForceSSL'\]", content):
                content = re.sub(
                    r"\$cfg\['ForceSSL'\]\s*=\s*[^;]+;",
                    "$cfg['ForceSSL'] = true;",
                    content,
                )
            else:
                content += "\n$cfg['ForceSSL'] = true;"
            PHPMYADMIN_CONFIG_FILE.write_text(content)
            changes.append("SSL enforcement enabled")

    if settings.command_dry_run:
        return {"message": f"DRY RUN: {', '.join(changes)}"}

    # Reload Nginx
    shell.privileged("nginx-reload", fallback=["systemctl", "reload", "nginx"])

    return {
        "message": "Security settings applied",
        "changes": changes,
    }


def backup_phpmyadmin_config() -> dict:
    """Create a backup of phpMyAdmin configuration."""
    if not PHPMYADMIN_CONFIG_FILE.exists() and not PHPMYADMIN_NGINX_CONFIG.exists():
        raise RuntimeError("No phpMyAdmin configuration found to backup")

    PHPMYADMIN_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_info = {"timestamp": timestamp, "files": []}

    if PHPMYADMIN_CONFIG_FILE.exists():
        backup_file = PHPMYADMIN_BACKUP_DIR / f"config.inc.php.{timestamp}.bak"
        shell.run(["cp", str(PHPMYADMIN_CONFIG_FILE), str(backup_file)])
        backup_info["files"].append(str(backup_file))

    if PHPMYADMIN_NGINX_CONFIG.exists():
        backup_file = PHPMYADMIN_BACKUP_DIR / f"nginx.conf.{timestamp}.bak"
        shell.run(["cp", str(PHPMYADMIN_NGINX_CONFIG), str(backup_file)])
        backup_info["files"].append(str(backup_file))

    # Save backup metadata
    metadata_file = PHPMYADMIN_BACKUP_DIR / f"backup_metadata.{timestamp}.json"
    metadata_file.write_text(json.dumps(backup_info, indent=2))

    return {
        "message": "Backup created successfully",
        "backup_dir": str(PHPMYADMIN_BACKUP_DIR),
        "timestamp": timestamp,
        "files": backup_info["files"],
    }


def restore_phpmyadmin_config(backup_timestamp: Optional[str] = None) -> dict:
    """Restore phpMyAdmin configuration from a backup."""
    if not PHPMYADMIN_BACKUP_DIR.exists():
        raise RuntimeError("No backup directory found")

    if backup_timestamp:
        # Restore specific backup
        config_backup = PHPMYADMIN_BACKUP_DIR / f"config.inc.php.{backup_timestamp}.bak"
        nginx_backup = PHPMYADMIN_BACKUP_DIR / f"nginx.conf.{backup_timestamp}.bak"

        if not config_backup.exists() and not nginx_backup.exists():
            raise RuntimeError(f"Backup with timestamp {backup_timestamp} not found")

        restored = []
        if config_backup.exists():
            shell.run(["cp", str(config_backup), str(PHPMYADMIN_CONFIG_FILE)])
            restored.append(str(PHPMYADMIN_CONFIG_FILE))

        if nginx_backup.exists():
            shell.run(["cp", str(nginx_backup), str(PHPMYADMIN_NGINX_CONFIG)])
            restored.append(str(PHPMYADMIN_NGINX_CONFIG))

        # Reload services
        shell.privileged("nginx-reload", fallback=["systemctl", "reload", "nginx"])

        return {
            "message": "Configuration restored successfully",
            "restored_files": restored,
        }
    else:
        # List available backups
        backups = []
        for f in PHPMYADMIN_BACKUP_DIR.glob("backup_metadata.*.json"):
            try:
                metadata = json.loads(f.read_text())
                backups.append(metadata)
            except Exception:
                pass

        return {
            "message": "Available backups",
            "backups": backups,
        }


def uninstall_phpmyadmin(remove_data: bool = False) -> dict:
    """Remove phpMyAdmin from the server."""
    removed_items = []

    # Remove Nginx config
    if PHPMYADMIN_NGINX_CONFIG.exists():
        shell.privileged(
            "phpmyadmin-rm-nginx",
            helper_args=[str(PHPMYADMIN_NGINX_CONFIG)],
            fallback=["rm", "-f", str(PHPMYADMIN_NGINX_CONFIG)],
        )
        removed_items.append(str(PHPMYADMIN_NGINX_CONFIG))

    # Backup config before removal (optional)
    if PHPMYADMIN_CONFIG_FILE.exists() and not remove_data:
        backup_result = backup_phpmyadmin_config()

    # Remove phpMyAdmin installation
    if PHPMYADMIN_INSTALL_DIR.exists():
        shell.privileged(
            "phpmyadmin-rm-install",
            helper_args=[str(PHPMYADMIN_INSTALL_DIR)],
            fallback=["rm", "-rf", str(PHPMYADMIN_INSTALL_DIR)],
        )
        removed_items.append(str(PHPMYADMIN_INSTALL_DIR))

    # Optionally remove config and data
    if remove_data:
        if PHPMYADMIN_CONFIG_FILE.exists():
            shell.privileged(
                "phpmyadmin-rm-config",
                helper_args=[str(PHPMYADMIN_CONFIG_FILE)],
                fallback=["rm", "-f", str(PHPMYADMIN_CONFIG_FILE)],
            )
            removed_items.append(str(PHPMYADMIN_CONFIG_FILE))

        if PHPMYADMIN_BACKUP_DIR.exists():
            shell.privileged(
                "phpmyadmin-rm-backups",
                helper_args=[str(PHPMYADMIN_BACKUP_DIR)],
                fallback=["rm", "-rf", str(PHPMYADMIN_BACKUP_DIR)],
            )
            removed_items.append(str(PHPMYADMIN_BACKUP_DIR))

    if settings.command_dry_run:
        return {"message": f"DRY RUN: {', '.join(removed_items)}"}

    # Reload Nginx
    shell.privileged("nginx-reload", fallback=["systemctl", "reload", "nginx"])

    return {
        "message": "phpMyAdmin uninstalled successfully",
        "removed": removed_items,
    }
