import streamlit as st
import requests, pandas as pd
from datetime import date
API = "http://127.0.0.1:8000/api/v1"
USERS = {
 "Customer — customer_001":"customer_001",
 "Branch Employee — branch_001":"branch_001",
 "Operations Executive — ops_001":"ops_001",
 "Supervisor — supervisor_001":"supervisor_001",
 "Authorised Approver — approver_001":"approver_001",
 "Central Operations — central_001":"central_001",
 "Service Manager — manager_001":"manager_001",
 "System Administrator — admin_001":"admin_001"
}
st.set_page_config(page_title="AI Friday Banking Service Requests", layout="wide")
st.title("AI-Powered Banking Service Request Management")
st.caption("Hackathon POC • Synthetic data • No production financial actions")
choice=st.sidebar.selectbox("Demo identity",list(USERS))
uid=USERS[choice]
headers={"X-User-Id":uid}
def api(method,path,**kwargs):
    try:
        r=requests.request(method,API+path,headers=headers,timeout=30,**kwargs)
        if r.status_code>=400:
            st.error(f"{r.status_code}: {r.text}")
            return None
        return r.json() if r.content else {}
    except requests.RequestException as e:
        st.error(f"API unavailable: {e}")
        return None

summary=api("GET","/dashboard/summary")
if summary:
    cols=st.columns(5)
    for c,(label,key) in zip(cols,[("Total","total_requests"),("Open","open_requests"),("Overdue","overdue"),("Pending approval","pending_approvals"),("Closed","closed")]):
        c.metric(label,summary.get(key,0))
tabs=st.tabs(["Create request","Case queue","Case actions","Approvals","Audit & notifications"])
with tabs[0]:
    st.subheader("Register a banking service request")
    with st.form("new_request"):
        customer_ref=st.text_input("Customer reference", "CUST-001")
        channel=st.selectbox("Channel",["MOBILE_APP","BRANCH","CONTACT_CENTRE"])
        typ=st.selectbox("Request type",["TRANSACTION_DISCREPANCY","BANK_STATEMENT"])
        msg=st.text_area("Customer message", "UPI payment of INR 2500 was debited but beneficiary has not received it.")
        submitted=st.form_submit_button("Submit and analyse")
    if submitted:
        out=api("POST","/requests",json={"customer_ref":customer_ref,"channel":channel,"request_type":typ,"message":msg,"fields":{}})
        if out:
            st.success(f"Created request {out['request_id']}")
            st.json(out["ai_analysis"])
with tabs[1]:
    st.subheader("Requests in your permitted scope")
    rows=api("GET","/requests") or []
    if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True)
    else: st.info("No requests in this role's scope.")
with tabs[2]:
    rows=api("GET","/requests") or []
    if rows:
        rid=st.selectbox("Select request", [r["request_id"] for r in rows])
        detail=api("GET",f"/requests/{rid}")
        if detail: st.json(detail)
        if uid in {"branch_001","ops_001","supervisor_001","central_001"}:
            with st.form("review"):
                priority=st.selectbox("Confirm priority",["P1","P2","P3","P4"])
                team=st.text_input("Assigned team",detail.get("assigned_team","PAYMENTS_OPERATIONS") if detail else "PAYMENTS_OPERATIONS")
                verified=st.checkbox("Identity verified in approved process")
                review=st.form_submit_button("Confirm AI review")
            if review:
                api("POST",f"/requests/{rid}/review-ai",json={"request_type":detail["request_type"],"subcategory":detail["subcategory"],
                   "priority":priority,"assigned_team":team,"identity_verified":verified})
                st.rerun()
            with st.form("investigation"):
                finding=st.text_area("Investigation finding")
                evidence=st.text_input("Evidence reference (synthetic)")
                inv=st.form_submit_button("Add investigation")
            if inv:
                api("POST",f"/requests/{rid}/investigation",json={"finding":finding,"evidence_reference":evidence})
            with st.form("resolve"):
                notes=st.text_area("Resolution notes")
                proof=st.text_input("Verified resolution evidence")
                resolved=st.form_submit_button("Resolve case")
            if resolved:
                api("POST",f"/requests/{rid}/resolve",json={"notes":notes,"evidence":proof})
with tabs[3]:
    st.subheader("Approval workflow")
    if uid=="ops_001" or uid=="central_001":
        rows=api("GET","/requests") or []
        if rows:
            rid=st.selectbox("Request for approval", [r["request_id"] for r in rows],key="approval_req")
            with st.form("submit_approval"):
                action=st.selectbox("Action",["WAIVER","REFUND","REVERSAL"])
                amount=st.number_input("Amount (INR)",min_value=1.0,max_value=100000.0,value=500.0)
                why=st.text_area("Business justification","Verified charge details; waiver recommended under POC policy.")
                go=st.form_submit_button("Submit for approval")
            if go:
                api("POST",f"/requests/{rid}/submit-approval",json={"action_type":action,"amount":amount,"currency":"INR","justification":why})
    if uid=="approver_001":
        # Approval IDs are exposed in the database via this demo helper endpoint in future extension;
        # show explicit instruction instead of fabricating an approval identifier.
        st.info("Use the approval_id returned by POST /requests/{id}/submit-approval in Swagger /docs to decide an approval.")
        approval_id=st.text_input("Approval ID")
        decision=st.selectbox("Decision",["APPROVED","REJECTED","RETURNED"])
        comments=st.text_area("Decision comments")
        if st.button("Record decision"):
            api("POST",f"/approvals/{approval_id}/decision",json={"decision":decision,"comments":comments})
with tabs[4]:
    st.subheader("Audit and notification history")
    rows=api("GET","/requests") or []
    if rows:
        rid=st.selectbox("Request", [r["request_id"] for r in rows],key="audit_req")
        if uid!="customer_001":
            if st.button("Load audit trail"):
                st.json(api("GET",f"/requests/{rid}/audit"))
        if st.button("Load notifications"):
            st.json(api("GET",f"/requests/{rid}/notifications"))
    if uid in {"supervisor_001","admin_001"} and st.button("Run SLA monitor now"):
        st.json(api("POST","/scheduler/run"))
