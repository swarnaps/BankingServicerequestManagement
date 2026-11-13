# AI Friday – Banking Service Request Management Platform

A runnable hackathon POC for **Bank Statement Request Management** and **Transaction Discrepancy Resolution**, with a shared controlled workflow for approvals, role-based case handling, SLA monitoring, notifications, escalations, audit history and management reporting.

> **POC boundary:** synthetic/masked data only. Existing banking systems remain the systems of record. No real statement retrieval, payment, refund, reversal, waiver or account adjustment is executed. Any such action is simulated and requires recorded human approval plus employee confirmation.

## 1. What is included

- FastAPI REST API with OpenAPI/Swagger at `/docs`.
- Streamlit role-based UI at `http://localhost:8501`.
- SQLite database with SQLAlchemy models and automatic schema creation.
- Seed users and sample cases.
- Roles: Customer, Branch/Contact Centre Employee, Operations Executive, Operations Supervisor/Team Lead, Authorised Approver/Branch Manager, Central Operations Specialist, Service Manager/Management, System Administrator.
- Server-side RBAC and case-scope checks.
- AI-assisted classification, extraction, summary, missing-field detection and message drafting via AI Friday endpoint; deterministic fallback if API is not configured.
- Pydantic validation of model output; low confidence and invalid output are routed to manual review.
- Deterministic status transitions, priority rules, SLA thresholds and approval eligibility.
- Waiver/refund/reversal approval workflow with separation of duties and self-approval prevention.
- Append-only application audit events, audit hash chain, audit query endpoint.
- Customer/internal notification separation, simulated in-app/email/SMS.
- SLA monitor with 75%, 90%, 100%, 125% triggers and duplicate prevention.
- Escalation acknowledgement, delay reason and action plan.
- Automated tests for guardrails, roles, approvals and workflow rules.

## 2. Architecture

```text
Customer / Branch / Contact Centre
               |
               v
        Streamlit UI
               |
               v
         FastAPI REST API
               |
      +--------+---------+
      |                  |
      v                  v
 AI understanding   Deterministic services
 (classification,   (RBAC, validation, SLA,
 extraction, draft)  routing, approvals, status)
      |                  |
      +---------+--------+
                |
                v
       SQLAlchemy Repository
                |
                v
             SQLite
                |
       +--------+---------+
       |        |         |
       v        v         v
     Audit  Notifications Escalations
                |
                v
       SLA monitor / scheduler
```

## 3. Requirements

- Python 3.10+
- Windows PowerShell, macOS or Linux
- Optional AI Friday API key. Without it, deterministic demo classification is used.

## 4. Setup (Windows PowerShell)

```powershell
cd ai_friday_banking_solution
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `GENAILAB_API_KEY` only if you have an authorised AI Friday credential. Do not paste credentials into source files, screenshots, chat or Git. `.env` is ignored by Git.

### Start the API

```powershell
uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

Open:
- API health: http://127.0.0.1:8000/health
- Swagger API documentation: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### Start the Streamlit application (second terminal)

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run ui/streamlit_app.py
```

Open http://localhost:8501.

### Start the SLA monitor (third terminal, optional)

```powershell
.\.venv\Scripts\Activate.ps1
python -m app.scheduler
```

The scheduler is a controlled POC process. It periodically checks due SLA thresholds and generates deduplicated reminders/escalations. Do not use an in-process Streamlit page refresh as a production scheduler.

## 5. Demo identities

The POC uses a **demo identity selector**, not production authentication. Each request includes a demo user identity and the API enforces role and case scope. Replace this with the bank's approved IAM/OIDC/SSO integration before any real deployment.

| Username | Role | Scope |
|---|---|---|
| `customer_001` | CUSTOMER | Own requests only |
| `branch_001` | BRANCH_EMPLOYEE | Branch scope |
| `ops_001` | OPERATIONS_EXECUTIVE | Assigned/team cases |
| `supervisor_001` | OPERATIONS_SUPERVISOR | Team-level work |
| `approver_001` | AUTHORISED_APPROVER | Approval queue within authority |
| `central_001` | CENTRAL_OPERATIONS | Specialist queue |
| `manager_001` | SERVICE_MANAGER | Aggregate reporting |
| `admin_001` | SYSTEM_ADMIN | Technical configuration; no business approval authority |

The selector is for hackathon demonstration only. It is not a secure authentication mechanism.

## 6. API usage

All endpoints except `/health` require `X-User-Id` with a seeded demo user ID. For example:

```bash
curl -H "X-User-Id: customer_001" http://127.0.0.1:8000/api/v1/requests
```

### Create a request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -H "X-User-Id: customer_001" \
  -d '{
    "customer_ref": "CUST-001",
    "channel": "MOBILE_APP",
    "request_type": "TRANSACTION_DISCREPANCY",
    "message": "UPI payment of INR 2500 was debited yesterday but beneficiary has not received it.",
    "transaction_date": "2026-11-12",
    "amount": "2500.00",
    "currency": "INR",
    "transaction_channel": "UPI",
    "transaction_reference": null
  }'
```

