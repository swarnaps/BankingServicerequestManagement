from datetime import timedelta, timezone
from uuid import uuid4
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db import get_db, init_db, User, ServiceRequest, Approval, Notification, Escalation, AuditEvent, Investigation, now_utc
from app.security import current_user, require_roles, require_request_scope
from app.guardrails import sanitise_customer_text, assert_customer_safe_message
from app.ai import analyse_request
from app.workflow import audit, notify, set_status, run_sla_monitor
from app.config import API_PREFIX, CONFIG
from app.seed import seed

app = FastAPI(title="AI Friday Banking Service Request API", version="1.0.0",
              description="Controlled hackathon POC. Synthetic data only; no production financial actions.")
@app.on_event("startup")
def startup():
    seed()

class RequestCreate(BaseModel):
    customer_ref: str = Field(min_length=3, max_length=80)
    channel: str = Field(pattern="^(BRANCH|MOBILE_APP|CONTACT_CENTRE)$")
    request_type: str = Field(pattern="^(BANK_STATEMENT|TRANSACTION_DISCREPANCY)$")
    message: str = Field(min_length=8, max_length=4000)
    fields: dict = Field(default_factory=dict)

class ReviewAI(BaseModel):
    request_type: str
    subcategory: str
    priority: str = Field(pattern="^(P1|P2|P3|P4)$")
    assigned_team: str
    corrected_summary: str | None = None
    identity_verified: bool = False

class AssignBody(BaseModel):
    owner_id: str
    assigned_team: str

class StatusBody(BaseModel):
    status: str
    reason: str | None = None

class InvestigationBody(BaseModel):
    finding: str = Field(min_length=5, max_length=2000)
    evidence_reference: str | None = None

class ApprovalSubmit(BaseModel):
    action_type: str = Field(pattern="^(WAIVER|REFUND|REVERSAL)$")
    amount: Decimal = Field(gt=0, le=1000000)
    currency: str = "INR"
    justification: str = Field(min_length=10, max_length=2000)

class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED|RETURNED)$")
    comments: str = Field(min_length=3, max_length=1000)

class ConfirmAction(BaseModel):
    processing_reference: str = Field(min_length=4, max_length=100)
    confirmation: str = Field(min_length=8, max_length=500)

class ResolveBody(BaseModel):
    notes: str = Field(min_length=5, max_length=2000)
    evidence: str = Field(min_length=5, max_length=1000)

class EscalationAction(BaseModel):
    delay_reason: str = Field(min_length=5, max_length=1000)
    action_plan: str = Field(min_length=5, max_length=1000)

@app.get("/health")
def health():
    return {"status":"ok","mode":"POC","financial_execution":"disabled"}

@app.get(API_PREFIX + "/users")
def users(db: Session = Depends(get_db), actor=Depends(require_roles("SYSTEM_ADMIN"))):
    return [{"id":u.id,"username":u.username,"role":u.role,"team":u.team,"active":u.active}
            for u in db.scalars(select(User)).all()]

@app.post(API_PREFIX + "/requests", status_code=201)
def create_request(body: RequestCreate, db: Session = Depends(get_db), actor=Depends(current_user)):
    if actor.role == "CUSTOMER":
        expected = actor.id.replace("customer_", "CUST-").upper()
        if body.customer_ref != expected:
            raise HTTPException(403, "Customer can create requests only for their own customer reference")
    msg = sanitise_customer_text(body.message)
    fields = dict(body.fields)
    ai = analyse_request(msg, body.request_type, fields)
    hours = CONFIG["sla_hours"].get(ai.recommended_priority, 72)
    now = now_utc()
    req = ServiceRequest(id=str(uuid4()), customer_ref=body.customer_ref, channel=body.channel,
        request_type=body.request_type, subcategory=ai.subcategory, message=msg,
        ai_summary=ai.summary, extracted_fields=ai.extracted_fields, ai_confidence=ai.confidence,
        ai_review_required=ai.human_review_required, priority=ai.recommended_priority,
        assigned_team=ai.recommended_team, status="AI_CLASSIFIED", approval_status="NOT_REQUIRED",
        sla_hours=hours, created_at=now, original_sla_deadline=now+timedelta(hours=hours),
        current_sla_deadline=now+timedelta(hours=hours))
    db.add(req); db.flush()
    audit(db, actor, "REQUEST_CREATED", req.id, None, {"request_type":req.request_type,"status":req.status})
    notify(db, req, "REQUEST_RECEIVED", f"Your service request {req.id[:8]} has been received.")
    if ai.human_review_required:
        notify(db, req, "AI_REVIEW_REQUIRED", f"Request {req.id[:8]} requires employee review.",
               audience="INTERNAL", role="BRANCH_EMPLOYEE")
    db.commit()
    return {"request_id":req.id,"status":req.status,"ai_analysis":ai.model_dump(),
            "human_review_required":req.ai_review_required,"sla_deadline":req.current_sla_deadline}

