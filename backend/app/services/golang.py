"""
Go service for managing Go version, modules, and process management.
"""

import json
import os
import re
from typing import Any, Optional

from app.services.shell import shell


def get_go_version() -> dict:
    """Get the currently active Go version."""
    try:
        result = shell.run(["go", "version"])
        version_output = result.stdout.strip()
        # Parse "go version go1.21.0 linux/amd64"
        match = re.search(r"go(\d+\.\d+\.\d+)", version_output)
        if match:
            version = match.group(1)
            return {"version": version, "installed": True, "raw": version_output}
        return {"version": None, "installed": True, "raw": version_output}
    except (RuntimeError, FileNotFoundError):
        return {"version": None, "installed": False}


def list_go_versions() -> dict:
    """List available Go versions from official sources."""
    # Common stable Go versions (can be extended with dynamic fetching)
    stable_versions = [
        "1.24.0", "1.23.0", "1.22.0", "1.21.0", "1.20.0",
        "1.19.0", "1.18.0", "1.17.0", "1.16.0", "1.15.0",
    ]

    installed_version = get_go_version().get("version")

    versions = []
    for version in stable_versions:
        versions.append({
            "version": version,
            "installed": version == installed_version,
            "current": version == installed_version,
        })

    return {"versions": versions}


def install_go_version(version: str) -> dict:
    """Install a specific Go version using the official Go installer."""
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        raise ValueError(f"Invalid Go version format: {version}")

    try:
        # Get system architecture
        arch_result = shell.run(["uname", "-m"])
        arch = arch_result.stdout.strip()
        arch_mapping = {
            "x86_64": "amd64",
            "aarch64": "arm64",
            "armv7l": "armv6l",
        }
        arch = arch_mapping.get(arch, arch)

        # Get OS
        os_result = shell.run(["uname", "-s"])
        os_name = os_result.stdout.strip().lower()
        os_mapping = {"linux": "linux", "darwin": "darwin", "freebsd": "freebsd"}
        os_name = os_mapping.get(os_name, os_name)

        # Download URL
        download_url = f"https://go.dev/dl/go{version}.{os_name}-{arch}.tar.gz"
        install_dir = f"/usr/local/go{version}"
        tar_path = f"/tmp/go{version}.tar.gz"

        # Download Go
        wget_result = shell.run(["wget", "-O", tar_path, download_url])
        if wget_result.returncode != 0:
            raise RuntimeError(f"Failed to download Go {version}: {wget_result.stderr}")

        # Extract Go
        extract_result = shell.run(["tar", "-C", "/usr/local", "-xzf", tar_path])
        if extract_result.returncode != 0:
            raise RuntimeError(f"Failed to extract Go {version}: {extract_result.stderr}")

        # Cleanup
        shell.run(["rm", "-f", tar_path])

        # Update PATH by creating a profile script
        profile_script = f"/etc/profile.d/golang{version.replace('.', '')}.sh"
        profile_content = f"""export GOROOT={install_dir}
export PATH=$PATH:{install_dir}/bin
"""
        with open(profile_script, "w") as f:
            f.write(profile_content)

        return {
            "version": version,
            "success": True,
            "install_dir": install_dir,
            "message": f"Go {version} installed successfully to {install_dir}",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to install Go {version}: {exc}") from exc


def get_go_modules(path: str) -> list:
    """List Go modules in a project."""
    # Validate path
    if not path:
        raise ValueError("Path is required")

    try:
        result = shell.run(["go", "list", "-m", "all"], cwd=path)
        modules = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("main"):
                continue
            # Parse module line: module@version
            parts = line.split()
            if len(parts) >= 1:
                module = parts[0]
                version = parts[1] if len(parts) > 1 else ""
                modules.append({
                    "name": module,
                    "version": version,
                })
        return modules
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to list Go modules: {exc}") from exc


def build_go_project(path: str, output: str = "") -> dict:
    """Build a Go project."""
    if not path:
        raise ValueError("Path is required")

    try:
        cmd = ["go", "build"]
        if output:
            cmd.extend(["-o", output])
        cmd.append(".")

        result = shell.run(cmd, cwd=path)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to build Go project: {result.stderr}")

        return {
            "success": True,
            "path": path,
            "output": output,
            "message": "Go project built successfully",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to build Go project: {exc}") from exc


def run_go_project(path: str, args: list = None) -> dict:
    """Run a Go application."""
    if not path:
        raise ValueError("Path is required")

    args = args or []

    try:
        cmd = ["go", "run", "."] + args
        result = shell.run(cmd, cwd=path)
        return {
            "success": result.returncode == 0,
            "path": path,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else "",
            "returncode": result.returncode,
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to run Go project: {exc}") from exc


def get_go_env(path: str = "") -> dict:
    """Get Go environment for a project or global environment."""
    try:
        cmd = ["go", "env", "-json"]
        result = shell.run(cmd, cwd=path if path else None)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get Go environment: {result.stderr}")

        try:
            env = json.loads(result.stdout)
            return {"env": env}
        except json.JSONDecodeError:
            return {"env": {}, "raw": result.stdout}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to get Go environment: {exc}") from exc


def test_go_project(path: str) -> dict:
    """Run Go tests in a project."""
    if not path:
        raise ValueError("Path is required")

    try:
        result = shell.run(["go", "test", "-v", "./..."], cwd=path)
        return {
            "success": result.returncode == 0,
            "path": path,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode,
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to run Go tests: {exc}") from exc


def setup_golang_service(website_id: int) -> dict:
    """Setup Go web server with systemd for a website.

    Args:
        website_id: The website ID to setup Go service for.

    Returns:
        Dictionary with setup result.

    Raises:
        ValueError: If website not found or paths are invalid.
    """
    import re
    from app.core.database import get_db
    from app.models.entities import Website

    # Allowed root directories for security
    ALLOWED_ROOTS = ['/www/wwwroot', '/var/www', '/home']

    def is_safe_path(path: str) -> bool:
        """Validate path is within allowed directories."""
        try:
            abs_path = os.path.abspath(path)
            return any(abs_path.startswith(root) for root in ALLOWED_ROOTS)
        except (OSError, ValueError):
            return False

    db = next(get_db())
    try:
        website = db.query(Website).filter(Website.id == website_id).first()
        if not website:
            raise ValueError(f"Website with ID {website_id} not found")

        document_root = website.root_path

        # Validate document_root is within allowed directories
        if not is_safe_path(document_root):
            raise ValueError("Document root path outside allowed directory")

        # Find Go entry point
        main_files = [
            f"{document_root}/main.go",
            f"{document_root}/cmd/server/main.go",
            f"{document_root}/cmd/main.go",
        ]

        main_path = None
        for fp in main_files:
            if shell.run(["test", "-f", fp], check=False).returncode == 0:
                main_path = fp
                break

        if not main_path:
            raise ValueError(f"No main.go found in {document_root}")

        # Validate main_path is within allowed directories
        if not is_safe_path(main_path):
            raise ValueError("Main file path outside allowed directory")

        # Sanitize service name and domain
        def sanitize_service_name(name: str) -> str:
            return re.sub(r"[^a-zA-Z0-9]", "_", name.lower())

        def sanitize_unit_value(value: str) -> str:
            """Remove control characters and newlines for systemd unit files."""
            return re.sub(r'[\r\n\t]', '_', value).strip()

        service_name = f"bpanel-go-{sanitize_service_name(website.domain)}"
        service_file = f"/etc/systemd/system/{service_name}.service"

        # Get port from website config or use default
        port = 8080

        # Sanitize values for safe inclusion in systemd unit
        safe_description = sanitize_unit_value(f"Go Application for {website.domain}")
        safe_user = sanitize_unit_value(website.linux_user)
        safe_cwd = sanitize_unit_value(document_root)
        safe_main = sanitize_unit_value(main_path)
        safe_out_log = sanitize_unit_value(f"{document_root}/logs/go-out.log")
        safe_err_log = sanitize_unit_value(f"{document_root}/logs/go-error.log")

        unit_content = f"""[Unit]
Description={safe_description}
After=network.target

[Service]
Type=simple
User={safe_user}
WorkingDirectory={safe_cwd}
ExecStart=/usr/local/go/bin/go run {safe_main}
Restart=always
RestartSec=5
StandardOutput=append:{safe_out_log}
StandardError=append:{safe_err_log}
Environment="PORT={port}"

[Install]
WantedBy=multi-user.target
"""

        # Create logs directory
        shell.run(["mkdir", "-p", f"{document_root}/logs"])
        shell.run(["chown", "-R", website.linux_user, f"{document_root}/logs"])

        # Write service file
        with open(service_file, "w") as f:
            f.write(unit_content)

        # Reload systemd and enable service
        shell.run(["systemctl", "daemon-reload"])
        shell.run(["systemctl", "enable", service_name])
        shell.run(["systemctl", "start", service_name])

        return {
            "website_id": website_id,
            "domain": website.domain,
            "service_name": service_name,
            "service_file": service_file,
            "main_path": main_path,
            "port": port,
            "success": True,
            "message": f"Go service '{service_name}' setup for {website.domain}",
        }
    except ValueError:
        raise
    finally:
        db.close()


def list_go_processes() -> dict:
    """List running Go processes."""
    try:
        result = shell.run(["ps", "aux"])
        processes = []
        for line in result.stdout.splitlines():
            if "go run" in line or "go-build" in line or ".go:" in line:
                parts = line.split()
                if len(parts) >= 11:
                    user = parts[0]
                    pid = parts[1]
                    cpu = parts[2]
                    mem = parts[3]
                    # Find the command part
                    cmd_idx = next((i for i, p in enumerate(parts) if p.endswith(".go") or "go run" in p), -1)
                    if cmd_idx > 0:
                        cmd = " ".join(parts[cmd_idx:cmd_idx+5])
                        processes.append({
                            "user": user,
                            "pid": pid,
                            "cpu": cpu,
                            "memory": mem,
                            "command": cmd,
                        })
        return {"processes": processes}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to list Go processes: {exc}") from exc


def restart_go_service(name: str) -> dict:
    """Restart a Go systemd service."""
    try:
        result = shell.run(["systemctl", "restart", name])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to restart service '{name}': {result.stderr}")
        return {"name": name, "success": True, "message": f"Service '{name}' restarted successfully"}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to restart Go service: {exc}") from exc


def stop_go_service(name: str) -> dict:
    """Stop a Go systemd service."""
    try:
        result = shell.run(["systemctl", "stop", name])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to stop service '{name}': {result.stderr}")
        return {"name": name, "success": True, "message": f"Service '{name}' stopped successfully"}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to stop Go service: {exc}") from exc


def get_go_logs(name: str, lines: int = 100) -> dict:
    """Get logs for a Go systemd service."""
    try:
        result = shell.run(["journalctl", "-u", name, "-n", str(lines), "--no-pager"])
        return {
            "name": name,
            "lines": lines,
            "logs": result.stdout,
            "error_logs": result.stderr,
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to get Go logs: {exc}") from exc


def get_go_service_status(name: str) -> dict:
    """Get status of a Go systemd service."""
    try:
        result = shell.run(["systemctl", "status", name])
        # Parse status output
        is_active = "active (running)" in result.stdout
        return {
            "name": name,
            "active": is_active,
            "status": result.stdout,
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to get service status: {exc}") from exc
