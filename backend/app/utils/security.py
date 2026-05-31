"""
Security utilities for BPanel.

Provides validation functions for common security checks including IP addresses,
ports, file paths, usernames, domains, and sensitive data masking.
"""

import os
import re
from typing import List, Optional


def validate_ip(ip: str) -> bool:
    """Validate IP address format (IPv4).

    Args:
        ip: The IP address string to validate.

    Returns:
        True if valid IPv4 address, False otherwise.
    """
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    octets = ip.split('.')
    return all(0 <= int(o) <= 255 for o in octets)


def validate_port(port: int) -> bool:
    """Validate port number.

    Args:
        port: The port number to validate.

    Returns:
        True if valid port (1-65535), False otherwise.
    """
    return 1 <= port <= 65535


def validate_path(path: str, allowed_roots: Optional[List[str]] = None) -> bool:
    """Validate path is within allowed directories.

    Prevents path traversal attacks by ensuring the resolved path
    starts with an allowed root directory.

    Args:
        path: The file path to validate.
        allowed_roots: List of allowed root directories. Defaults to common web roots.

    Returns:
        True if path is safe and within allowed directories, False otherwise.
    """
    if allowed_roots is None:
        allowed_roots = ['/www/wwwroot', '/var/www', '/home']

    try:
        abs_path = os.path.abspath(os.path.expanduser(path))
        return any(abs_path.startswith(root) for root in allowed_roots)
    except (OSError, ValueError):
        return False


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive string for safe logging.

    Shows first and last few characters, masks the middle portion.

    Args:
        value: The sensitive value to mask.
        visible_chars: Number of characters to show at start and end.

    Returns:
        Masked string with middle portion replaced by asterisks.
    """
    if not value or len(value) <= visible_chars:
        return '****'
    half = visible_chars // 2
    return value[:half] + '*' * (len(value) - visible_chars) + value[-half:]


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal.

    Removes directory components and special characters.

    Args:
        filename: The filename to sanitize.

    Returns:
        Sanitized filename safe for filesystem operations.
    """
    # Remove directory components
    filename = os.path.basename(filename)
    # Remove special characters, allow alphanumeric, dash, underscore, dot
    return re.sub(r'[^\w\-.]', '_', filename)


def validate_username(username: str) -> bool:
    """Validate Linux username format.

    Follows standard Linux username conventions:
    - Starts with letter or underscore
    - Contains only letters, digits, underscores, and dashes
    - 2-32 characters in length

    Args:
        username: The username to validate.

    Returns:
        True if valid username format, False otherwise.
    """
    pattern = r'^[a-z_][a-z0-9_-]{2,31}$'
    return bool(re.match(pattern, username, re.IGNORECASE))


def validate_domain(domain: str) -> bool:
    """Validate domain name format.

    Args:
        domain: The domain name to validate.

    Returns:
        True if valid domain format, False otherwise.
    """
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.?$'
    return bool(re.match(pattern, domain))


def validate_ssh_command(command: str) -> bool:
    """Validate SSH command for basic safety.

    Args:
        command: The command string to validate.

    Returns:
        True if command appears safe, False otherwise.
    """
    # Block dangerous patterns
    dangerous = [
        r';\s*rm\s', r'&\s*rm\s', r'\|\s*rm\s',
        r'>\s*/etc/', r'>\s*/var/', r'>\s*/root/',
        r'<\s*/etc/passwd',
        r'eval\s*\(', r'exec\s*\(',
    ]
    for pattern in dangerous:
        if re.search(pattern, command, re.IGNORECASE):
            return False
    return True


def sanitize_command(command: str) -> str:
    """Sanitize command to prevent command injection.

    Removes dangerous patterns while preserving the command functionality.

    Args:
        command: The command to sanitize.

    Returns:
        Sanitized command string.

    Raises:
        ValueError: If command contains dangerous patterns.
    """
    dangerous_patterns = [
        r';\s*rm\s', r';\s*del\s', r'&\s*rm\s', r'\|\s*rm\s',
        r';\s*cat\s', r'&\s*cat\s', r'\|\s*cat\s',
        r';\s*wget\s', r';\s*curl\s',
        r';\s*nc\s', r'&\s*nc\s', r'\|\s*nc\s',
        r';\s*bash\s', r'&\s*bash\s', r'\|\s*bash\s',
        r';\s*sh\s', r'&\s*sh\s', r'\|\s*sh\s',
        r'>\s*/etc/', r'>\s*/var/', r'>\s*/root/',
        r'<\s*/etc/passwd',
        r';\s*chmod\s+0', r';\s*chmod\s+7',
        r';\s*useradd', r';\s*adduser',
        r'eval\s*\(', r'exec\s*\(',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            raise ValueError("Command contains dangerous patterns")

    return command


def validate_cron_expression(expression: str) -> bool:
    """Validate cron expression format.

    Args:
        expression: The cron expression to validate.

    Returns:
        True if valid cron expression, False otherwise.
    """
    parts = expression.split()
    if len(parts) != 5:
        return False
    # Basic format check (each part should be valid cron syntax)
    for part in parts:
        if not re.match(r'^(\*|[\d,\-/]+)$', part):
            return False
    return True