@app.get(API_PREFIX + "/requests")
def list_requests(db: Session = Depends(get_db), actor=Depends(current_user), status: str | None = None):
    query = select(ServiceRequest).order_by(ServiceRequest.created_at.desc())
    if status: query = query.where(ServiceRequest.status == status)
    rows = db.scalars(query).all()
    return [serialize_request(r) for r in rows if __import__("app.security",fromlist=["can_view_request"]).can_view_request(actor,r)]

def serialize_request(r):
    return {"request_id":r.id,"customer_ref":r.customer_ref,"channel":r.channel,"request_type":r.request_type,
            "subcategory":r.subcategory,"summary":r.ai_summary,"priority":r.priority,"assigned_team":r.assigned_team,
            "owner_id":r.owner_id,"status":r.status,"approval_status":r.approval_status,
            "approval_required":r.approval_required,"sla_deadline":r.current_sla_deadline,
            "created_at":r.created_at,"ai_confidence":r.ai_confidence,"ai_review_required":r.ai_review_required}

@app.get(API_PREFIX + "/requests/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db), actor=Depends(current_user)):
    req = db.get(ServiceRequest, request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor, req)
    data = serialize_request(req)
    if actor.role != "CUSTOMER":
        data.update({"message":req.message,"extracted_fields":req.extracted_fields,"resolution_notes":req.resolution_notes,
                     "resolution_evidence":req.resolution_evidence,"identity_verified":req.identity_verified})
    data["notifications"] = [{"trigger":n.trigger_type,"message":n.message,"audience":n.audience,"created_at":n.created_at}
                             for n in db.scalars(select(Notification).where(Notification.request_id==req.id)).all()
                             if actor.role != "CUSTOMER" or n.audience == "CUSTOMER"]
    return data

@app.post(API_PREFIX + "/requests/{request_id}/review-ai")
def review_ai(request_id: str, body: ReviewAI, db: Session=Depends(get_db),
              actor=Depends(require_roles("BRANCH_EMPLOYEE","OPERATIONS_EXECUTIVE","OPERATIONS_SUPERVISOR","CENTRAL_OPERATIONS"))):
    req=db.get(ServiceRequest,request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor,req)
    old={"request_type":req.request_type,"subcategory":req.subcategory,"priority":req.priority}
    req.request_type=body.request_type; req.subcategory=body.subcategory; req.priority=body.priority
    req.assigned_team=body.assigned_team; req.identity_verified=body.identity_verified
    if body.corrected_summary: req.ai_summary=body.corrected_summary
    req.ai_review_required=False
    if req.status=="AI_CLASSIFIED": req.status="PENDING_VERIFICATION"
    audit(db,actor,"AI_REVIEW_CONFIRMED",req.id,old,{"request_type":req.request_type,"subcategory":req.subcategory,"priority":req.priority})
    db.commit()
    return serialize_request(req)

@app.post(API_PREFIX + "/requests/{request_id}/assign")
def assign(request_id: str, body: AssignBody, db: Session=Depends(get_db),
           actor=Depends(require_roles("OPERATIONS_SUPERVISOR","SYSTEM_ADMIN"))):
    req=db.get(ServiceRequest,request_id)
    target=db.get(User,body.owner_id)
    if not req or not target: raise HTTPException(404,"Request or owner not found")
    if actor.role=="OPERATIONS_SUPERVISOR" and actor.team!="ALL" and body.assigned_team!=actor.team:
        raise HTTPException(403,"Cannot assign outside supervisor team")
    old={"owner_id":req.owner_id,"team":req.assigned_team}
    req.owner_id=target.id; req.assigned_team=body.assigned_team
    if req.status in {"PENDING_VERIFICATION","AI_CLASSIFIED"}: req.status="ASSIGNED"
    audit(db,actor,"REQUEST_ASSIGNED",req.id,old,{"owner_id":req.owner_id,"team":req.assigned_team})
    notify(db,req,"REQUEST_ASSIGNED","Your request has been assigned to our operations team.")
    db.commit()
    return serialize_request(req)

@app.post(API_PREFIX + "/requests/{request_id}/status")
def change_status(request_id: str, body: StatusBody, db: Session=Depends(get_db),
                  actor=Depends(require_roles("BRANCH_EMPLOYEE","OPERATIONS_EXECUTIVE","OPERATIONS_SUPERVISOR","CENTRAL_OPERATIONS"))):
    req=db.get(ServiceRequest,request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor,req)
    if body.status in {"RESOLVED","CLOSED","PENDING_APPROVAL"}:
        raise HTTPException(403,"Use the dedicated resolve/close/approval endpoint")
    set_status(db,actor,req,body.status,body.reason); db.commit()
    return serialize_request(req)

@app.post(API_PREFIX + "/requests/{request_id}/investigation")
def investigation(request_id: str, body: InvestigationBody, db: Session=Depends(get_db),
                  actor=Depends(require_roles("OPERATIONS_EXECUTIVE","OPERATIONS_SUPERVISOR","CENTRAL_OPERATIONS"))):
    req=db.get(ServiceRequest,request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor,req)
    inv=Investigation(id=str(uuid4()),request_id=req.id,actor_id=actor.id,finding=body.finding,evidence_reference=body.evidence_reference)
    db.add(inv); audit(db,actor,"INVESTIGATION_ADDED",req.id,None,{"finding":body.finding,"evidence_reference":body.evidence_reference})
    if req.status in {"ASSIGNED","ESCALATED"}: req.status="IN_PROGRESS"
    db.commit()
    return {"investigation_id":inv.id,"status":req.status}

@app.post(API_PREFIX + "/requests/{request_id}/submit-approval")
def submit_approval(request_id: str, body: ApprovalSubmit, db: Session=Depends(get_db),
                    actor=Depends(require_roles("OPERATIONS_EXECUTIVE","OPERATIONS_SUPERVISOR","CENTRAL_OPERATIONS"))):
    req=db.get(ServiceRequest,request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor,req)
    policy=CONFIG["approval_limits"].get(body.action_type)
    if not policy or float(body.amount)>policy["max_amount"]:
        raise HTTPException(422,"Amount exceeds configured POC approval limit; route to higher delegated authority")
    if req.status not in {"IN_PROGRESS","ASSIGNED","ESCALATED"}:
        raise HTTPException(409,"Request must be under active investigation before approval")
    req.approval_required=True; req.approval_status="PENDING"; req.action_type=body.action_type
    req.action_amount=float(body.amount); req.action_currency=body.currency; req.status="PENDING_APPROVAL"
    approval=Approval(id=str(uuid4()),request_id=req.id,requested_by=actor.id,action_type=body.action_type,
                      amount=body.amount,decision="PENDING")
    db.add(approval); audit(db,actor,"APPROVAL_SUBMITTED",req.id,None,{"action_type":body.action_type,"amount":str(body.amount),"justification":body.justification})
    notify(db,req,"APPROVAL_PENDING","Your request is awaiting the required internal review.")
    db.commit()
    return {"approval_id":approval.id,"request_id":req.id,"decision":"PENDING"}

@app.post(API_PREFIX + "/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, body: ApprovalDecision, db: Session=Depends(get_db),
                    actor=Depends(require_roles("AUTHORISED_APPROVER"))):
    approval=db.get(Approval,approval_id)
    if not approval: raise HTTPException(404,"Approval not found")
    req=db.get(ServiceRequest,approval.request_id)
    if not req: raise HTTPException(404,"Request not found")
    if approval.requested_by==actor.id: raise HTTPException(403,"Self-approval is prohibited")
    if approval.decision!="PENDING": raise HTTPException(409,"Approval already decided")
    policy=CONFIG["approval_limits"][approval.action_type]
    if float(approval.amount)>policy["max_amount"]: raise HTTPException(403,"Approver authority limit exceeded")
    approval.approver_id=actor.id; approval.decision=body.decision; approval.comments=body.comments; approval.decided_at=now_utc()
    req.approval_status=body.decision
    audit(db,actor,"APPROVAL_DECIDED",req.id,{"decision":"PENDING"},{"decision":body.decision,"comments":body.comments})
    if body.decision=="APPROVED":
        req.status="IN_PROGRESS"
        notify(db,req,"APPROVAL_APPROVED","Your request has received the required approval.")
    elif body.decision=="REJECTED":
        req.status="IN_PROGRESS"
        notify(db,req,"APPROVAL_REJECTED","Your request could not be approved. Our team will review the next steps.")
    else:
        req.status="PENDING_CUSTOMER_INFO"
        notify(db,req,"APPROVAL_RETURNED","Additional information is required to continue your request.")
    db.commit()
    return {"approval_id":approval.id,"decision":approval.decision,"request_status":req.status}

@app.post(API_PREFIX + "/requests/{request_id}/confirm-action")
def confirm_action(request_id: str, body: ConfirmAction, db: Session=Depends(get_db),
                   actor=Depends(require_roles("OPERATIONS_EXECUTIVE","OPERATIONS_SUPERVISOR","CENTRAL_OPERATIONS"))):
    req=db.get(ServiceRequest,request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor,req)
    if not req.approval_required or req.approval_status!="APPROVED":
        raise HTTPException(403,"A valid approval is required before recording this simulated action")
    if req.owner_id==actor.id and actor.role=="AUTHORISED_APPROVER":
        raise HTTPException(403,"Approver cannot execute their own approved action")
    req.action_executed=True
    audit(db,actor,"SIMULATED_FINANCIAL_ACTION_CONFIRMED",req.id,None,
          {"action_type":req.action_type,"processing_reference":body.processing_reference,"confirmation":body.confirmation},
          "POC simulation only; no banking transaction executed")
    db.commit()
    return {"request_id":req.id,"simulated_action_confirmed":True,"production_execution":False}

@app.post(API_PREFIX + "/requests/{request_id}/resolve")
def resolve(request_id: str, body: ResolveBody, db: Session=Depends(get_db),
            actor=Depends(require_roles("OPERATIONS_EXECUTIVE","OPERATIONS_SUPERVISOR","CENTRAL_OPERATIONS"))):
    req=db.get(ServiceRequest,request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor,req)
    if req.approval_required and req.approval_status!="APPROVED":
        raise HTTPException(409,"Required approval is not approved")
    if req.approval_required and not req.action_executed:
        raise HTTPException(409,"Simulated processing confirmation is required")
    if not req.identity_verified:
        raise HTTPException(409,"Identity verification must be confirmed by authorised staff")
    if not db.scalar(select(Investigation).where(Investigation.request_id==req.id)):
        raise HTTPException(409,"Investigation evidence is required before resolution")
    req.resolution_notes=body.notes; req.resolution_evidence=body.evidence
    set_status(db,actor,req,"RESOLVED","Verified outcome recorded")
    db.commit()
    return serialize_request(req)

@app.post(API_PREFIX + "/requests/{request_id}/close")
def close(request_id: str, db: Session=Depends(get_db),
          actor=Depends(require_roles("OPERATIONS_EXECUTIVE","OPERATIONS_SUPERVISOR","CENTRAL_OPERATIONS"))):
    req=db.get(ServiceRequest,request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor,req)
    if req.status!="RESOLVED" or not req.resolution_evidence:
        raise HTTPException(409,"Only resolved requests with verified evidence can be closed")
    set_status(db,actor,req,"CLOSED","Closure checks passed")
    audit(db,actor,"REQUEST_CLOSED",req.id,None,{"closed_at":str(req.closed_at)})
    notify(db,req,"REQUEST_CLOSED","Your service request has been successfully closed.")
    db.commit()
    return serialize_request(req)

@app.get(API_PREFIX + "/requests/{request_id}/audit")
def request_audit(request_id: str, db: Session=Depends(get_db),
                  actor=Depends(require_roles("BRANCH_EMPLOYEE","OPERATIONS_EXECUTIVE","OPERATIONS_SUPERVISOR","AUTHORISED_APPROVER","CENTRAL_OPERATIONS","SYSTEM_ADMIN"))):
    req=db.get(ServiceRequest,request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor,req)
    rows=db.scalars(select(AuditEvent).where(AuditEvent.request_id==req.id).order_by(AuditEvent.created_at)).all()
    return [{"event_id":e.id,"actor_id":e.actor_id,"actor_role":e.actor_role,"action":e.action,
             "previous_value":e.previous_value,"new_value":e.new_value,"reason":e.reason,
             "timestamp":e.created_at,"previous_hash":e.previous_hash,"event_hash":e.event_hash} for e in rows]

@app.get(API_PREFIX + "/requests/{request_id}/notifications")
def request_notifications(request_id: str, db: Session=Depends(get_db), actor=Depends(current_user)):
    req=db.get(ServiceRequest,request_id)
    if not req: raise HTTPException(404,"Request not found")
    require_request_scope(actor,req)
    q=select(Notification).where(Notification.request_id==req.id)
    if actor.role=="CUSTOMER": q=q.where(Notification.audience=="CUSTOMER")
    return [{"notification_id":n.id,"trigger":n.trigger_type,"channel":n.channel,"audience":n.audience,
             "message":n.message,"status":n.delivery_status,"created_at":n.created_at}
            for n in db.scalars(q.order_by(Notification.created_at.desc())).all()]

@app.post(API_PREFIX + "/escalations/{escalation_id}/acknowledge")
def acknowledge(escalation_id: str, db: Session=Depends(get_db),
                actor=Depends(require_roles("OPERATIONS_SUPERVISOR","CENTRAL_OPERATIONS","SERVICE_MANAGER"))):
    esc=db.get(Escalation,escalation_id)
    if not esc: raise HTTPException(404,"Escalation not found")
    esc.acknowledged=True; esc.acknowledged_by=actor.id; esc.acknowledged_at=now_utc()
    audit(db,actor,"ESCALATION_ACKNOWLEDGED",esc.request_id,None,{"escalation_id":esc.id})
    db.commit()
    return {"acknowledged":True}

@app.post(API_PREFIX + "/escalations/{escalation_id}/action")
def escalation_action(escalation_id: str, body: EscalationAction, db: Session=Depends(get_db),
                      actor=Depends(require_roles("OPERATIONS_SUPERVISOR","CENTRAL_OPERATIONS","SERVICE_MANAGER"))):
    esc=db.get(Escalation,escalation_id)
    if not esc: raise HTTPException(404,"Escalation not found")
    esc.delay_reason=body.delay_reason; esc.action_plan=body.action_plan
    audit(db,actor,"ESCALATION_ACTION_RECORDED",esc.request_id,None,{"delay_reason":body.delay_reason,"action_plan":body.action_plan})
    db.commit()
    return {"updated":True}

@app.post(API_PREFIX + "/scheduler/run")
def scheduler_run(db: Session=Depends(get_db), actor=Depends(require_roles("OPERATIONS_SUPERVISOR","SYSTEM_ADMIN"))):
    return run_sla_monitor(db,actor)

@app.get(API_PREFIX + "/dashboard/summary")
def dashboard(db: Session=Depends(get_db), actor=Depends(current_user)):
    reqs=db.scalars(select(ServiceRequest)).all()
    if actor.role=="CUSTOMER":
        reqs=[r for r in reqs if r.customer_ref=="CUST-001"]
    total=len(reqs); open_cases=[r for r in reqs if r.status not in {"CLOSED","RESOLVED"}]
    now=now_utc()
    overdue=sum(1 for r in open_cases if (r.current_sla_deadline.replace(tzinfo=timezone.utc) if getattr(r.current_sla_deadline, 'tzinfo', None) is None else r.current_sla_deadline) < now)
    pending=sum(1 for r in reqs if r.approval_status=="PENDING")
    return {"total_requests":total,"open_requests":len(open_cases),"overdue":overdue,
            "pending_approvals":pending,"closed":sum(1 for r in reqs if r.status=="CLOSED"),
            "by_status":{s:sum(1 for r in reqs if r.status==s) for s in sorted({r.status for r in reqs})},
            "by_type":{t:sum(1 for r in reqs if r.request_type==t) for t in sorted({r.request_type for r in reqs})}}