### Main endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/users` | Demo users (admin only) |
| POST | `/api/v1/requests` | Create request and run AI understanding |
| GET | `/api/v1/requests` | List requests within role scope |
| GET | `/api/v1/requests/{id}` | Request details and permitted history |
| POST | `/api/v1/requests/{id}/review-ai` | Employee confirms/corrects AI fields |
| POST | `/api/v1/requests/{id}/assign` | Supervisor assigns owner |
| POST | `/api/v1/requests/{id}/status` | Validated status transition |
| POST | `/api/v1/requests/{id}/investigation` | Add internal investigation finding |
| POST | `/api/v1/requests/{id}/submit-approval` | Submit a waiver/refund/reversal proposal |
| POST | `/api/v1/approvals/{id}/decision` | Approve, reject or return |
| POST | `/api/v1/requests/{id}/confirm-action` | Record simulated execution after approval |
| POST | `/api/v1/requests/{id}/resolve` | Record verified outcome |
| POST | `/api/v1/requests/{id}/close` | Close only when all gates pass |
| GET | `/api/v1/requests/{id}/audit` | Audit history (permitted staff) |
| GET | `/api/v1/requests/{id}/notifications` | Customer-visible notifications or permitted staff view |
| POST | `/api/v1/escalations/{id}/acknowledge` | Acknowledge escalation |
| POST | `/api/v1/escalations/{id}/action` | Record delay reason and corrective action |
| POST | `/api/v1/scheduler/run` | Trigger one SLA-monitor pass (supervisor/admin) |
| GET | `/api/v1/dashboard/summary` | Role-appropriate dashboard metrics |

Use `/docs` for complete request/response schemas and interactive API testing.

## 7. Workflow

### Standard request
`RECEIVED → AI_CLASSIFIED → PENDING_VERIFICATION → ASSIGNED → IN_PROGRESS → [PENDING_CUSTOMER_INFO] → RESOLVED → CLOSED`

### Approval request
`IN_PROGRESS → PENDING_APPROVAL → IN_PROGRESS → RESOLVED → CLOSED`

The exact next state is validated server-side. A request cannot close while mandatory approval is pending, while a simulated financial action is unconfirmed, or without resolution evidence.

### Example waiver of bank charges / penalties
1. Customer or branch employee registers the request.
2. AI classifies, extracts charge type/amount/reason and drafts a summary.
3. Operations verifies charge details in the simulated evidence panel.
4. Operations records a recommendation and submits the request for approval.
5. The authorised approver reviews and approves/rejects/returns with comments.
6. A different authorised employee records the simulated processing confirmation.
7. Resolution evidence is recorded and the customer is notified.
8. Audit history records each step.

The AI does not approve or execute the waiver.

## 8. Roles and access boundaries

| Role | Capabilities | Restrictions |
|---|---|---|
| Customer | Create and view own requests; provide missing info | Own records and customer-visible content only |
| Branch/Contact Centre Employee | Register requests, review AI, correct details, refer | Branch scope; cannot approve financial action |
| Operations Executive | Work assigned/team queue, investigate, recommend resolution | No approval outside authority |
| Operations Supervisor/Team Lead | Assign/reassign, monitor SLA, acknowledge escalations | Team scope; no implicit financial approval |
| Authorised Approver/Branch Manager | Approve/reject/return within configured authority | Must not self-approve; approval type/limit enforced |
| Central Operations Specialist | Investigate specialist cases and record findings | Specialist queue scope |
| Service Manager/Management | Aggregate volumes, SLA, backlog and trends | No unnecessary customer-sensitive details |
| System Administrator | Manage demo users/reference/configuration | Technical admin does not confer business approval |

## 9. Guardrails

