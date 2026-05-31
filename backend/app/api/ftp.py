"""
FTP account management API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, ensure_role
from app.models.entities import FTPAccount, User
from app.schemas.schemas import FtpAccountCreate, FtpAccountOut, FtpPasswordUpdate
from app.services import audit, ftp as ftp_service

router = APIRouter(prefix="/ftp", tags=["ftp"])


@router.post("/configure")
def configure_ftp(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Configure/install vsftpd."""
    ensure_role(current_user.role, Role.admin)
    result = ftp_service.configure_vsftpd()
    ftp_service.restart_ftp_service()
    audit.log_action(db, current_user.id, "configure_ftp", "vsftpd", request=request)
    return result


@router.get("/status")
def get_ftp_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get vsftpd service status."""
    ensure_role(current_user.role, Role.admin)
    return ftp_service.check_ftp_service_status()


@router.get("/users", response_model=List[FtpAccountOut])
def list_ftp_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all FTP users."""
    ensure_role(current_user.role, Role.admin)
    accounts = db.query(FTPAccount).all()
    return [FtpAccountOut.model_validate(acc) for acc in accounts]


@router.post("/users", response_model=FtpAccountOut)
def create_ftp_user(
    payload: FtpAccountCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new FTP user."""
    ensure_role(current_user.role, Role.admin)

    # Validate username
    username = payload.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    # Check if already exists
    existing = db.query(FTPAccount).filter(FTPAccount.username == username).first()
    if existing:
        raise HTTPException(status_code=409, detail="FTP user already exists")

    # Generate password if not provided
    password = payload.password
    if not password:
        password = ftp_service.generate_password()

    # Create system user
    try:
        result = ftp_service.create_ftp_user(username, password)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Store in database
    account = FTPAccount(
        username=result["username"],
        password_hash=result["password_hash"],
        home_directory=result["home_directory"],
        website_id=payload.website_id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    audit.log_action(db, current_user.id, "create_ftp_user", account.username, request=request)

    return FtpAccountOut(
        id=account.id,
        username=account.username,
        home_directory=account.home_directory,
        website_id=account.website_id,
        created_at=account.created_at.isoformat() if account.created_at else None,
        password=password,  # Only returned on creation
    )


@router.get("/users/{username}", response_model=FtpAccountOut)
def get_ftp_user(username: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get FTP user details."""
    ensure_role(current_user.role, Role.admin)
    account = db.query(FTPAccount).filter(FTPAccount.username == username).first()
    if not account:
        raise HTTPException(status_code=404, detail="FTP user not found")
    return FtpAccountOut.model_validate(account)


@router.put("/users/{username}/password")
def change_ftp_password(
    username: str,
    payload: FtpPasswordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change FTP user password."""
    ensure_role(current_user.role, Role.admin)

    account = db.query(FTPAccount).filter(FTPAccount.username == username).first()
    if not account:
        raise HTTPException(status_code=404, detail="FTP user not found")

    try:
        ftp_service.change_ftp_password(username, payload.password)
        account.password_hash = ftp_service.hash_ftp_password(payload.password)
        db.commit()
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit.log_action(db, current_user.id, "change_ftp_password", username, request=request)
    return {"message": f"Password changed for {username}"}


@router.delete("/users/{username}")
def delete_ftp_user(
    username: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an FTP user."""
    ensure_role(current_user.role, Role.admin)

    account = db.query(FTPAccount).filter(FTPAccount.username == username).first()
    if not account:
        raise HTTPException(status_code=404, detail="FTP user not found")

    try:
        ftp_service.delete_ftp_user(username)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.delete(account)
    db.commit()

    audit.log_action(db, current_user.id, "delete_ftp_user", username, request=request)
    return {"message": f"Deleted FTP user {username}"}
