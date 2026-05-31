from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="end_user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    website_limit: Mapped[int] = mapped_column(Integer, default=5)
    storage_limit_mb: Mapped[int] = mapped_column(Integer, default=1024)
    # Bumped to invalidate previously-issued JWTs (logout-everywhere, role
    # change, password reset by admin, account disable, etc).
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    websites: Mapped[List["Website"]] = relationship(back_populates="owner")


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    root_path: Mapped[str] = mapped_column(String(500))
    linux_user: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    php_version: Mapped[str] = mapped_column(String(16), default="8.3")
    app_type: Mapped[str] = mapped_column(String(32), default="wordpress")
    ssl_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    nginx_custom: Mapped[str] = mapped_column(Text, default="")
    waf_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    web_engine: Mapped[str] = mapped_column(String(50), default="nginx")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped[User] = relationship(back_populates="websites")
    database: Mapped["DatabaseAccount"] = relationship(back_populates="website", uselist=False)


class DatabaseAccount(Base):
    __tablename__ = "database_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id"))
    db_name: Mapped[str] = mapped_column(String(64), unique=True)
    db_user: Mapped[str] = mapped_column(String(64), unique=True)
    db_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    website: Mapped[Website] = relationship(back_populates="database")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(128))
    target: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jti: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SftpBackupTarget(Base):
    __tablename__ = "sftp_backup_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=22)
    username: Mapped[str] = mapped_column(String(128))
    password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    private_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remote_path: Mapped[str] = mapped_column(String(500), default="/backups/bpanel")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # TOFU host key pinning so the second SSH connection on cannot be silently
    # MITM'd. Populated on first successful connect (or by an explicit rotate
    # action) and verified on every connect afterwards.
    host_key_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    host_key_fingerprint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BackupSchedule(Base):
    __tablename__ = "backup_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_ids: Mapped[str] = mapped_column(Text, default="")
    all_users: Mapped[bool] = mapped_column(Boolean, default=False)
    target_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sftp_backup_targets.id"), nullable=True)
    schedule: Mapped[str] = mapped_column(String(100), default="0 2 * * *")
    retention: Mapped[int] = mapped_column(Integer, default=7)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str] = mapped_column(String(32), default="pending")
    last_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CronJob(Base):
    __tablename__ = "cron_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user: Mapped[str] = mapped_column(String(50), nullable=False, default="root")
    command: Mapped[str] = mapped_column(Text, nullable=False)
    schedule: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MailDomain(Base):
    """Mail domain configuration for the mail server."""
    __tablename__ = "mail_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    quota_gb: Mapped[int] = mapped_column(Integer, default=10)
    catch_all: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ssl_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    webmail_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    spam_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    spam_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    mailboxes: Mapped[List["Mailbox"]] = relationship(back_populates="domain")


class Mailbox(Base):
    """Mailbox within a mail domain."""
    __tablename__ = "mailboxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("mail_domains.id"), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quota_mb: Mapped[int] = mapped_column(Integer, default=5120)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    domain: Mapped["MailDomain"] = relationship(back_populates="mailboxes")


class VirtualEnvironment(Base):
    """Python virtual environment."""
    __tablename__ = "virtual_environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    python_version: Mapped[str] = mapped_column(String(32), nullable=False)
    python_executable: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlarmTask(Base):
    """Alarm task for monitoring and notifications."""
    __tablename__ = "alarm_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    alarm_type: Mapped[str] = mapped_column(String(50), nullable=False)  # cpu, memory, disk, network, service, custom
    notification_method: Mapped[str] = mapped_column(String(50), nullable=False)  # telegram, email, webhook
    condition_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON config
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PanelSetting(Base):
    """Panel setting key-value store."""
    __tablename__ = "panel_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BackupJob(Base):
    """Enhanced backup job configuration."""
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    job_type: Mapped[str] = mapped_column(String(50))  # full, incremental, differential
    destinations: Mapped[Optional[str]] = mapped_column(Text, default="[]")  # JSON list of destination types
    include_websites: Mapped[Optional[str]] = mapped_column(Text, default="[]")  # JSON list of website IDs
    include_databases: Mapped[Optional[str]] = mapped_column(Text, default="[]")  # JSON list of database IDs
    exclude_paths: Mapped[Optional[str]] = mapped_column(Text, default="[]")  # JSON list of exclude patterns
    schedule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    encryption_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    compression_level: Mapped[int] = mapped_column(Integer, default=6)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BackupStorage(Base):
    """Backup storage destination configuration."""
    __tablename__ = "backup_storages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    storage_type: Mapped[str] = mapped_column(String(50))  # ftp, s3, ssh, onedrive, etc.
    config: Mapped[Optional[str]] = mapped_column(Text, default="{}")  # JSON configuration (encrypted)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BackupHistory(Base):
    """Backup execution history."""
    __tablename__ = "backup_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("backup_jobs.id"), nullable=True)
    backup_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))  # running, completed, failed
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    destinations: Mapped[Optional[str]] = mapped_column(Text, default="[]")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
