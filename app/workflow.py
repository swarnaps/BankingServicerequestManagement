from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException
from app.db import ServiceRequest, Approval, Notification, Escalation, AuditEvent, SLAEvent, now_utc
from app.config import CONFIG
import hashlib, json

TRANSITIONS = {
 "RECEIVED": {"AI_CLASSIFIED", "PENDING_VERIFICATION"},
 "AI_CLASSIFIED": {"PENDING_VERIFICATION"},
 "PENDING_VERIFICATION": {"ASSIGNED", "PENDING_CUSTOMER_INFO"},
 "ASSIGNED": {"IN_PROGRESS", "PENDING_CUSTOMER_INFO"},
 "IN_PROGRESS": {"PENDING_CUSTOMER_INFO", "PENDING_APPROVAL", "RESOLVED"},
 "PENDING_CUSTOMER_INFO": {"PENDING_VERIFICATION", "ASSIGNED", "IN_PROGRESS"},
 "PENDING_APPROVAL": {"IN_PROGRESS"},
 "RESOLVED": {"CLOSED"},
 "ESCALATED": {"IN_PROGRESS", "PENDING_APPROVAL", "RESOLVED"}
}
def audit(db: Session, actor, action, req_id=None, old=None, new=None, reason=None):
    last = db.scalar(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(1))
    prev = last.event_hash if last else "0"*64
    eid = str(uuid4()); ts = now_utc().isoformat()
    payload = json.dumps({"id":eid,"request_id":req_id,"actor":actor.id,"role":actor.role,"action":action,
                          "old":old,"new":new,"reason":reason,"timestamp":ts,"previous_hash":prev},
                         sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    db.add(AuditEvent(id=eid, request_id=req_id, actor_id=actor.id, actor_role=actor.role,
                      action=action, previous_value=old, new_value=new, reason=reason,
                      previous_hash=prev, event_hash=digest))

def notify(db, req, trigger, message, audience="CUSTOMER", recipient=None, role="CUSTOMER", channel="IN_APP"):
    key = f"{req.id}:{trigger}:{audience}:{recipient or role}"
    exists = db.scalar(select(Notification).where(Notification.deduplication_key == key))
    if exists: return exists
    n = Notification(id=str(uuid4()), request_id=req.id, recipient_id=recipient,
                     recipient_role=role, trigger_type=trigger, channel=channel,
                     audience=audience, message=message, deduplication_key=key,
                     delivery_status="SIMULATED", sent_at=now_utc())
    db.add(n)
    return n

def set_status(db, actor, req, status, reason=None):
    if status not in TRANSITIONS.get(req.status, set()):
        raise HTTPException(409, f"Invalid status transition: {req.status} -> {status}")
    old = {"status": req.status}; req.status = status; req.updated_at = now_utc()
    audit(db, actor, "STATUS_CHANGED", req.id, old, {"status":status}, reason)
    notify(db, req, f"STATUS_{status}", f"Your service request {req.id[:8]} is now {status.replace('_',' ').lower()}.")
    if status == "RESOLVED": req.resolved_at = now_utc()
    if status == "CLOSED": req.closed_at = now_utc()

def create_escalation(db, actor, req, level, role, reason):
    esc = Escalation(id=str(uuid4()), request_id=req.id, level=level,
                     trigger_reason=reason, escalated_to_role=role)
    db.add(esc)
    notify(db, req, f"ESCALATION_L{level}", f"Request {req.id[:8]} requires operational attention.",
           audience="INTERNAL", role=role)
    audit(db, actor, "ESCALATION_CREATED", req.id, None, {"level":level,"role":role}, reason)
    if req.status not in {"RESOLVED","CLOSED"}:
        req.status = "ESCALATED"
    return esc

def run_sla_monitor(db: Session, actor):
    now = now_utc(); result = {"reminders":0,"escalations":0}
    cases = db.scalars(select(ServiceRequest).where(~ServiceRequest.status.in_(["RESOLVED","CLOSED"]))).all()
    for req in cases:
        total = max((req.current_sla_deadline - req.created_at).total_seconds(), 1)
        consumed = (now - req.created_at).total_seconds() / total * 100
        for threshold in CONFIG["sla_thresholds"]:
            key = f"{req.id}:SLA_{threshold}:INTERNAL:{'SLA_MONITOR'}"
            exists = db.scalar(select(Notification).where(Notification.deduplication_key == key))
            if consumed >= threshold and not exists:
                if threshold == 75:
                    notify(db, req, "SLA_75", f"Reminder: request {req.id[:8]} has consumed 75% of its SLA.",
                           "INTERNAL", role="OPERATIONS_EXECUTIVE", recipient=req.owner_id)
                    result["reminders"] += 1
                    db.add(SLAEvent(id=str(uuid4()), request_id=req.id, event_type="REMINDER", threshold_percentage=75, detail="75% SLA consumed"))
                elif threshold == 90:
                    notify(db, req, "SLA_90", f"Warning: request {req.id[:8]} is nearing SLA breach.",
                           "INTERNAL", role="OPERATIONS_SUPERVISOR")
                    result["reminders"] += 1
                    db.add(SLAEvent(id=str(uuid4()), request_id=req.id, event_type="WARNING", threshold_percentage=90, detail="90% SLA consumed"))
                elif threshold == 100:
                    create_escalation(db, actor, req, 2, "OPERATIONS_SUPERVISOR", "SLA_BREACHED")
                    db.add(SLAEvent(id=str(uuid4()), request_id=req.id, event_type="BREACH", threshold_percentage=100, detail="SLA breached"))
                    result["escalations"] += 1
                elif threshold == 125:
                    create_escalation(db, actor, req, 3, "CENTRAL_OPERATIONS", "SLA_125_PERCENT")
                    db.add(SLAEvent(id=str(uuid4()), request_id=req.id, event_type="CRITICAL_ESCALATION", threshold_percentage=125, detail="125% SLA consumed"))
                    result["escalations"] += 1
    db.commit()
    return result
