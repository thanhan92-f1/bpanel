"""
Mail Server API endpoints for managing mail domains, mailboxes, and settings.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import get_current_user
from app.core.permissions import Role, ensure_role
from app.models.entities import User
from app.schemas.schemas import DomainValidator
from app.services import audit, mailserver as mail_service

router = APIRouter(prefix="/mail", tags=["mail"])


# ============================================================================
# Request/Response Models
# ============================================================================

class MailDomainCreate(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)
    quota_gb: int = Field(default=10, ge=1, le=10000)

    @classmethod
    def validate_domain(cls, value: str) -> str:
        return DomainValidator.validate_domain(value)


class MailDomainQuotaUpdate(BaseModel):
    quota_gb: int = Field(..., ge=1, le=10000)


class CatchAllCreate(BaseModel):
    forward_to: EmailStr


class MailboxCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    quota_mb: int = Field(default=5120, ge=1, le=102400)


class MailboxBatchCreate(BaseModel):
    mailboxes: List[MailboxCreate]


class MailboxPasswordUpdate(BaseModel):
    password: str = Field(..., min_length=8, max_length=128)


class MailboxQuotaUpdate(BaseModel):
    quota_mb: int = Field(..., ge=1, le=102400)


class EmailMoveRequest(BaseModel):
    folder: str = Field(..., pattern=r"^(INBOX|Drafts|Sent|Trash|Junk)$")


class EmailSendRequest(BaseModel):
    from_addr: EmailStr
    to_addrs: List[EmailStr] = Field(..., min_length=1, max_length=100)
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    attachments: Optional[List[dict]] = None


class MailServerSettingsUpdate(BaseModel):
    max_message_size_mb: Optional[int] = Field(default=None, ge=1, le=500)
    max_recipients: Optional[int] = Field(default=None, ge=1, le=1000)


class SpamFilterSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    required_hits: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    report_safe: Optional[int] = Field(default=None, ge=0, le=2)
    rewrite_header: Optional[str] = None


# ============================================================================
# Mail Domain Endpoints
# ============================================================================

@router.get("/domains")
def list_mail_domains(
    db=None,
    current_user: User = Depends(get_current_user),
):
    """List all configured mail domains."""
    ensure_role(current_user.role, Role.admin)
    return mail_service.list_mail_domains()


@router.post("/domains")
def create_mail_domain(
    payload: MailDomainCreate,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Add a new mail domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.add_mail_domain(payload.domain, payload.quota_gb)
        audit.log_action(db, current_user.id, "create_mail_domain", payload.domain, request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/domains/{domain}")
def delete_mail_domain(
    domain: str,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Remove a mail domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.remove_mail_domain(domain)
        audit.log_action(db, current_user.id, "delete_mail_domain", domain, request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/domains/{domain}")
def get_domain_info(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a mail domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        return mail_service.get_domain_info(domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/domains/{domain}/quota")
def update_domain_quota(
    domain: str,
    payload: MailDomainQuotaUpdate,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Set storage quota for a domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.set_domain_quota(domain, payload.quota_gb)
        audit.log_action(db, current_user.id, "update_domain_quota", f"{domain}:{payload.quota_gb}GB", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/domains/{domain}/ssl")
def configure_domain_ssl(
    domain: str,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Configure SSL/TLS for a mail domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.configure_domain_ssl(domain)
        audit.log_action(db, current_user.id, "configure_domain_ssl", domain, request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/domains/{domain}/spam-check")
def check_domain_spam(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Check if domain is on spam blacklists."""
    ensure_role(current_user.role, Role.admin)

    try:
        return mail_service.check_domain_spam_list(domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/domains/{domain}/dns-refresh")
def refresh_domain_dns(
    domain: str,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Refresh DNS records for mail domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.refresh_domain_dns(domain)
        audit.log_action(db, current_user.id, "refresh_domain_dns", domain, request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/domains/{domain}/catchall")
def get_catch_all(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Get catch-all email configuration for a domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        domain_info = mail_service.get_domain_info(domain)
        # Check for catch-all file
        from pathlib import Path
        catch_all_file = Path(f"/var/vmail/{domain}/.catch_all")
        if catch_all_file.exists():
            forward_to = catch_all_file.read_text().strip()
            return {"domain": domain, "enabled": True, "forward_to": forward_to}
        return {"domain": domain, "enabled": False}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/domains/{domain}/catchall")
def set_catch_all(
    domain: str,
    payload: CatchAllCreate,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Enable catch-all email routing for a domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.enable_catch_all(domain, payload.forward_to)
        audit.log_action(db, current_user.id, "enable_catch_all", f"{domain} -> {payload.forward_to}", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/domains/{domain}/catchall")
def disable_catch_all(
    domain: str,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Disable catch-all email routing for a domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.disable_catch_all(domain)
        audit.log_action(db, current_user.id, "disable_catch_all", domain, request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/domains/{domain}/webmail")
def get_webmail_url(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Get webmail URL for a domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        return {
            "domain": domain,
            "webmail_url": mail_service.get_webmail_url(domain),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# Mailbox Endpoints
# ============================================================================

@router.get("/domains/{domain}/mailboxes")
def list_domain_mailboxes(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """List all mailboxes for a domain."""
    ensure_role(current_user.role, Role.admin)

    try:
        return mail_service.list_mailboxes(domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/domains/{domain}/mailboxes")
def create_mailbox(
    domain: str,
    payload: MailboxCreate,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Create a new mailbox."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.add_mailbox(domain, payload.username, payload.password or "", payload.quota_mb)
        result["password"] = payload.password or result.get("password", "")
        audit.log_action(db, current_user.id, "create_mailbox", f"{domain}:{payload.username}", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/domains/{domain}/mailboxes/{username}")
def delete_mailbox(
    domain: str,
    username: str,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Delete a mailbox."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.remove_mailbox(domain, username)
        audit.log_action(db, current_user.id, "delete_mailbox", f"{domain}:{username}", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/domains/{domain}/mailboxes/{username}/password")
def change_mailbox_password(
    domain: str,
    username: str,
    payload: MailboxPasswordUpdate,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Update mailbox password."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.update_mailbox_password(domain, username, payload.password)
        audit.log_action(db, current_user.id, "change_mailbox_password", f"{domain}:{username}", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/domains/{domain}/mailboxes/{username}/quota")
def update_mailbox_quota(
    domain: str,
    username: str,
    payload: MailboxQuotaUpdate,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Update mailbox quota."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.update_mailbox_quota(domain, username, payload.quota_mb)
        audit.log_action(db, current_user.id, "update_mailbox_quota", f"{domain}:{username}", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/domains/{domain}/mailboxes/batch")
def batch_create_mailboxes(
    domain: str,
    payload: MailboxBatchCreate,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Create multiple mailboxes at once."""
    ensure_role(current_user.role, Role.admin)

    mailboxes = [
        {"username": mb.username, "password": mb.password, "quota_mb": mb.quota_mb}
        for mb in payload.mailboxes
    ]

    try:
        result = mail_service.batch_create_mailboxes(domain, mailboxes)
        audit.log_action(db, current_user.id, "batch_create_mailboxes", f"{domain}:{len(mailboxes)} mailboxes", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/domains/{domain}/mailboxes/import")
def import_mailboxes(
    domain: str,
    csv_content: str = Body(..., embed=True),
    request: Request = None,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Import mailboxes from CSV content."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.import_mailboxes_from_csv(domain, csv_content)
        audit.log_action(db, current_user.id, "import_mailboxes", f"{domain}:{result['total_created']} imported", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/domains/{domain}/mailboxes/export")
def export_mailboxes(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Export mailboxes to CSV format."""
    ensure_role(current_user.role, Role.admin)

    try:
        csv_content = mail_service.export_mailboxes_to_csv(domain)
        return {"csv": csv_content}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/domains/{domain}/mailboxes/{username}/info")
def get_mailbox_info(
    domain: str,
    username: str,
    current_user: User = Depends(get_current_user),
):
    """Get detailed mailbox information."""
    ensure_role(current_user.role, Role.admin)

    try:
        return mail_service.get_mailbox_info(domain, username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# Email Endpoints
# ============================================================================

@router.get("/domains/{domain}/mailboxes/{username}/emails")
def get_emails(
    domain: str,
    username: str,
    folder: str = Query(default="INBOX", pattern=r"^(INBOX|Drafts|Sent|Trash|Junk)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
):
    """Get emails from a mailbox folder."""
    ensure_role(current_user.role, Role.admin)

    try:
        return mail_service.get_emails(domain, username, folder, page, per_page)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/domains/{domain}/mailboxes/{username}/emails/{message_id}")
def get_email_content(
    domain: str,
    username: str,
    message_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get full email content."""
    ensure_role(current_user.role, Role.admin)

    try:
        return mail_service.get_email_content(domain, username, message_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/domains/{domain}/mailboxes/{username}/emails/{message_id}/move")
def move_email(
    domain: str,
    username: str,
    message_id: str,
    payload: EmailMoveRequest,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Move an email to a different folder."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.move_email(domain, username, message_id, payload.folder)
        audit.log_action(db, current_user.id, "move_email", f"{domain}:{username}/{message_id} -> {payload.folder}", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/domains/{domain}/mailboxes/{username}/emails/{message_id}")
def delete_email(
    domain: str,
    username: str,
    message_id: str,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Delete an email."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.delete_email(domain, username, message_id)
        audit.log_action(db, current_user.id, "delete_email", f"{domain}:{username}/{message_id}", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/domains/{domain}/mailboxes/{username}/emails/{message_id}/spam")
def mark_as_spam(
    domain: str,
    username: str,
    message_id: str,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Mark an email as spam."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.mark_as_spam(domain, username, message_id)
        audit.log_action(db, current_user.id, "mark_as_spam", f"{domain}:{username}/{message_id}", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/send")
def send_email(
    payload: EmailSendRequest,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Send an email via SMTP."""
    ensure_role(current_user.role, Role.admin)

    try:
        result = mail_service.send_email(
            payload.from_addr,
            payload.to_addrs,
            payload.subject,
            payload.body,
            payload.attachments,
        )
        audit.log_action(db, current_user.id, "send_email", f"{payload.from_addr} -> {', '.join(payload.to_addrs)}", request=request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# Settings Endpoints
# ============================================================================

@router.get("/settings")
def get_settings(
    current_user: User = Depends(get_current_user),
):
    """Get current mail server settings."""
    ensure_role(current_user.role, Role.admin)
    return mail_service.get_mailserver_settings()


@router.put("/settings")
def update_settings(
    payload: MailServerSettingsUpdate,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Update mail server settings."""
    ensure_role(current_user.role, Role.admin)

    settings = payload.model_dump(exclude_none=True)
    result = mail_service.update_mailserver_settings(settings)
    audit.log_action(db, current_user.id, "update_mail_settings", str(settings), request=request)
    return result


@router.get("/status")
def get_status(
    current_user: User = Depends(get_current_user),
):
    """Get mail server service status."""
    ensure_role(current_user.role, Role.admin)
    return mail_service.get_mailserver_status()


@router.post("/restart")
def restart_services(
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Restart all mail services."""
    ensure_role(current_user.role, Role.admin)

    result = mail_service.restart_mail_services()
    audit.log_action(db, current_user.id, "restart_mail_services", "all", request=request)
    return result


@router.get("/spam-filter")
def get_spam_filter_settings(
    current_user: User = Depends(get_current_user),
):
    """Get spam filter settings."""
    ensure_role(current_user.role, Role.admin)
    return mail_service.get_spam_filter_settings()


@router.put("/spam-filter")
def update_spam_filter_settings(
    payload: SpamFilterSettingsUpdate,
    request: Request,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """Update spam filter settings."""
    ensure_role(current_user.role, Role.admin)

    settings = payload.model_dump(exclude_none=True)
    result = mail_service.update_spam_filter_settings(settings)
    audit.log_action(db, current_user.id, "update_spam_filter", str(settings), request=request)
    return result


# Helper to import Body for import_mailboxes
from fastapi import Body