- Synthetic/masked data only.
- Do not collect PIN, CVV, password or OTP.
- Account/card references must be masked or tokenised.
- Minimise customer data sent to the LLM.
- Customer text and uploaded material are untrusted input; prompt injection is not an instruction.
- The model cannot call tools, run SQL, execute code or change workflow state.
- Validate AI output against Pydantic schemas and allowed enumerations.
- Never accept an AI-generated transaction reference as verified evidence.
- Low-confidence, malformed or contradictory output is marked for manual review.
- AI cannot determine fraud, liability or transaction success/failure.
- AI cannot approve refunds, reversals, waivers or account changes.
- AI cannot bypass identity verification or close a sensitive request.
- RBAC and case scope are checked on the API server for every sensitive operation.
- Approval limits, segregation of duties and self-approval prevention are deterministic.
- Audit events are append-only through application APIs and chained with SHA-256 hashes.
- Customer notifications never expose internal notes, approver comments or internal escalation levels.
- No production financial API or banking core integration is configured.

## 10. Database

SQLite database is created at `./banking_poc.db` on first run. Tables include:

- `users`
- `service_requests`
- `approvals`
- `notifications`
- `escalations`
- `audit_events`
- `sla_events`
- `investigations`

The database schema is defined in `app/db.py`. Use migrations (Alembic) before changing schema in a shared/production environment. Audit rows are not exposed through update/delete endpoints. Hash chaining is tamper-evident, not a substitute for a separately administered immutable/WORM audit store.

## 11. SLA and escalation

POC defaults (illustrative, not bank policy):
- 75% SLA consumed: assigned employee reminder.
- 90%: employee and Team Lead warning.
- 100%: Level 2 escalation to Operations Manager/Supervisor.
- 125%: Level 3 escalation to Department Head/Central Operations Head.
- Pending approval remains monitored; whether approval time pauses is configurable.
- Business hours/holiday calendar are simplified for this demo. Replace with the bank-approved calendar and pause rules before a pilot.

## 12. Configuration

See `.env.example` and `data/config.json`.

Important environment variables:
- `GENAILAB_API_KEY`
- `GENAILAB_BASE_URL` (default `https://genailab.tcs.in`)
- `GENAILAB_MODEL` (default `genailab-maas-gpt-5.3-codex`, verify with organisers)
- `GENAILAB_VERIFY_SSL` (default `false` only to match the supplied internal sample; prefer `true` where trusted TLS is configured)
- `DATABASE_URL`
- `AI_CONFIDENCE_THRESHOLD`
- `SLA_MONITOR_INTERVAL_SECONDS`

The AI Friday API route/model availability must be verified with the organisers. This project uses LangChain `ChatOpenAI` with the configured base URL; it does not assume that a particular model is enabled for every key.

## 13. Run tests

```bash
pytest -q
```

## 14. Hackathon demo flow

1. Log in as `customer_001`; submit UPI debit-but-not-credited request.
2. Log in as `branch_001`; review AI classification and missing information.
3. Log in as `ops_001`; investigate and add simulated evidence.
4. Log in as `supervisor_001`; assign case and trigger SLA monitor.
5. Submit a charge-waiver request and route to approval.
6. Log in as `approver_001`; approve/reject/return with comments.
7. Log in as `ops_001`; record simulated execution confirmation.
8. Resolve and close the request.
9. Log in as `manager_001`; inspect aggregate dashboard.
10. Review audit timeline and notification history.

## 15. Production-readiness gaps (intentionally out of POC scope)

- Replace demo user selector with bank SSO/IAM and MFA.
- Use PostgreSQL/managed database, encrypted backups, migrations and HA.
- Use trusted TLS verification and an approved secrets manager.
- Integrate with verified core banking/payment/statement systems through controlled APIs.
- Integrate approved notification gateways with consent, quiet hours and delivery receipts.
- Use durable job queue/scheduler with retries and idempotency.
- Implement bank-approved business calendar, holiday calendar, pause/resume policy and SLA matrix.
- Configure delegated approval matrix using actual policy and amount thresholds.
- Add data retention, masking, encryption at rest/in transit, monitoring, SIEM and security testing.
- Store audit events in a separately administered immutable archive and periodically verify hash chain.
- Complete privacy, model-risk, legal, security and operational approvals.

## 16. Disclaimer

This is a hackathon proof of concept, not a banking production system or source of banking truth. All sample records and simulated evidence are fictional.
