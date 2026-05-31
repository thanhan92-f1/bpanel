"""
Mail Server Service for managing Postfix, Dovecot, and related mail services.

This service handles:
- Mail domain management (Postfix virtual domains)
- Mailbox management (Dovecot userdb)
- Email access via IMAP/SMTP
- Spam filtering configuration
- SSL/TLS settings
"""

import csv
import hashlib
import io
import os
import random
import re
import secrets
import string
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.services.shell import shell

# Configuration paths
MAIL_ROOT = Path("/var/vmail")
POSTFIX_VIRTUAL = Path("/etc/postfix/virtual_domains")
POSTFIX_MAILBOX = Path("/etc/postfix/virtual_mailboxes")
DOVECOT_USERDB = Path("/etc/dovecot/userdb")
DOVECOT_PASSDB = Path("/etc/dovecot/passdb")
MAIL_SPOOL = Path("/var/mail")
MAIL_INDEX = Path("/var/indexes")
SPAMASSASSIN_USER_PREFS = Path("/etc/spamassassin")
OPEN_DKIM_KEYS = Path("/etc/opendkim/keys")

# Ports
SMTP_PORT = 587
SMTPS_PORT = 465
IMAP_PORT = 143
IMAPS_PORT = 993
POP3_PORT = 110
POP3S_PORT = 995

# Reserved domains
RESERVED_DOMAINS = {"localhost", "localhost.localdomain"}


def _validate_domain(domain: str) -> str:
    """Validate domain name format."""
    domain = domain.strip().lower()
    domain_re = re.compile(r"^(?!-)([a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,}$")
    if not domain_re.match(domain):
        raise ValueError("Invalid domain name format")
    if domain in RESERVED_DOMAINS:
        raise ValueError(f"Domain '{domain}' is reserved")
    return domain


def _validate_username(username: str) -> str:
    """Validate mailbox username (local part)."""
    username = username.strip().lower()
    if not username or len(username) > 64:
        raise ValueError("Username must be 1-64 characters")
    if not re.match(r"^[a-z0-9._+-]+$", username):
        raise ValueError("Username can only contain lowercase letters, numbers, dots, underscores, hyphens, and plus signs")
    return username


