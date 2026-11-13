from datetime import timedelta
from sqlalchemy.orm import Session
from app.db import init_db, SessionLocal, User, ServiceRequest, now_utc
from app.workflow import audit, notify
from uuid import uuid4

USERS = [
 ("customer_001","CUSTOMER","CUSTOMER","BRANCH-001"),
 ("branch_001","BRANCH_EMPLOYEE","BRANCH_OPERATIONS","BRANCH-001"),
 ("ops_001","OPERATIONS_EXECUTIVE","PAYMENTS_OPERATIONS","BRANCH-001"),
 ("supervisor_001","OPERATIONS_SUPERVISOR","ALL","BRANCH-001"),
 ("approver_001","AUTHORISED_APPROVER","APPROVALS","BRANCH-001"),
 ("central_001","CENTRAL_OPERATIONS","CENTRAL_OPERATIONS","CENTRAL"),
 ("manager_001","SERVICE_MANAGER","MANAGEMENT","ALL"),
 ("admin_001","SYSTEM_ADMIN","IT_ADMIN","ALL")
]
def seed():
    init_db()
    db = SessionLocal()
    try:
        for uid, role, team, branch in USERS:
            if not db.get(User, uid):
                db.add(User(id=uid, username=uid, role=role, team=team, branch=branch))
        db.commit()
        if db.query(ServiceRequest).count() == 0:
            now = now_utc()
            examples = [
              ("customer_001","MOBILE_APP","TRANSACTION_DISCREPANCY","UPI debit of INR 2500 but beneficiary not credited.","UPI_DEBIT_BENEFICIARY_NOT_CREDITED","P2","PAYMENTS_OPERATIONS","ops_001",48),
              ("customer_001","BRANCH","BANK_STATEMENT","Need six months bank statement for visa application.","STATEMENT_REQUEST","P3","BRANCH_OPERATIONS","branch_001",72),
              ("customer_001","CONTACT_CENTRE","TRANSACTION_DISCREPANCY","ATM cash not dispensed but account was debited.","ATM_CASH_NOT_DISPENSED","P2","ATM_OPERATIONS","ops_001",24)
            ]
            for cust, channel, typ, msg, sub, pri, team, owner, hours in examples:
                req = ServiceRequest(id=str(uuid4()), customer_ref="CUST-001", channel=channel,
                    request_type=typ, subcategory=sub, message=msg, ai_summary=msg,
                    extracted_fields={}, ai_confidence=.65, ai_review_required=True,
                    priority=pri, assigned_team=team, owner_id=owner, status="IN_PROGRESS",
                    approval_status="NOT_REQUIRED", sla_hours=hours,
                    created_at=now-timedelta(hours=hours*.4),
                    original_sla_deadline=now+timedelta(hours=hours*.6),
                    current_sla_deadline=now+timedelta(hours=hours*.6))
                db.add(req); db.flush()
                notify(db, req, "REQUEST_RECEIVED", f"Your service request {req.id[:8]} has been received.")
                audit(db, db.get(User, "admin_001"), "SAMPLE_REQUEST_SEEDED", req.id, None, {"status":req.status})
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
