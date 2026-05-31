"""
Python Project service for managing Python, virtual environments, and packages.
"""

import json
import re
from typing import Any, Optional

from app.services.shell import shell


def get_python_version() -> dict:
    """Get the default Python version."""
    try:
        result = shell.run(["python3", "--version"])
        version = result.stdout.strip().lstrip("Python")
        return {"version": version, "installed": True}
    except (RuntimeError, FileNotFoundError):
        try:
            result = shell.run(["python", "--version"])
            version = result.stdout.strip().lstrip("Python")
            return {"version": version, "installed": True}
        except (RuntimeError, FileNotFoundError):
            return {"version": None, "installed": False}


def list_python_versions() -> dict:
    """List installed Python versions."""
    versions = []

    # Try pyenv first
    try:
        result = shell.run(["pyenv", "versions", "--json"])
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for v in data.get("installed", []):
                versions.append({"version": v, "source": "pyenv", "installed": True})
            for v in data.get("uninstalled", []):
                versions.append({"version": v, "source": "pyenv", "installed": False})
            return {"versions": versions}
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
        pass

    # Fallback: list python binaries in /usr/bin
    try:
        result = shell.run(["ls", "/usr/bin/python*"])
        for line in result.stdout.splitlines():
            line = line.strip()
            match = re.match(r"python(\d+(?:\.\d+)?)", line)
            if match:
                version = match.group(1)
                versions.append({"version": version, "source": "system", "installed": True})
        return {"versions": versions}
    except (RuntimeError, FileNotFoundError):
        pass

    return {"versions": versions}


