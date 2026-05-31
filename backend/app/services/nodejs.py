"""
Node.js service for managing Node.js, npm, and PM2 process manager.
"""

import json
import re
from typing import Any, Optional

from app.services.shell import shell


def get_node_version() -> dict:
    """Get the currently active Node.js version."""
    try:
        result = shell.run(["node", "--version"])
        version = result.stdout.strip().lstrip("v")
        return {"version": version, "installed": True}
    except (RuntimeError, FileNotFoundError):
        return {"version": None, "installed": False}


def get_npm_version() -> dict:
    """Get the npm version."""
    try:
        result = shell.run(["npm", "--version"])
        return {"version": result.stdout.strip(), "installed": True}
    except (RuntimeError, FileNotFoundError):
        return {"version": None, "installed": False}


def list_node_versions() -> dict:
    """List all available Node.js versions via nvm."""
    try:
        result = shell.run(["nvm", "list", "available"])
        versions = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("NVM"):
                continue
            match = re.match(r"^(?:\->\s*)?v?(\d+\.\d+\.\d+)", line)
            if match:
                version = match.group(1)
                lts = ""
                if "LTS" in line:
                    lts_match = re.search(r"LTS:\s*(\w+)", line)
                    if lts_match:
                        lts = lts_match.group(1)
                versions.append({"version": version, "lts": lts, "current": "->" in line})

        installed_result = shell.run(["nvm", "list"])
        installed = set()
        for line in installed_result.stdout.splitlines():
            line = line.strip()
            match = re.match(r"^(?:\->\s*)?v?(\d+\.\d+\.\d+)", line)
            if match:
                installed.add(match.group(1))

        for v in versions:
            v["installed"] = v["version"] in installed

        return {"versions": versions}
    except (RuntimeError, FileNotFoundError):
        return {"versions": []}


def install_node_version(version: str) -> dict:
    """Install a specific Node.js version via nvm."""
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        raise ValueError(f"Invalid Node.js version format: {version}")

    try:
        result = shell.run(["nvm", "install", version])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to install Node.js {version}: {result.stderr}")

        return {
            "version": version,
            "success": True,
            "message": f"Node.js {version} installed successfully",
        }
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to install Node.js {version}: {exc}") from exc


def list_pm2_processes() -> dict:
    """List all PM2 processes."""
    try:
        result = shell.run(["pm2", "list", "--format=json"])
        if result.returncode != 0:
            result = shell.run(["pm2", "list"])

        try:
            processes = json.loads(result.stdout)
            return {"processes": processes}
        except json.JSONDecodeError:
            processes = _parse_pm2_list_text(result.stdout)
            return {"processes": processes}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to list PM2 processes: {exc}") from exc


def _parse_pm2_list_text(output: str) -> list:
    """Parse PM2 list text output into a list of process dictionaries."""
    processes = []
    lines = output.splitlines()
    for line in lines:
        line = line.strip()
        if "│" in line and not line.startswith("┌") and not line.startswith("─"):
            parts = [p.strip() for p in line.split("│")]
            parts = [p for p in parts if p]
            if len(parts) >= 6:
                name = parts[1] if len(parts) > 1 else ""
                status = parts[2] if len(parts) > 2 else ""
                cpu = parts[3] if len(parts) > 3 else ""
                memory = parts[4] if len(parts) > 4 else ""
                restarts = parts[6] if len(parts) > 6 else "0"
                if name and name != "Name":
                    processes.append({
                        "name": name,
                        "status": status.lower(),
                        "cpu": cpu,
                        "memory": memory,
                        "restarts": int(restarts) if restarts.isdigit() else 0,
                        "pm_id": len(processes),
                    })
    return processes


def get_pm2_process_info(name: str) -> dict:
    """Get detailed information about a specific PM2 process."""
    try:
        result = shell.run(["pm2", "show", name])
        if result.returncode != 0:
            raise ValueError(f"Process '{name}' not found")

        info = {"name": name}
        for line in result.stdout.splitlines():
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                if "status" in key:
                    info["status"] = value.lower()
                elif "restarts" in key:
                    info["restarts"] = int(value) if value.isdigit() else 0
                elif "uptime" in key:
                    info["uptime"] = value
                elif "cpu" in key:
                    info["cpu"] = value
                elif "memory" in key:
                    info["memory"] = value
                elif "pid" in key:
                    info["pid"] = value
        return info
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to get PM2 process info: {exc}") from exc


