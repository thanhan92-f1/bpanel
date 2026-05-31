import json
import re
import secrets as _secrets
from pathlib import Path
from typing import Dict

from app.core.config import settings
from app.services import site_users
from app.services.shell import shell


# Strict whitelists for values fed to WP-CLI to prevent flag injection.
WP_USER_RE = re.compile(r"^[A-Za-z0-9._@-]{3,60}$")
WP_TITLE_RE = re.compile(r"^[\w\s.,'\-:!()&]{1,150}$", re.UNICODE)
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{3,255}$")


WP_SALT_KEYS = (
    "AUTH_KEY", "SECURE_AUTH_KEY", "LOGGED_IN_KEY", "NONCE_KEY",
    "AUTH_SALT", "SECURE_AUTH_SALT", "LOGGED_IN_SALT", "NONCE_SALT",
)


def _generate_wp_salts() -> str:
    lines = []
    for key in WP_SALT_KEYS:
        salt = _secrets.token_urlsafe(48).replace("'", "")
        lines.append(f"define('{key}', '{salt}');")
    return "\n".join(lines)


def _render_wp_config(db_name: str, db_user: str, db_password: str) -> str:
    """Render wp-config.php directly so the DB password never appears in argv.

    PHP single-quoted strings only need ' and \\ escaping.
    """
    def esc(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    return (
        "<?php\n"
        f"define('DB_NAME', '{esc(db_name)}');\n"
        f"define('DB_USER', '{esc(db_user)}');\n"
        f"define('DB_PASSWORD', '{esc(db_password)}');\n"
        "define('DB_HOST', 'localhost');\n"
        "define('DB_CHARSET', 'utf8mb4');\n"
        "define('DB_COLLATE', '');\n"
        "\n"
        "$table_prefix = 'wp_';\n"
        "\n"
        f"{_generate_wp_salts()}\n"
        "\n"
        "define('WP_DEBUG', false);\n"
        "if ( ! defined('ABSPATH') ) {\n"
        "    define('ABSPATH', __DIR__ . '/');\n"
        "}\n"
        "require_once ABSPATH . 'wp-settings.php';\n"
    )


def _safe_value(value: str, pattern: re.Pattern, label: str) -> str:
    value = (value or "").strip()
    if value.startswith("-") or "\x00" in value or not pattern.fullmatch(value):
        raise ValueError(f"Invalid {label}")
    return value


def site_root(domain: str) -> str:
    return site_users.site_root_for_domain(domain)


def install_wordpress(
    domain: str,
    db: Dict[str, str],
    title: str,
    admin_user: str,
    admin_password: str,
    admin_email: str,
    php_version: str,
    linux_user: str | None = None,
    root_path: str | None = None,
) -> str:
    safe_user = _safe_value(admin_user, WP_USER_RE, "WordPress admin username")
    safe_title = _safe_value(title, WP_TITLE_RE, "WordPress site title")
    safe_email = _safe_value(admin_email, EMAIL_RE, "WordPress admin email")
    if not isinstance(admin_password, str) or len(admin_password) < 10 or "\x00" in admin_password:
        raise ValueError("WordPress admin password must be at least 10 characters")

    root = Path(root_path or site_root(domain))
    public = site_users.document_root(root)
    linux_user = linux_user or site_users.ensure_site_runtime(domain, str(root), php_version)
    wp_path = f"--path={public}"

    # WP-CLI runs as this website's isolated Linux user through the helper.
    shell.privileged(
        "wp-site",
        helper_args=[linux_user, "core", "download", wp_path],
        fallback=["wp", "core", "download", wp_path],
    )

    # Render wp-config.php directly to avoid leaking the DB password through
    # argv (which would be visible to other local users via /proc/<pid>/cmdline
    # or `ps auxww` while wp config create runs).
    config_path = public / "wp-config.php"
    config_content = _render_wp_config(db["db_name"], db["db_user"], db["db_password"])
    if not settings.command_dry_run:
        config_path.write_text(config_content, encoding="utf-8")
        try:
            config_path.chmod(0o640)
        except PermissionError:
            pass
    shell.privileged(
        "site-path-fix",
        helper_args=[str(public), linux_user],
        check=False,
        fallback=["chown", "-R", f"{linux_user}:{linux_user}", str(public)],
    )

    install_args = [
        "core", "install", wp_path,
        f"--url=https://{domain}",
        f"--title={safe_title}",
        f"--admin_user={safe_user}",
        f"--admin_email={safe_email}",
        "--prompt=admin_password",
        "--skip-email",
        "--allow-root",
    ]
    shell.privileged(
        "wp-site",
        helper_args=[linux_user, *install_args],
        fallback=["wp", *install_args],
        input=admin_password + "\n",
        sensitive=True,
    )

    fix_permissions(str(root), linux_user)
    return str(root)


def fix_permissions(root_path: str, linux_user: str | None = None):
    return site_users.fix_site_permissions(root_path, linux_user)


def wp_update(path: str, action: str, linux_user: str | None = None):
    if action == "core":
        args = ["core", "update", f"--path={path}", "--allow-root"]
    elif action == "plugins":
        args = ["plugin", "update", "--all", f"--path={path}", "--allow-root"]
    elif action == "themes":
        args = ["theme", "update", "--all", f"--path={path}", "--allow-root"]
    else:
        raise ValueError("Unsupported WordPress action")
    if linux_user:
        return shell.privileged("wp-site", helper_args=[linux_user, *args], fallback=["wp", *args])
    return shell.privileged("wp", helper_args=args, fallback=["wp", *args])


def reset_admin_password(path: str, user: str, password: str, linux_user: str | None = None):
    safe_user = _safe_value(user, WP_USER_RE, "WordPress username")
    if not isinstance(password, str) or len(password) < 10 or "\x00" in password:
        raise ValueError("Password must be at least 10 characters")
    args = ["user", "update", safe_user, "--user_pass=/dev/stdin", f"--path={path}", "--allow-root"]
    return shell.privileged(
        "wp-site" if linux_user else "wp",
        helper_args=[linux_user, *args] if linux_user else args,
        fallback=["wp", *args],
        input=password,
        sensitive=True,
    )


def delete_wordpress(root_path: str):
    target = Path(root_path).resolve()
    if not site_users.is_managed_site_path(target):
        raise ValueError("Refusing to delete path outside managed site roots")
    return shell.privileged(
        "rm-site",
        helper_args=[str(target)],
        fallback=["rm", "-rf", str(target)],
    )


def _wp_cli_args(path: str, linux_user: str | None = None) -> list:
    """Build common WP-CLI arguments for a given path and user."""
    args = ["--path=" + path, "--allow-root"]
    if linux_user:
        return shell.privileged, [linux_user, "wp", *args], ["wp", *args]
    return shell.privileged, args, ["wp", *args]


def list_plugins(path: str, linux_user: str | None = None) -> list:
    """List all installed WordPress plugins."""
    wp_args = ["plugin", "list", "--format=json", f"--path={path}", "--allow-root"]
    privileged_fn, helper_args, fallback_args = (shell.privileged, [linux_user, *wp_args], ["wp", *wp_args]) if linux_user else (None, None, None)
    if privileged_fn:
        result = privileged_fn("wp-site" if linux_user else "wp", helper_args=helper_args, fallback=fallback_args)
    else:
        result = shell.privileged("wp", helper_args=wp_args, fallback=["wp", *wp_args])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to list plugins: {result.stderr or result.stdout}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON response from wp plugin list: {result.stdout}")


def activate_plugin(path: str, plugin: str, linux_user: str | None = None):
    """Activate a WordPress plugin."""
    args = ["plugin", "activate", plugin, f"--path={path}", "--allow-root"]
    helper = ["wp-site", [linux_user, *args], ["wp", *args]] if linux_user else None
    if helper:
        result = shell.privileged(helper[0], helper_args=helper[1], fallback=helper[2])
    else:
        result = shell.privileged("wp", helper_args=args, fallback=["wp", *args])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to activate plugin '{plugin}': {result.stderr or result.stdout}")
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def deactivate_plugin(path: str, plugin: str, linux_user: str | None = None):
    """Deactivate a WordPress plugin."""
    args = ["plugin", "deactivate", plugin, f"--path={path}", "--allow-root"]
    helper = ["wp-site", [linux_user, *args], ["wp", *args]] if linux_user else None
    if helper:
        result = shell.privileged(helper[0], helper_args=helper[1], fallback=helper[2])
    else:
        result = shell.privileged("wp", helper_args=args, fallback=["wp", *args])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to deactivate plugin '{plugin}': {result.stderr or result.stdout}")
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def delete_plugin(path: str, plugin: str, linux_user: str | None = None):
    """Delete a WordPress plugin."""
    args = ["plugin", "delete", plugin, f"--path={path}", "--allow-root"]
    helper = ["wp-site", [linux_user, *args], ["wp", *args]] if linux_user else None
    if helper:
        result = shell.privileged(helper[0], helper_args=helper[1], fallback=helper[2])
    else:
        result = shell.privileged("wp", helper_args=args, fallback=["wp", *args])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to delete plugin '{plugin}': {result.stderr or result.stdout}")
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def list_themes(path: str, linux_user: str | None = None) -> list:
    """List all installed WordPress themes."""
    args = ["theme", "list", "--format=json", f"--path={path}", "--allow-root"]
    helper = ["wp-site", [linux_user, *args], ["wp", *args]] if linux_user else None
    if helper:
        result = shell.privileged(helper[0], helper_args=helper[1], fallback=helper[2])
    else:
        result = shell.privileged("wp", helper_args=args, fallback=["wp", *args])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to list themes: {result.stderr or result.stdout}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON response from wp theme list: {result.stdout}")


def activate_theme(path: str, theme: str, linux_user: str | None = None):
    """Activate a WordPress theme."""
    args = ["theme", "activate", theme, f"--path={path}", "--allow-root"]
    helper = ["wp-site", [linux_user, *args], ["wp", *args]] if linux_user else None
    if helper:
        result = shell.privileged(helper[0], helper_args=helper[1], fallback=helper[2])
    else:
        result = shell.privileged("wp", helper_args=args, fallback=["wp", *args])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to activate theme '{theme}': {result.stderr or result.stdout}")
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def wp_health_check(path: str, linux_user: str | None = None) -> dict:
    """Run WordPress health check using wp doctor."""
    args = ["doctor", "check", "--all", f"--path={path}", "--allow-root"]
    helper = ["wp-site", [linux_user, *args], ["wp", *args]] if linux_user else None
    if helper:
        result = shell.privileged(helper[0], helper_args=helper[1], fallback=helper[2])
    else:
        result = shell.privileged("wp", helper_args=args, fallback=["wp", *args])
    if result.returncode != 0 and result.returncode != 1:
        raise RuntimeError(f"Health check failed: {result.stderr or result.stdout}")
    output = result.stdout + result.stderr
    return {"returncode": result.returncode, "output": output}


def create_staging(root_path: str, linux_user: str | None = None) -> str:
    """Create a staging environment by cloning the site."""
    public_path = Path(root_path) / "public_html"
    staging_path = Path(root_path).parent / (Path(root_path).name + "-staging")
    staging_public = staging_path / "public_html"
    if staging_public.exists():
        raise RuntimeError("Staging environment already exists")
    shell.privileged(
        "cp-site",
        helper_args=[str(public_path), str(staging_public)],
        fallback=["cp", "-r", str(public_path), str(staging_public)],
    )
    shell.privileged(
        "site-path-fix",
        helper_args=[str(staging_path), linux_user] if linux_user else [str(staging_path)],
        fallback=["chown", "-R", f"{linux_user}:{linux_user}" if linux_user else "www-data:www-data", str(staging_path)],
    )
    return str(staging_path)


def get_staging_status(root_path: str) -> dict:
    """Check if staging environment exists and return its status."""
    staging_path = Path(root_path).parent / (Path(root_path).name + "-staging")
    staging_public = staging_path / "public_html"
    exists = staging_public.exists()
    if exists:
        wp_index = staging_public / "index.php"
        has_wordpress = wp_index.exists()
        return {"exists": True, "path": str(staging_path), "has_wordpress": has_wordpress}
    return {"exists": False, "path": str(staging_path), "has_wordpress": False}


def push_staging_to_production(root_path: str, linux_user: str | None = None):
    """Push staging environment to production by overwriting the production files."""
    staging_path = Path(root_path).parent / (Path(root_path).name + "-staging")
    staging_public = staging_path / "public_html"
    public_path = Path(root_path) / "public_html"
    if not staging_public.exists():
        raise RuntimeError("Staging environment does not exist")
    shell.privileged(
        "rm-site",
        helper_args=[str(public_path)],
        fallback=["rm", "-rf", str(public_path)],
    )
    shell.privileged(
        "cp-site",
        helper_args=[str(staging_public), str(public_path)],
        fallback=["cp", "-r", str(staging_public), str(public_path)],
    )
    shell.privileged(
        "site-path-fix",
        helper_args=[str(public_path), linux_user] if linux_user else [str(public_path)],
        fallback=["chown", "-R", f"{linux_user}:{linux_user}" if linux_user else "www-data:www-data", str(public_path)],
    )
    return {"message": "Staging pushed to production successfully"}
