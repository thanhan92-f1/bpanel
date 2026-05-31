"""
FTP service for managing FTP accounts using vsftpd.
"""

import hashlib
import os
import random
import re
import string
from pathlib import Path
from typing import List, Optional

from app.services.shell import shell


LINUX_USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{2,31}$")
FTP_HOME_ROOT = Path("/home/www-data/ftp")
RESERVED_LINUX_USERS = {
    "root", "daemon", "bin", "sys", "sync", "games", "man", "lp", "mail",
    "news", "uucp", "proxy", "www-data", "backup", "list", "irc", "_apt",
    "nobody", "bpanel", "bpanel-sites", "mysql", "redis", "nginx",
}


def validate_ftp_username(username: str) -> str:
    """Validate that a username is safe for FTP use."""
    if not LINUX_USER_RE.fullmatch(username or "") or username in RESERVED_LINUX_USERS:
        raise ValueError("Invalid FTP username. Must be 3-32 lowercase letters, numbers, underscores, or hyphens.")
    return username


def generate_password(length: int = 16) -> str:
    """Generate a random secure password."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def hash_ftp_password(password: str) -> str:
    """Create a password hash for FTP storage (using SHA-256 with salt)."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + key.hex()


def ftp_home_dir(username: str) -> Path:
    """Get the home directory path for an FTP user."""
    return FTP_HOME_ROOT / username


def create_ftp_user(username: str, password: str, home_dir: Optional[str] = None) -> dict:
    """Create an FTP user for vsftpd."""
    username = validate_ftp_username(username)
    if not username.startswith("ftp_"):
        username = f"ftp_{username}"

    home_path = Path(home_dir) if home_dir else ftp_home_dir(username)

    # Create home directory
    shell.privileged(
        "ftp-home-create",
        helper_args=[str(home_path)],
        fallback=["mkdir", "-p", str(home_path)],
    )

    # Create system user
    try:
        shell.privileged(
            "ftp-user-create",
            helper_args=[username, str(home_path)],
            fallback=[
                "useradd", "-M", "-d", str(home_path),
                "-s", "/usr/sbin/nologin", "-p", "*", username,
            ],
        )
    except RuntimeError:
        pass

    # Set FTP password
    passwd_input = f"{username}:{password}"
    shell.run(["chpasswd"], input=passwd_input, check=True)

    # Set permissions
    shell.privileged(
        "ftp-home-perms",
        helper_args=[str(home_path), username],
        fallback=["chown", "-R", f"{username}:{username}", str(home_path)],
    )

    return {
        "username": username,
        "home_directory": str(home_path),
        "password_hash": hash_ftp_password(password),
    }


def delete_ftp_user(username: str) -> None:
    """Delete an FTP user."""
    username = validate_ftp_username(username)
    if not username.startswith("ftp_"):
        username = f"ftp_{username}"

    home_path = ftp_home_dir(username)

    shell.privileged(
        "ftp-user-delete",
        helper_args=[username],
        fallback=["userdel", "-r", username],
        check=False,
    )

    shell.privileged(
        "ftp-home-delete",
        helper_args=[str(home_path)],
        fallback=["rm", "-rf", str(home_path)],
        check=False,
    )


def list_ftp_users() -> List[str]:
    """List all FTP users on the system."""
    result = shell.privileged(
        "ftp-user-list",
        helper_args=[],
        fallback=["getent", "passwd"],
        check=False,
    )

    if result.returncode != 0:
        return []

    ftp_users = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split(":")
        if len(parts) >= 7:
            uname = parts[0]
            ushell = parts[6]
            if uname.startswith("ftp_") or ushell in ("/usr/sbin/nologin", "/sbin/nologin", "/bin/false"):
                if uname not in RESERVED_LINUX_USERS:
                    ftp_users.append(uname)

    return sorted(ftp_users)


def change_ftp_password(username: str, new_password: str) -> None:
    """Change the password for an FTP user."""
    username = validate_ftp_username(username)
    if not username.startswith("ftp_"):
        username = f"ftp_{username}"

    passwd_input = f"{username}:{new_password}"
    shell.run(["chpasswd"], input=passwd_input, check=True)


def get_ftp_user_info(username: str) -> Optional[dict]:
    """Get detailed information about an FTP user."""
    username = validate_ftp_username(username)
    if not username.startswith("ftp_"):
        username = f"ftp_{username}"

    result = shell.privileged(
        "ftp-user-info",
        helper_args=[username],
        fallback=["getent", "passwd", username],
        check=False,
    )

    if result.returncode != 0:
        return None

    parts = result.stdout.strip().split(":")
    if len(parts) < 7:
        return None

    home_dir = parts[5]
    home_path = Path(home_dir)

    return {
        "username": username,
        "home_directory": home_dir,
        "exists": home_path.exists(),
    }


def configure_vsftpd() -> dict:
    """Ensure vsftpd is installed and properly configured."""
    shell.privileged(
        "apt-install",
        helper_args=["vsftpd"],
        fallback=["apt-get", "install", "-y", "vsftpd"],
        check=False,
    )

    shell.privileged(
        "ftp-root-create",
        helper_args=[str(FTP_HOME_ROOT)],
        fallback=["mkdir", "-p", str(FTP_HOME_ROOT)],
    )

    return {"status": "configured", "config_path": "/etc/vsftpd.conf"}


def restart_ftp_service() -> dict:
    """Restart the vsftpd service."""
    shell.privileged(
        "ftp-service-restart",
        helper_args=[],
        fallback=["systemctl", "restart", "vsftpd"],
        check=False,
    )

    return {"status": "restarted", "service": "vsftpd"}


def check_ftp_service_status() -> dict:
    """Check if vsftpd service is running."""
    result = shell.privileged(
        "ftp-service-status",
        helper_args=[],
        fallback=["systemctl", "is-active", "vsftpd"],
        check=False,
    )

    is_active = result.stdout.strip() == "active"

    return {
        "service": "vsftpd",
        "active": is_active,
        "status": "running" if is_active else "stopped",
    }