def restart_pm2_process(name: str) -> dict:
    """Restart a PM2 process."""
    try:
        result = shell.run(["pm2", "restart", name])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to restart process '{name}': {result.stderr}")
        return {"name": name, "success": True, "message": f"Process '{name}' restarted successfully"}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to restart PM2 process: {exc}") from exc


def stop_pm2_process(name: str) -> dict:
    """Stop a PM2 process."""
    try:
        result = shell.run(["pm2", "stop", name])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to stop process '{name}': {result.stderr}")
        return {"name": name, "success": True, "message": f"Process '{name}' stopped successfully"}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to stop PM2 process: {exc}") from exc


def delete_pm2_process(name: str) -> dict:
    """Delete a PM2 process."""
    try:
        shell.run(["pm2", "stop", name])
        result = shell.run(["pm2", "delete", name])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to delete process '{name}': {result.stderr}")
        return {"name": name, "success": True, "message": f"Process '{name}' deleted successfully"}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to delete PM2 process: {exc}") from exc


def get_pm2_logs(name: str, lines: int = 100) -> dict:
    """Get PM2 logs for a specific process."""
    try:
        result = shell.run(["pm2", "logs", name, "--nostream", "--lines", str(lines)])
        return {"name": name, "lines": lines, "logs": result.stdout, "error_logs": result.stderr}
    except (RuntimeError, FileNotFoundError) as exc:
        raise RuntimeError(f"Failed to get PM2 logs: {exc}") from exc


def setup_pm2_process(website_id: int, path: str) -> dict:
    """Setup PM2 for a website application."""
    import re
    from app.core.database import get_db
    from app.models.entities import Website

    # Sanitize domain for PM2 process name (alphanumeric, dash, dot only)
    def sanitize_pm2_name(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9._-]", "_", name)

    # Validate path is safe (no command injection)
    def is_safe_path(p: str) -> bool:
        return bool(re.match(r"^/[a-zA-Z0-9/_.-]+$", p))

    db = next(get_db())
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise ValueError(f"Website with ID {website_id} not found")

    document_root = website.root_path
    if not is_safe_path(document_root):
        raise ValueError("Invalid document root path")
    package_json_path = f"{document_root}/package.json"
    server_js_path = f"{document_root}/server.js"
    app_js_path = f"{document_root}/app.js"
    index_js_path = f"{document_root}/index.js"

    script_path = None
    if shell.run(["test", "-f", package_json_path], check=False).returncode == 0:
        script_path = f"{document_root}/node_modules/.bin/npm start"
    elif shell.run(["test", "-f", server_js_path], check=False).returncode == 0:
        script_path = f"{document_root}/server.js"
    elif shell.run(["test", "-f", app_js_path], check=False).returncode == 0:
        script_path = f"{document_root}/app.js"
    elif shell.run(["test", "-f", index_js_path], check=False).returncode == 0:
        script_path = f"{document_root}/index.js"
    else:
        raise ValueError(f"No Node.js entry point found in {document_root}")

    # Validate script_path is within document_root
    if not script_path.startswith(document_root):
        raise ValueError("Script path must be within document root")

    # Sanitize values for safe inclusion in JS config
    pm2_name = sanitize_pm2_name(website.domain)
    safe_script = script_path.replace("'", "\\'")
    safe_cwd = document_root.replace("'", "\\'")
    safe_domain = website.domain.replace("'", "\\'")
    safe_err_log = f"{document_root}/logs/pm2-error.log".replace("'", "\\'")
    safe_out_log = f"{document_root}/logs/pm2-out.log".replace("'", "\\'")

    ecosystem_content = f"""module.exports = {{
  apps: [{{
    name: '{pm2_name}',
    script: '{safe_script}',
    cwd: '{safe_cwd}',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {{
      NODE_ENV: 'production',
      PORT: 3000
    }},
    error_file: '{safe_err_log}',
    out_file: '{safe_out_log}',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true
  }}]
}};
"""
    ecosystem_path = f"{document_root}/ecosystem.config.js"
    shell.run(["mkdir", "-p", f"{document_root}/logs"])

    with open(ecosystem_path, "w") as f:
        f.write(ecosystem_content)

    shell.run(["chown", "-R", website.linux_user, document_root])
    start_result = shell.run(["pm2", "start", ecosystem_path])
    if start_result.returncode != 0:
        raise RuntimeError(f"Failed to start PM2 process: {start_result.stderr}")

    shell.run(["pm2", "save"])

    return {
        "website_id": website_id,
        "domain": website.domain,
        "ecosystem_path": ecosystem_path,
        "script": script_path,
        "success": True,
        "message": f"PM2 process setup for {website.domain}",
    }