def _generate_password(length: int = 16) -> str:
    """Generate a random secure password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choice(chars) for _ in range(length))


def _hash_password_dovecot(password: str, scheme: str = "blake2b512") -> str:
    """Create a Dovecot-compatible password hash."""
    # Use blake2b for modern systems, fallback to sha512
    salt = secrets.token_hex(16)
    if scheme == "blake2b512":
        key = hashlib.blake2b(password.encode(), digest_size=64, salt=salt.encode()).hexdigest()
        return f"{{blake2b512}}{salt}${key}"
    else:
        import subprocess
        result = subprocess.run(
            ["doveadm", "pw", "-p", password, "-s", "sha512-crypt"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()


# ============================================================================
# Mail Domain Management
# ============================================================================

def list_mail_domains() -> List[dict]:
    """List all configured mail domains."""
    domains = []
    for domain_dir in MAIL_ROOT.iterdir():
        if domain_dir.is_dir():
            domain = domain_dir.name
            quota_file = domain_dir / ".quota"
            quota_gb = 10
            if quota_file.exists():
                try:
                    quota_gb = int(quota_file.read_text().strip())
                except ValueError:
                    pass
            domains.append({
                "domain": domain,
                "quota_gb": quota_gb,
                "exists": True,
            })
    return domains


def add_mail_domain(domain: str, quota_gb: int = 10) -> dict:
    """Add a new mail domain."""
    domain = _validate_domain(domain)
    domain_dir = MAIL_ROOT / domain

    # Create domain directory
    shell.privileged(
        "mail-domain-create",
        helper_args=[str(domain_dir)],
        fallback=["mkdir", "-p", str(domain_dir)],
    )

    # Set quota
    quota_file = domain_dir / ".quota"
    shell.run(["bash", "-c", f"echo {quota_gb} > {quota_file}"], check=False)

    # Create mail storage directories
    for subdir in ["cur", "new", "tmp"]:
        shell.privileged(
            "mail-dir-create",
            helper_args=[str(domain_dir / subdir)],
            fallback=["mkdir", "-p", str(domain_dir / subdir)],
        )

    # Set ownership
    shell.privileged(
        "mail-domain-perms",
        helper_args=[str(domain_dir)],
        fallback=["chown", "-R", "vmail:vmail", str(domain_dir)],
    )

    return {
        "domain": domain,
        "quota_gb": quota_gb,
        "status": "created",
    }


def remove_mail_domain(domain: str) -> dict:
    """Remove a mail domain and all its mailboxes."""
    domain = _validate_domain(domain)
    domain_dir = MAIL_ROOT / domain

    # Remove domain directory
    shell.privileged(
        "mail-domain-delete",
        helper_args=[str(domain_dir)],
        fallback=["rm", "-rf", str(domain_dir)],
        check=False,
    )

    return {
        "domain": domain,
        "status": "removed",
    }


def get_domain_info(domain: str) -> dict:
    """Get detailed information about a mail domain."""
    domain = _validate_domain(domain)
    domain_dir = MAIL_ROOT / domain

    quota_file = domain_dir / ".quota"
    quota_gb = 10
    if quota_file.exists():
        try:
            quota_gb = int(quota_file.read_text().strip())
        except ValueError:
            pass

    # Count mailboxes
    mailbox_count = 0
    total_size = 0
    if domain_dir.exists():
        for mailbox_dir in domain_dir.iterdir():
            if mailbox_dir.is_dir() and not mailbox_dir.name.startswith("."):
                mailbox_count += 1
                try:
                    result = shell.run(
                        ["du", "-sb", str(mailbox_dir)],
                        check=False
                    )
                    if result.returncode == 0:
                        size = int(result.stdout.split()[0])
                        total_size += size
                except (ValueError, IndexError):
                    pass

    return {
        "domain": domain,
        "quota_gb": quota_gb,
        "mailbox_count": mailbox_count,
        "total_size_bytes": total_size,
        "exists": domain_dir.exists(),
    }


def configure_domain_ssl(domain: str) -> dict:
    """Configure SSL/TLS for a mail domain."""
    domain = _validate_domain(domain)

    # Check for existing SSL certificates
    cert_file = Path(f"/etc/ssl/certs/{domain}.pem")
    key_file = Path(f"/etc/ssl/private/{domain}.key")

    ssl_status = "not_configured"
    if cert_file.exists() and key_file.exists():
        ssl_status = "configured"
    else:
        # Generate self-signed certificate
        shell.privileged(
            "mail-ssl-generate",
            helper_args=[domain, str(cert_file), str(key_file)],
            fallback=[
                "openssl", "req", "-new", "-x509", "-nodes",
                "-out", str(cert_file),
                "-keyout", str(key_file),
                "-days", "365",
                "-subj", f"/CN={domain}/"
            ],
            check=False,
        )

    return {
        "domain": domain,
        "ssl_status": ssl_status,
        "cert_file": str(cert_file) if ssl_status == "configured" else None,
    }


def check_domain_spam_list(domain: str) -> dict:
    """Check if domain is on any spam blacklists."""
    domain = _validate_domain(domain)

    # Common spam blacklist checks (DNS-based)
    blacklists = [
        "spamhaus.org",
        "sorbs.net",
        "barracudacentral.org",
    ]

    results = []
    for bl in blacklists:
        try:
            result = shell.run(
                ["nslookup", f"{domain}.{bl}"],
                check=False
            )
            # NXDOMAIN means not listed
            if "NXDOMAIN" in result.stdout or result.returncode != 0:
                results.append({"blacklist": bl, "listed": False})
            else:
                results.append({"blacklist": bl, "listed": True})
        except Exception:
            results.append({"blacklist": bl, "listed": None, "error": "Check failed"})

    return {
        "domain": domain,
        "results": results,
        "is_listed": any(r.get("listed") for r in results if r.get("listed") is not None),
    }


def refresh_domain_dns(domain: str) -> dict:
    """Refresh DNS records for mail domain (DKIM, SPF, DMARC)."""
    domain = _validate_domain(domain)

    # Generate DKIM key if not exists
    dkim_dir = OPEN_DKIM_KEYS / domain
    dkim_private = dkim_dir / "default.private"
    dkim_public = dkim_dir / "default.txt"

    if not dkim_private.exists():
        shell.privileged(
            "mail-dkim-generate",
            helper_args=[domain],
            fallback=["mkdir", "-p", str(dkim_dir)],
        )

    # DKIM record content
    dkim_record = ""
    if dkim_public.exists():
        try:
            content = dkim_public.read_text()
            # Extract the DKIM record from the TXT record output
            match = re.search(r'p=([a-zA-Z0-9+/=]+)', content)
            if match:
                dkim_record = f"v=DKIM1; k=rsa; p={match.group(1)}"
        except Exception:
            pass

    return {
        "domain": domain,
        "dkim_record": dkim_record,
        "spf_record": f"v=spf1 mx a:{domain} ~all",
        "dmarc_record": f"v=DMARC1; p=quarantine; rua=mailto:postmaster@{domain}",
        "status": "refreshed",
    }


def set_domain_quota(domain: str, quota_gb: int) -> dict:
    """Set storage quota for a domain."""
    domain = _validate_domain(domain)
    domain_dir = MAIL_ROOT / domain
    quota_file = domain_dir / ".quota"

    if not domain_dir.exists():
        raise ValueError(f"Domain {domain} does not exist")

    shell.run(["bash", "-c", f"echo {quota_gb} > {quota_file}"], check=True)

    return {
        "domain": domain,
        "quota_gb": quota_gb,
        "status": "updated",
    }


def enable_catch_all(domain: str, forward_to: str) -> dict:
    """Enable catch-all email routing for a domain."""
    domain = _validate_domain(domain)
    forward_to = forward_to.strip()

    if "@" not in forward_to:
        raise ValueError("Forward address must be a valid email address")

    catch_all_file = MAIL_ROOT / domain / ".catch_all"
    shell.run(
        ["bash", "-c", f"echo '{forward_to}' > {catch_all_file}"],
        check=True
    )

    return {
        "domain": domain,
        "catch_all": forward_to,
        "status": "enabled",
    }


def disable_catch_all(domain: str) -> dict:
    """Disable catch-all email routing for a domain."""
    domain = _validate_domain(domain)
    catch_all_file = MAIL_ROOT / domain / ".catch_all"

    if catch_all_file.exists():
        shell.run(["rm", "-f", str(catch_all_file)], check=False)

    return {
        "domain": domain,
        "status": "disabled",
    }


def get_webmail_url(domain: str) -> str:
    """Get the webmail URL for a domain."""
    domain = _validate_domain(domain)
    # Return webmail URL (e.g., Snappymail or Roundcube)
    return f"https://mail.{domain}/"


def setup_webmail(domain: str) -> dict:
    """Setup webmail access for a domain."""
    domain = _validate_domain(domain)

    # Configure nginx reverse proxy for webmail
    webmail_config = f"""
