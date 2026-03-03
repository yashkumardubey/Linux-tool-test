"""SQLAlchemy ORM models — enterprise patch management."""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float,
    ForeignKey, Enum, Table, JSON, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from database import Base


# ── Enums ──

class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"
    auditor = "auditor"


class JobStatus(str, enum.Enum):
    pending = "pending"
    scheduled = "scheduled"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"
    rolled_back = "rolled_back"


class PatchAction(str, enum.Enum):
    upgrade = "upgrade"
    install = "install"
    rollback = "rollback"
    snapshot = "snapshot"
    offline_install = "offline_install"
    server_patch = "server_patch"


class Severity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    negligible = "negligible"


# ── Association tables ──

host_group_assoc = Table(
    "host_group_assoc",
    Base.metadata,
    Column("host_id", Integer, ForeignKey("hosts.id", ondelete="CASCADE")),
    Column("group_id", Integer, ForeignKey("host_groups.id", ondelete="CASCADE")),
)

host_tag_assoc = Table(
    "host_tag_assoc",
    Base.metadata,
    Column("host_id", Integer, ForeignKey("hosts.id", ondelete="CASCADE")),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE")),
)


# ── Users ──

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), default="")
    role = Column(Enum(UserRole), default=UserRole.viewer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    audit_logs = relationship("AuditLog", back_populates="user")


# ── Hosts ──

class Host(Base):
    __tablename__ = "hosts"
    id = Column(Integer, primary_key=True)
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    ip = Column(String(45), nullable=False)
    os = Column(String(100), default="")
    os_version = Column(String(50), default="")
    kernel = Column(String(100), default="")
    arch = Column(String(20), default="")
    agent_version = Column(String(20), default="")
    agent_token = Column(String(100), default="")
    is_online = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime, nullable=True)
    last_patched = Column(DateTime, nullable=True)
    reboot_required = Column(Boolean, default=False)
    installed_count = Column(Integer, default=0)
    upgradable_count = Column(Integer, default=0)
    cve_count = Column(Integer, default=0)
    compliance_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    groups = relationship("HostGroup", secondary=host_group_assoc, back_populates="hosts")
    tags = relationship("Tag", secondary=host_tag_assoc, back_populates="hosts")
    patch_jobs = relationship("PatchJob", back_populates="host")
    snapshots_db = relationship("Snapshot", back_populates="host")
    host_cves = relationship("HostCVE", back_populates="host")

    __table_args__ = (Index("ix_hosts_ip", "ip"),)


# ── Host Groups ──

class HostGroup(Base):
    __tablename__ = "host_groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    hosts = relationship("Host", secondary=host_group_assoc, back_populates="groups")
    schedules = relationship("PatchSchedule", back_populates="group")


# ── Tags ──

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    hosts = relationship("Host", secondary=host_tag_assoc, back_populates="tags")


# ── Patch Jobs ──

class PatchJob(Base):
    __tablename__ = "patch_jobs"
    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    action = Column(Enum(PatchAction), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.pending)
    packages = Column(JSON, default=list)
    hold_packages = Column(JSON, default=list)
    dry_run = Column(Boolean, default=False)
    auto_snapshot = Column(Boolean, default=True)
    auto_rollback = Column(Boolean, default=True)
    result = Column(JSON, nullable=True)
    output = Column(Text, default="")
    initiated_by = Column(String(100), default="system")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    host = relationship("Host", back_populates="patch_jobs")


# ── Snapshots ──

class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    packages_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    host = relationship("Host", back_populates="snapshots_db")

    __table_args__ = (UniqueConstraint("host_id", "name", name="uq_host_snapshot"),)


# ── Patch Schedules ──

class PatchSchedule(Base):
    __tablename__ = "patch_schedules"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    group_id = Column(Integer, ForeignKey("host_groups.id", ondelete="SET NULL"), nullable=True)
    cron_expression = Column(String(100), nullable=False)  # e.g. "0 2 * * SAT"
    auto_snapshot = Column(Boolean, default=True)
    auto_rollback = Column(Boolean, default=True)
    auto_reboot = Column(Boolean, default=False)
    packages = Column(JSON, default=list)
    hold_packages = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_by = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    group = relationship("HostGroup", back_populates="schedules")

    # Blackout windows (JSON list of {"start": "HH:MM", "end": "HH:MM", "days": [0-6]})
    blackout_windows = Column(JSON, default=list)


# ── CVE / Security Advisories ──

class CVE(Base):
    __tablename__ = "cves"
    id = Column(Integer, primary_key=True)
    cve_id = Column(String(30), unique=True, nullable=False, index=True)  # CVE-2024-12345
    severity = Column(Enum(Severity), default=Severity.medium)
    cvss_score = Column(Float, nullable=True)
    description = Column(Text, default="")
    affected_packages = Column(JSON, default=list)  # ["openssl", "libssl3"]
    fixed_in = Column(JSON, default=dict)  # {"openssl": "3.0.2-0ubuntu1.15"}
    advisory_url = Column(String(500), default="")
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    host_cves = relationship("HostCVE", back_populates="cve")


class HostCVE(Base):
    __tablename__ = "host_cves"
    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    cve_id = Column(Integer, ForeignKey("cves.id", ondelete="CASCADE"), nullable=False)
    is_patched = Column(Boolean, default=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    patched_at = Column(DateTime, nullable=True)

    host = relationship("Host", back_populates="host_cves")
    cve = relationship("CVE", back_populates="host_cves")

    __table_args__ = (UniqueConstraint("host_id", "cve_id", name="uq_host_cve"),)


# ── Audit Log ──

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)  # "patch.execute", "snapshot.create"
    resource_type = Column(String(50), default="")  # "host", "group", "schedule"
    resource_id = Column(String(100), default="")
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (Index("ix_audit_created", "created_at"),)


# ── Notification Channels ──

class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    channel_type = Column(String(30), nullable=False)  # "email", "slack", "teams", "webhook"
    config = Column(JSON, default=dict)  # {"url": "...", "token": "...", etc.}
    events = Column(JSON, default=list)  # ["patch.failed", "cve.critical", "agent.offline"]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
