from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, DateTime, Boolean, Float, ForeignKey, Integer, Numeric, JSON, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship
from app.config import DATABASE_URL

class Base(DeclarativeBase):
    pass

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def now_utc():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    team: Mapped[str] = mapped_column(String(80), default="GENERAL")
    branch: Mapped[str] = mapped_column(String(80), default="BRANCH-001")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class ServiceRequest(Base):
    __tablename__ = "service_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_ref: Mapped[str] = mapped_column(String(80), index=True)
    channel: Mapped[str] = mapped_column(String(30))
    request_type: Mapped[str] = mapped_column(String(40))
    subcategory: Mapped[str] = mapped_column(String(80), default="GENERAL")
    message: Mapped[str] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_review_required: Mapped[bool] = mapped_column(Boolean, default=True)
    identity_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[str] = mapped_column(String(2), default="P3")
    assigned_team: Mapped[str] = mapped_column(String(80), default="BRANCH_OPERATIONS")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="RECEIVED", index=True)
    approval_status: Mapped[str] = mapped_column(String(30), default="NOT_REQUIRED")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    action_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    action_amount: Mapped[float | None] = mapped_column(Numeric(14,2), nullable=True)
    action_currency: Mapped[str] = mapped_column(String(3), default="INR")
    action_executed: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_hours: Mapped[int] = mapped_column(Integer, default=72)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    original_sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("service_requests.id"), index=True)
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approver_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(30))
    amount: Mapped[float] = mapped_column(Numeric(14,2))
    decision: Mapped[str] = mapped_column(String(20), default="PENDING")
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("service_requests.id"), index=True)
    recipient_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recipient_role: Mapped[str] = mapped_column(String(40))
    trigger_type: Mapped[str] = mapped_column(String(60))
    channel: Mapped[str] = mapped_column(String(20), default="IN_APP")
    audience: Mapped[str] = mapped_column(String(20), default="CUSTOMER")
    message: Mapped[str] = mapped_column(Text)
    deduplication_key: Mapped[str] = mapped_column(String(180), unique=True)
    delivery_status: Mapped[str] = mapped_column(String(20), default="SIMULATED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Escalation(Base):
    __tablename__ = "escalations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("service_requests.id"), index=True)
    level: Mapped[int] = mapped_column(Integer)
    trigger_reason: Mapped[str] = mapped_column(String(160))
    escalated_to_role: Mapped[str] = mapped_column(String(40))
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String(40), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delay_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    actor_id: Mapped[str] = mapped_column(String(40))
    actor_role: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(80), index=True)
    previous_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    previous_hash: Mapped[str] = mapped_column(String(64), default="0" * 64)
    event_hash: Mapped[str] = mapped_column(String(64))

class SLAEvent(Base):
    __tablename__ = "sla_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("service_requests.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    threshold_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("service_requests.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(40))
    finding: Mapped[str] = mapped_column(Text)
    evidence_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