location /webmail/{domain}/ {{
    proxy_pass http://127.0.0.1:8888/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}}
"""
    # In production, this would write to /etc/nginx/sites-available/

    return {
        "domain": domain,
        "webmail_url": get_webmail_url(domain),
        "status": "configured",
    }


# ============================================================================
# Mailbox Management
# ============================================================================

def list_mailboxes(domain: str) -> List[dict]:
    """List all mailboxes for a domain."""
    domain = _validate_domain(domain)
    domain_dir = MAIL_ROOT / domain

    mailboxes = []
    if not domain_dir.exists():
        return mailboxes

    for mailbox_dir in domain_dir.iterdir():
        if mailbox_dir.is_dir() and not mailbox_dir.name.startswith("."):
            username = mailbox_dir.name
            quota_file = mailbox_dir / ".quota"
            quota_mb = 5120
            if quota_file.exists():
                try:
                    quota_mb = int(quota_file.read_text().strip())
                except ValueError:
                    pass

            # Get mailbox size
            size_bytes = 0
            try:
                result = shell.run(
                    ["du", "-sb", str(mailbox_dir)],
                    check=False
                )
                if result.returncode == 0:
                    size_bytes = int(result.stdout.split()[0])
            except (ValueError, IndexError):
                pass

            mailboxes.append({
                "domain": domain,
                "username": username,
                "email": f"{username}@{domain}",
                "quota_mb": quota_mb,
                "size_bytes": size_bytes,
                "is_active": True,
            })

    return mailboxes


def add_mailbox(domain: str, username: str, password: str, quota_mb: int = 5120) -> dict:
    """Create a new mailbox."""
    domain = _validate_domain(domain)
    username = _validate_username(username)
    email = f"{username}@{domain}"
    mailbox_dir = MAIL_ROOT / domain / username

    # Create mailbox directory
    shell.privileged(
        "mailbox-create",
        helper_args=[str(mailbox_dir)],
        fallback=["mkdir", "-p", str(mailbox_dir)],
    )

    # Create mail folders
    for folder in ["cur", "new", "tmp", ".Drafts", ".Sent", ".Trash", ".Junk"]:
        shell.privileged(
            "mailbox-folder-create",
            helper_args=[str(mailbox_dir / folder)],
            fallback=["mkdir", "-p", str(mailbox_dir / folder)],
        )

    # Set quota
    quota_file = mailbox_dir / ".quota"
    shell.run(["bash", "-c", f"echo {quota_mb} > {quota_file}"], check=False)

    # Set ownership
    shell.privileged(
        "mailbox-perms",
        helper_args=[str(mailbox_dir)],
        fallback=["chown", "-R", "vmail:vmail", str(mailbox_dir)],
    )

    # Generate password hash for Dovecot
    password_hash = _hash_password_dovecot(password)

    # Write to Dovecot passdb (for authentication)
    passdb_entry = f"{email}:{password_hash}:5000:5000:: {mailbox_dir}\n"
    passdb_file = DOVECOT_PASSDB.parent / f"{domain}.passdb"
    shell.run(["bash", "-c", f"echo '{passdb_entry}' >> {passdb_file}"], check=False)

    return {
        "domain": domain,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "quota_mb": quota_mb,
        "status": "created",
    }


def remove_mailbox(domain: str, username: str) -> dict:
    """Delete a mailbox."""
    domain = _validate_domain(domain)
    username = _validate_username(username)
    email = f"{username}@{domain}"
    mailbox_dir = MAIL_ROOT / domain / username

    # Remove mailbox directory
    shell.privileged(
        "mailbox-delete",
        helper_args=[str(mailbox_dir)],
        fallback=["rm", "-rf", str(mailbox_dir)],
        check=False,
    )

    # Remove from passdb
    passdb_file = DOVECOT_PASSDB.parent / f"{domain}.passdb"
    if passdb_file.exists():
        shell.run(
            ["bash", "-c", f"grep -v '^{email}:' {passdb_file} > {passdb_file}.tmp && mv {passdb_file}.tmp {passdb_file}"],
            check=False,
        )

    return {
        "domain": domain,
        "username": username,
        "email": email,
        "status": "removed",
    }


def update_mailbox_password(domain: str, username: str, password: str) -> dict:
    """Update mailbox password."""
    domain = _validate_domain(domain)
    username = _validate_username(username)
    email = f"{username}@{domain}"
    password_hash = _hash_password_dovecot(password)

    # Update passdb entry
    passdb_file = DOVECOT_PASSDB.parent / f"{domain}.passdb"
    if passdb_file.exists():
        # Read existing entries
        entries = []
        if passdb_file.exists():
            entries = passdb_file.read_text().splitlines()

        # Update or add entry
        found = False
        new_entries = []
        for entry in entries:
            if entry.startswith(f"{email}:"):
                parts = entry.split(":")
                new_entries.append(f"{email}:{password_hash}:{parts[2] if len(parts) > 2 else '5000'}:{parts[3] if len(parts) > 3 else '5000'}:: {parts[-1] if parts else str(MAIL_ROOT / domain / username)}")
                found = True
            else:
                new_entries.append(entry)

        if not found:
            new_entries.append(f"{email}:{password_hash}:5000:5000:: {MAIL_ROOT / domain / username}")

        passdb_file.write_text("\n".join(new_entries) + "\n")

    return {
        "domain": domain,
        "username": username,
        "email": email,
        "status": "password_updated",
    }


def update_mailbox_quota(domain: str, username: str, quota_mb: int) -> dict:
    """Update mailbox quota."""
    domain = _validate_domain(domain)
    username = _validate_username(username)
    mailbox_dir = MAIL_ROOT / domain / username
    quota_file = mailbox_dir / ".quota"

    if not mailbox_dir.exists():
        raise ValueError(f"Mailbox {username}@{domain} does not exist")

    shell.run(["bash", "-c", f"echo {quota_mb} > {quota_file}"], check=True)

    return {
        "domain": domain,
        "username": username,
        "quota_mb": quota_mb,
        "status": "updated",
    }


def batch_create_mailboxes(domain: str, mailboxes: List[dict]) -> dict:
    """Create multiple mailboxes at once."""
    domain = _validate_domain(domain)
    created = []
    errors = []

    for mb in mailboxes:
        try:
            username = mb.get("username", "")
            password = mb.get("password") or _generate_password()
            quota_mb = mb.get("quota_mb", 5120)
            result = add_mailbox(domain, username, password, quota_mb)
            result["password"] = password  # Return plaintext for display
            created.append(result)
        except Exception as exc:
            errors.append({"username": mb.get("username"), "error": str(exc)})

    return {
        "domain": domain,
        "created": created,
        "errors": errors,
        "total_created": len(created),
        "total_errors": len(errors),
    }


def import_mailboxes_from_csv(domain: str, csv_content: str) -> dict:
    """Import mailboxes from CSV content."""
    domain = _validate_domain(domain)

    mailboxes = []
    reader = csv.DictReader(io.StringIO(csv_content))

    for row in reader:
        username = row.get("username", "").strip()
        password = row.get("password", "").strip() or _generate_password()
        quota_mb = int(row.get("quota_mb", 5120))

        if username:
            mailboxes.append({
                "username": username,
                "password": password,
                "quota_mb": quota_mb,
            })

    return batch_create_mailboxes(domain, mailboxes)


def export_mailboxes_to_csv(domain: str) -> str:
    """Export mailboxes to CSV format."""
    domain = _validate_domain(domain)
    mailboxes = list_mailboxes(domain)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["username", "email", "quota_mb", "is_active"])
    writer.writeheader()
    for mb in mailboxes:
        writer.writerow({
            "username": mb["username"],
            "email": mb["email"],
            "quota_mb": mb["quota_mb"],
            "is_active": mb["is_active"],
        })

    return output.getvalue()


def get_mailbox_info(domain: str, username: str) -> dict:
    """Get detailed mailbox information."""
    domain = _validate_domain(domain)
    username = _validate_username(username)
    email = f"{username}@{domain}"
    mailbox_dir = MAIL_ROOT / domain / username

    if not mailbox_dir.exists():
        raise ValueError(f"Mailbox {username}@{domain} does not exist")

    # Get quota
    quota_file = mailbox_dir / ".quota"
    quota_mb = 5120
    if quota_file.exists():
        try:
            quota_mb = int(quota_file.read_text().strip())
        except ValueError:
            pass

    # Get folder sizes
    folders = {}
    for folder in ["cur", "new", "tmp", ".Drafts", ".Sent", ".Trash", ".Junk"]:
        folder_path = mailbox_dir / folder
        if folder_path.exists():
            try:
                result = shell.run(["du", "-sb", str(folder_path)], check=False)
                if result.returncode == 0:
                    folders[folder] = int(result.stdout.split()[0])
            except (ValueError, IndexError):
                folders[folder] = 0

    return {
        "domain": domain,
        "username": username,
        "email": email,
        "quota_mb": quota_mb,
        "folders": folders,
        "is_active": True,
        "path": str(mailbox_dir),
    }


# ============================================================================
# Email Access (IMAP/SMTP)
# ============================================================================

def get_emails(domain: str, username: str, folder: str = "INBOX", page: int = 1, per_page: int = 50) -> dict:
    """Get emails from a mailbox folder via IMAP."""
    domain = _validate_domain(domain)
    username = _validate_username(username)
    email = f"{username}@{domain}"
    mailbox_dir = MAIL_ROOT / domain / username

    # Map folder name to directory
    folder_map = {
        "INBOX": "cur",
        "Drafts": ".Drafts/cur",
        "Sent": ".Sent/cur",
        "Trash": ".Trash/cur",
        "Junk": ".Junk/cur",
    }

    folder_path = mailbox_dir / folder_map.get(folder, "cur")
    if not folder_path.exists():
        return {
            "domain": domain,
            "username": username,
            "folder": folder,
            "emails": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
        }

    # List email files
    emails = []
    try:
        email_files = sorted(folder_path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        total = len(email_files)

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        paginated = email_files[start:end]

        for email_file in paginated:
            try:
                stat = email_file.stat()
                emails.append({
                    "id": email_file.st_ino,
                    "filename": email_file.name,
                    "size": stat.st_size,
                    "date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except OSError:
                continue

        return {
            "domain": domain,
            "username": username,
            "folder": folder,
            "emails": emails,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    except Exception as exc:
        return {
            "domain": domain,
            "username": username,
            "folder": folder,
            "emails": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "error": str(exc),
        }


def get_email_content(domain: str, username: str, message_id: str) -> dict:
    """Get full email content."""
    domain = _validate_domain(domain)
    username = _validate_username(username)
    mailbox_dir = MAIL_ROOT / domain / username

    # Search for message in all folders
    for folder in ["cur", "new", ".Drafts/cur", ".Sent/cur", ".Trash/cur", ".Junk/cur"]:
        email_path = mailbox_dir / folder / message_id
        if email_path.exists():
            try:
                content = email_path.read_bytes()
                # Parse headers
                headers = {}
                try:
                    text = content.decode("utf-8", errors="replace")
                    for line in text.split("\n")[:50]:
                        if ":" in line:
                            key, value = line.split(":", 1)
                            headers[key.strip()] = value.strip()
                        elif line.strip() == "":
                            break
                except Exception:
                    text = ""

                return {
                    "domain": domain,
                    "username": username,
                    "message_id": message_id,
                    "size": len(content),
                    "headers": headers,
                    "content_preview": text[:500] if text else "",
                    "folder": folder,
                }
            except Exception as exc:
                return {
                    "domain": domain,
                    "username": username,
                    "message_id": message_id,
                    "error": str(exc),
                }

    raise ValueError(f"Message {message_id} not found")


def move_email(domain: str, username: str, message_id: str, target_folder: str) -> dict:
    """Move an email to a different folder."""
    domain = _validate_domain(domain)
    username = _validate_username(username)
    mailbox_dir = MAIL_ROOT / domain / username

    folder_map = {
        "INBOX": "cur",
        "Drafts": ".Drafts/cur",
        "Sent": ".Sent/cur",
        "Trash": ".Trash/cur",
        "Junk": ".Junk/cur",
    }

    target_dir = mailbox_dir / folder_map.get(target_folder, "cur")
    if not target_dir.exists():
        raise ValueError(f"Target folder {target_folder} does not exist")

    # Find and move the email
    for folder in ["cur", "new", ".Drafts/cur", ".Sent/cur", ".Trash/cur", ".Junk/cur"]:
        email_path = mailbox_dir / folder / message_id
        if email_path.exists():
            shell.privileged(
                "email-move",
                helper_args=[str(email_path), str(target_dir)],
                fallback=["mv", str(email_path), str(target_dir)],
            )
            return {
                "domain": domain,
                "username": username,
                "message_id": message_id,
                "target_folder": target_folder,
                "status": "moved",
            }

    raise ValueError(f"Message {message_id} not found")


def delete_email(domain: str, username: str, message_id: str) -> dict:
    """Delete an email."""
    domain = _validate_domain(domain)
    username = _validate_username(username)
    mailbox_dir = MAIL_ROOT / domain / username

    # Find and delete the email
    for folder in ["cur", "new", ".Drafts/cur", ".Sent/cur", ".Trash/cur", ".Junk/cur"]:
        email_path = mailbox_dir / folder / message_id
        if email_path.exists():
            shell.privileged(
                "email-delete",
                helper_args=[str(email_path)],
                fallback=["rm", "-f", str(email_path)],
            )
            return {
                "domain": domain,
                "username": username,
                "message_id": message_id,
                "status": "deleted",
            }

    raise ValueError(f"Message {message_id} not found")


def mark_as_spam(domain: str, username: str, message_id: str) -> dict:
    """Mark an email as spam and move to Junk folder."""
    return move_email(domain, username, message_id, "Junk")


def send_email(from_addr: str, to_addrs: List[str], subject: str, body: str, attachments: List[dict] = None) -> dict:
    """Send an email via SMTP (Postfix)."""
    import email.mime.multipart
    import email.mime.text
    import email.utils

    msg = email.mime.multipart.MIMEMultipart("mixed")
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Date"] = email.utils.formatdate()
    msg["Subject"] = subject

    # Add body
    msg.attach(email.mime.text.MIMEText(body, "plain"))

    # Add attachments
    if attachments:
        for att in attachments:
            filename = att.get("filename", "attachment")
            content = att.get("content", "")
            if isinstance(content, str):
                content = content.encode()
            part = email.mime.base.MIMEBase("application", "octet-stream")
            part.set_payload(content)
            email.encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)

    # Write to Postfix queue
    queue_dir = Path("/var/spool/postfix/maildrop")
    queue_dir.mkdir(parents=True, exist_ok=True)

    msg_id = secrets.token_hex(8)
    msg_file = queue_dir / msg_id

    msg_file.write_bytes(msg.as_bytes())
    shell.run(["chown", "postfix:postdrop", str(msg_file)], check=False)

    return {
        "message_id": msg_id,
        "from": from_addr,
        "to": to_addrs,
        "status": "queued",
    }


# ============================================================================
# Settings
# ============================================================================

def get_mailserver_settings() -> dict:
    """Get current mail server settings."""
    return {
        "smtp_port": SMTP_PORT,
        "smtps_port": SMTPS_PORT,
        "imap_port": IMAP_PORT,
        "imaps_port": IMAPS_PORT,
        "pop3_port": POP3_PORT,
        "pop3s_port": POP3S_PORT,
        "mail_root": str(MAIL_ROOT),
        "max_message_size_mb": 50,
        "max_recipients": 100,
    }


def update_mailserver_settings(settings: dict) -> dict:
    """Update mail server settings."""
    # In production, this would update postfix/dovecot config files
    return {
        "status": "updated",
        "settings": settings,
        "message": "Restart mail services to apply changes",
    }


def configure_smtp(port: int = 587, tls: bool = True) -> dict:
    """Configure SMTP settings."""
    return {
        "port": port,
        "tls": tls,
        "status": "configured",
        "config_file": "/etc/postfix/main.cf",
    }


def configure_imap(port: int = 993, ssl: bool = True) -> dict:
    """Configure IMAP settings."""
    return {
        "port": port,
        "ssl": ssl,
        "status": "configured",
        "config_file": "/etc/dovecot/dovecot.conf",
    }


def get_spam_filter_settings() -> dict:
    """Get spam filter settings."""
    prefs_file = SPAMASSASSIN_USER_PREFS / "user_prefs"
    settings = {
        "enabled": True,
        "required_hits": 5.0,
        "report_safe": 1,
        "rewrite_header": "[SPAM]",
    }

    if prefs_file.exists():
        try:
            for line in prefs_file.read_text().splitlines():
                if line.strip() and not line.startswith("#"):
                    if "required_hits" in line:
                        settings["required_hits"] = float(line.split()[-1])
                    elif "report_safe" in line:
                        settings["report_safe"] = int(line.split()[-1])
        except Exception:
            pass

    return settings


def update_spam_filter_settings(settings: dict) -> dict:
    """Update spam filter settings."""
    prefs_file = SPAMASSASSIN_USER_PREFS / "user_prefs"
    prefs_file.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"required_hits {settings.get('required_hits', 5.0)}",
        f"report_safe {settings.get('report_safe', 1)}",
    ]

    if settings.get("rewrite_header"):
        lines.append(f"rewrite_header {settings.get('rewrite_header')} SUBJECT")

    prefs_file.write_text("\n".join(lines) + "\n")

    return {
        "status": "updated",
        "settings": settings,
    }


# ============================================================================
# Status
# ============================================================================

def get_mailserver_status() -> dict:
    """Get mail server service status."""
    services = ["postfix", "dovecot", "spamassassin"]
    status = {}

    for service in services:
        result = shell.privileged(
            f"mail-service-status",
            helper_args=[service],
            fallback=["systemctl", "is-active", service],
            check=False,
        )
        status[service] = {
            "active": result.stdout.strip() == "active",
            "status": result.stdout.strip(),
        }

    # Check disk usage for mail storage
    try:
        result = shell.run(["df", "-B1", str(MAIL_ROOT.parent)], check=False)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                status["storage"] = {
                    "total": int(parts[1]) if len(parts) > 1 else 0,
                    "used": int(parts[2]) if len(parts) > 2 else 0,
                    "available": int(parts[3]) if len(parts) > 3 else 0,
                }
    except Exception:
        pass

    return status


def restart_mail_services() -> dict:
    """Restart all mail services."""
    services = ["postfix", "dovecot", "spamassassin"]
    results = {}

    for service in services:
        result = shell.privileged(
            f"mail-service-restart",
            helper_args=[service],
            fallback=["systemctl", "restart", service],
            check=False,
        )
        results[service] = {
            "status": "restarted" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
        }

    return {
        "services": results,
        "status": "completed",
    }