def install_python_version(version: str) -> dict:
    """Install a Python version using pyenv."""
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        raise ValueError(f"Invalid Python version format: {version}")

    try:
        result = shell.run(["pyenv", "install", version])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to install Python {version}: {result.stderr}")

        return {
            "version": version,
            "success": True,
            "message": f"Python {version} installed successfully",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to install Python {version}: {exc}") from exc


def create_venv(path: str, python_version: str = "python3") -> dict:
    """Create a virtual environment."""
    import re
    from app.core.database import get_db
    from app.models.entities import VirtualEnvironment

    # Validate path is safe
    if not re.match(r"^/[a-zA-Z0-9/_.-]+$", path):
        raise ValueError("Invalid path format")

    # Create parent directory if needed
    parent_dir = "/".join(path.rsplit("/", 1)[:-1])
    if parent_dir and parent_dir != "/":
        shell.run(["mkdir", "-p", parent_dir])

    # Determine Python executable
    if python_version == "python3":
        python_exec = "python3"
    elif re.match(r"^\d+\.\d+$", python_version):
        python_exec = f"python{python_version}"
    else:
        python_exec = python_version

    try:
        result = shell.run([python_exec, "-m", "venv", path])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create venv: {result.stderr}")

        # Determine Python version in venv
        venv_python = f"{path}/bin/python3"
        ver_result = shell.run([venv_python, "--version"])
        venv_version = ver_result.stdout.strip().lstrip("Python")

        # Save to database
        db = next(get_db())
        venv = VirtualEnvironment(
            path=path,
            python_version=venv_version,
            python_executable=venv_python,
        )
        db.add(venv)
        db.commit()
        db.refresh(venv)

        return {
            "id": venv.id,
            "path": path,
            "python_version": venv_version,
            "success": True,
            "message": f"Virtual environment created at {path}",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to create virtual environment: {exc}") from exc


def get_venv_info(venv_id: int) -> dict:
    """Get virtual environment info by ID."""
    from app.core.database import get_db
    from app.models.entities import VirtualEnvironment

    db = next(get_db())
    venv = db.query(VirtualEnvironment).filter(VirtualEnvironment.id == venv_id).first()
    if not venv:
        raise ValueError(f"Virtual environment with ID {venv_id} not found")

    return {
        "id": venv.id,
        "path": venv.path,
        "python_version": venv.python_version,
        "python_executable": venv.python_executable,
    }


def list_venv_packages(venv_path: str) -> list:
    """List installed packages in virtual environment."""
    pip_path = f"{venv_path}/bin/pip"

    try:
        result = shell.run([pip_path, "list", "--format=json"])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to list packages: {result.stderr}")

        packages = json.loads(result.stdout)
        return packages
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to list venv packages: {exc}") from exc


def install_venv_package(venv_path: str, package: str) -> dict:
    """Install a package in virtual environment."""
    pip_path = f"{venv_path}/bin/pip"

    try:
        result = shell.run([pip_path, "install", package])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to install package: {result.stderr}")

        return {
            "package": package,
            "venv_path": venv_path,
            "success": True,
            "message": f"Package '{package}' installed successfully",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to install package: {exc}") from exc


def uninstall_venv_package(venv_path: str, package: str) -> dict:
    """Uninstall a package from virtual environment."""
    pip_path = f"{venv_path}/bin/pip"

    try:
        result = shell.run([pip_path, "uninstall", "-y", package])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to uninstall package: {result.stderr}")

        return {
            "package": package,
            "venv_path": venv_path,
            "success": True,
            "message": f"Package '{package}' uninstalled successfully",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to uninstall package: {exc}") from exc


def run_python_script(venv_path: str, script: str, args: list = None) -> dict:
    """Run a Python script in virtual environment."""
    if args is None:
        args = []

    python_path = f"{venv_path}/bin/python"

    # Validate script path is safe
    if not script.startswith("/"):
        raise ValueError("Script path must be absolute")

    try:
        cmd = [python_path, script] + list(args)
        result = shell.run(cmd)
        return {
            "script": script,
            "venv_path": venv_path,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to run Python script: {exc}") from exc


def test_python_project(path: str) -> dict:
    """Run pytest on a Python project."""
    pytest_path = f"{path}/venv/bin/pytest"

    # Fallback to system pytest if venv pytest doesn't exist
    try:
        shell.run(["test", "-f", pytest_path])
    except (RuntimeError, FileNotFoundError):
        pytest_path = "pytest"

    try:
        result = shell.run([pytest_path, "-v", "--tb=short", path])
        return {
            "path": path,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to run tests: {exc}") from exc


def setup_python_service(website_id: int, venv_path: str, script: str = None) -> dict:
    """Setup Python app with systemd service."""
    import re
    from app.core.database import get_db
    from app.models.entities import Website

    def sanitize_service_name(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]", "_", name)

    def is_safe_path(p: str) -> bool:
        return bool(re.match(r"^/[a-zA-Z0-9/_.-]+$", p))

    db = next(get_db())
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise ValueError(f"Website with ID {website_id} not found")

    document_root = website.root_path
    if not is_safe_path(document_root):
        raise ValueError("Invalid document root path")

    # Determine entry script
    if script:
        script_path = f"{document_root}/{script}"
    else:
        # Look for common Python entry points
        for name in ["app.py", "main.py", "server.py", "run.py"]:
            candidate = f"{document_root}/{name}"
            if shell.run(["test", "-f", candidate], check=False).returncode == 0:
                script_path = candidate
                break
        else:
            raise ValueError(f"No Python entry point found in {document_root}")

    # Validate script path
    if not script_path.startswith(document_root):
        raise ValueError("Script path must be within document root")

    service_name = f"bpanel-{sanitize_service_name(website.domain)}"
    python_path = f"{venv_path}/bin/python"

    service_content = f"""[Unit]
Description=BPanel Python Application - {website.domain}
After=network.target

[Service]
Type=simple
User={website.linux_user}
WorkingDirectory={document_root}
ExecStart={python_path} {script_path}
Restart=always
RestartSec=5
Environment="PATH={venv_path}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
"""

    service_path = f"/etc/systemd/system/{service_name}.service"
    shell.run(["bash", "-c", f"echo '$SERVICE_CONTENT' > {service_path}".replace("$SERVICE_CONTENT", service_content.replace("'", "'\"'\"'"))])

    shell.run(["systemctl", "daemon-reload"])
    shell.run(["systemctl", "enable", service_name])
    shell.run(["systemctl", "start", service_name])

    return {
        "website_id": website_id,
        "domain": website.domain,
        "service_name": service_name,
        "script_path": script_path,
        "venv_path": venv_path,
        "success": True,
        "message": f"Systemd service '{service_name}' created for {website.domain}",
    }


def get_python_processes() -> dict:
    """List running Python processes."""
    try:
        result = shell.run(["ps", "aux"])
        processes = []
        for line in result.stdout.splitlines():
            if "python" in line.lower() and "grep" not in line:
                parts = line.split()
                if len(parts) >= 11:
                    processes.append({
                        "user": parts[0],
                        "pid": parts[1],
                        "cpu": parts[2],
                        "mem": parts[3],
                        "command": " ".join(parts[10:])[:100],
                    })
        return {"processes": processes}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to list Python processes: {exc}") from exc


def restart_python_service(name: str) -> dict:
    """Restart a Python systemd service."""
    try:
        result = shell.run(["systemctl", "restart", name])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to restart service '{name}': {result.stderr}")

        return {
            "name": name,
            "success": True,
            "message": f"Service '{name}' restarted successfully",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to restart service: {exc}") from exc


def stop_python_service(name: str) -> dict:
    """Stop a Python systemd service."""
    try:
        result = shell.run(["systemctl", "stop", name])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to stop service '{name}': {result.stderr}")

        return {
            "name": name,
            "success": True,
            "message": f"Service '{name}' stopped successfully",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to stop service: {exc}") from exc


def get_python_logs(name: str, lines: int = 100) -> dict:
    """Get logs for a Python systemd service."""
    try:
        result = shell.run(["journalctl", "-u", name, "-n", str(lines), "--no-pager"])
        return {
            "name": name,
            "lines": lines,
            "logs": result.stdout,
            "error_logs": "",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to get service logs: {exc}") from exc


def delete_venv(venv_id: int) -> dict:
    """Delete a virtual environment."""
    from app.core.database import get_db
    from app.models.entities import VirtualEnvironment

    db = next(get_db())
    venv = db.query(VirtualEnvironment).filter(VirtualEnvironment.id == venv_id).first()
    if not venv:
        raise ValueError(f"Virtual environment with ID {venv_id} not found")

    try:
        shell.run(["rm", "-rf", venv.path])
        db.delete(venv)
        db.commit()

        return {
            "id": venv_id,
            "path": venv.path,
            "success": True,
            "message": f"Virtual environment at {venv.path} deleted",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        db.rollback()
        raise RuntimeError(f"Failed to delete virtual environment: {exc}") from exc


def list_venvs() -> list:
    """List all virtual environments from database."""
    from app.core.database import get_db
    from app.models.entities import VirtualEnvironment

    db = next(get_db())
    venvs = db.query(VirtualEnvironment).all()

    return [
        {
            "id": venv.id,
            "path": venv.path,
            "python_version": venv.python_version,
            "python_executable": venv.python_executable,
        }
        for venv in venvs
    ]
