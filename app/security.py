from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db import get_db, User

ROLE = {
 "CUSTOMER", "BRANCH_EMPLOYEE", "OPERATIONS_EXECUTIVE", "OPERATIONS_SUPERVISOR",
 "AUTHORISED_APPROVER", "CENTRAL_OPERATIONS", "SERVICE_MANAGER", "SYSTEM_ADMIN"
}
def current_user(x_user_id: str = Header(..., alias="X-User-Id"), db: Session = Depends(get_db)):
    user = db.get(User, x_user_id)
    if not user or not user.active:
        raise HTTPException(401, "Unknown or inactive demo user")
    return user

def require_roles(*roles):
    def dep(user=Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Role is not authorised for this action")
        return user
    return dep

def can_view_request(user: User, req) -> bool:
    if user.role == "CUSTOMER":
        return req.customer_ref == user.id.replace("customer_", "CUST-").upper()
    if user.role in {"SYSTEM_ADMIN", "SERVICE_MANAGER"}:
        return True
    if user.role == "BRANCH_EMPLOYEE":
        return user.branch == "BRANCH-001"
    if user.role == "OPERATIONS_SUPERVISOR":
        return user.team in {req.assigned_team, "ALL"}
    if user.role == "CENTRAL_OPERATIONS":
        return req.assigned_team in {"CENTRAL_OPERATIONS", "PAYMENTS_OPERATIONS", "CARDS_OPERATIONS", "ATM_OPERATIONS"}
    if user.role == "OPERATIONS_EXECUTIVE":
        return req.owner_id == user.id or req.assigned_team == user.team
    if user.role == "AUTHORISED_APPROVER":
        return req.approval_required
    return False

def require_request_scope(user, req):
    if not can_view_request(user, req):
        raise HTTPException(404, "Request not found")
