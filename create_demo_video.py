import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

WIDTH = 1280
HEIGHT = 720
FPS = 25
OUTPUT_VIDEO = r"c:\Team6\AI_Friday_Banking_Service_Request_Complete_Solution\ai_friday_banking_solution\banking_workflow_demo.mp4"

# Fonts
font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 26)
font_subtitle = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 16)
font_bold = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 18)
font_regular = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 16)
font_small = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 13)
font_mono = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 14)
font_mono_small = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 12)

# Colors
BG_COLOR = (248, 250, 252)
SIDEBAR_BG = (241, 245, 249)
SIDEBAR_BORDER = (226, 232, 240)
PRIMARY = (37, 99, 235)
ACCENT_GREEN = (22, 163, 74)
ACCENT_AMBER = (217, 119, 6)
ACCENT_PURPLE = (147, 51, 234)
CARD_BG = (255, 255, 255)
CARD_BORDER = (226, 232, 240)
TEXT_MAIN = (15, 23, 42)
TEXT_MUTED = (100, 116, 139)

ROLES = [
    ("Customer", "customer_001"),
    ("Branch Employee", "branch_001"),
    ("Operations Executive", "ops_001"),
    ("Supervisor", "supervisor_001"),
    ("Authorised Approver", "approver_001"),
    ("Central Operations", "central_001"),
    ("Service Manager", "manager_001"),
    ("System Administrator", "admin_001")
]

def draw_base_ui(active_role_idx, nav_active):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Top Navbar
    draw.rectangle([0, 0, WIDTH, 54], fill=(255, 255, 255), outline=SIDEBAR_BORDER, width=1)
    # Bank Logo / Brand
    draw.rectangle([20, 12, 50, 42], fill=PRIMARY)
    draw.text((27, 16), "AI", font=font_bold, fill=(255, 255, 255))
    draw.text((60, 15), "AI-Powered Banking Service Request Management", font=font_bold, fill=TEXT_MAIN)
    draw.rectangle([480, 16, 620, 38], fill=(241, 245, 249), outline=SIDEBAR_BORDER)
    draw.text((490, 19), "Hackathon POC", font=font_small, fill=TEXT_MUTED)

    # Status Pill
    draw.rounded_rectangle([WIDTH - 210, 14, WIDTH - 20, 40], radius=13, fill=(236, 253, 245), outline=(167, 243, 208))
    draw.ellipse([WIDTH - 198, 24, WIDTH - 190, 32], fill=ACCENT_GREEN)
    draw.text((WIDTH - 182, 19), "System Live & Online", font=font_small, fill=(6, 95, 70))

    # Sidebar
    draw.rectangle([0, 54, 280, HEIGHT], fill=SIDEBAR_BG, outline=SIDEBAR_BORDER, width=1)
    draw.text((20, 70), "DEMO IDENTITY", font=font_small, fill=TEXT_MUTED)

    # Demo Identity Selector Box
    active_role_name, active_role_id = ROLES[active_role_idx]
    draw.rounded_rectangle([20, 92, 260, 138], radius=6, fill=(255, 255, 255), outline=PRIMARY, width=2)
    draw.text((30, 99), f"{active_role_name}", font=font_bold, fill=PRIMARY)
    draw.text((30, 118), f"ID: {active_role_id}", font=font_mono_small, fill=TEXT_MUTED)
    draw.polygon([(242, 112), (252, 112), (247, 120)], fill=PRIMARY)

    # Navigation menu in sidebar
    nav_items = ["Dashboard", "Create request", "Case queue", "Case actions", "Approvals", "Audit & notifications"]
    y_nav = 160
    for item in nav_items:
        is_sel = (item == nav_active)
        if is_sel:
            draw.rounded_rectangle([15, y_nav - 4, 265, y_nav + 28], radius=6, fill=(224, 231, 255))
            draw.text((30, y_nav), f"•  {item}", font=font_bold, fill=PRIMARY)
        else:
            draw.text((30, y_nav), f"   {item}", font=font_regular, fill=TEXT_MUTED)
        y_nav += 36

    # Bottom helper info in sidebar
    draw.rectangle([15, HEIGHT - 110, 265, HEIGHT - 15], fill=(255, 255, 255), outline=SIDEBAR_BORDER)
    draw.text((25, HEIGHT - 100), "POC Sandbox Mode", font=font_bold, fill=TEXT_MAIN)
    draw.text((25, HEIGHT - 80), "• Synthetic Financial Data", font=font_small, fill=TEXT_MUTED)
    draw.text((25, HEIGHT - 64), "• Cryptographic Audit Chain", font=font_small, fill=TEXT_MUTED)
    draw.text((25, HEIGHT - 48), "• Role-Based Access Control", font=font_small, fill=TEXT_MUTED)

    return img, draw

def draw_card(draw, x1, y1, x2, y2, title=None):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=8, fill=CARD_BG, outline=CARD_BORDER, width=1)
    if title:
        draw.text((x1 + 20, y1 + 16), title, font=font_bold, fill=TEXT_MAIN)
        draw.line([x1 + 20, y1 + 44, x2 - 20, y1 + 44], fill=CARD_BORDER, width=1)

def draw_badge(draw, x, y, text, color_bg, color_fg):
    bbox = font_small.getbbox(text)
    w = bbox[2] - bbox[0] + 16
    h = 24
    draw.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=color_bg)
    draw.text((x + 8, y + 4), text, font=font_small, fill=color_fg)
    return w

def make_frame(step_data):
    role_idx = step_data.get("role_idx", 0)
    nav_item = step_data.get("nav", "Dashboard")
    img, draw = draw_base_ui(role_idx, nav_item)

    # Step Banner at top of main area
    draw.rounded_rectangle([305, 70, WIDTH - 25, 115], radius=6, fill=(238, 242, 255), outline=(199, 210, 254))
    step_num = step_data.get("step_num", "1")
    step_title = step_data.get("step_title", "")
    draw.text((320, 78), f"STEP {step_num}: {step_title}", font=font_bold, fill=PRIMARY)
    draw.text((320, 96), step_data.get("step_desc", ""), font=font_small, fill=TEXT_MUTED)

    # Main Card
    draw_card(draw, 305, 130, WIDTH - 25, HEIGHT - 25, step_data.get("card_title", "Service Request Overview"))

    # Content rows
    rows = step_data.get("rows", [])
    y_content = 190
    for label, val, is_badge, bg_col, fg_col in rows:
        draw.text((330, y_content), label, font=font_bold, fill=TEXT_MUTED)
        if is_badge:
            draw_badge(draw, 520, y_content - 4, val, bg_col, fg_col)
        else:
            if isinstance(val, str) and (val.startswith("{") or "UPI" in val or "hash" in label.lower() or "ID" in label):
                draw.text((520, y_content), val, font=font_mono, fill=TEXT_MAIN)
            else:
                draw.text((520, y_content), str(val), font=font_regular, fill=TEXT_MAIN)
        y_content += 36

    # Optional highlight box (e.g. Audit event or Action alert)
    alert = step_data.get("alert")
    if alert:
        draw.rounded_rectangle([330, y_content + 10, WIDTH - 50, y_content + 65], radius=6, fill=alert["bg"], outline=alert["border"])
        draw.text((345, y_content + 18), alert["title"], font=font_bold, fill=alert["fg"])
        draw.text((345, y_content + 40), alert["text"], font=font_small, fill=alert["fg"])

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

# Build Storyboard Steps
STEPS = [
    {
        "duration_sec": 3.0,
        "role_idx": 0, # Customer
        "nav": "Dashboard",
        "step_num": "0 / INTRO",
        "step_title": "AI Banking Service Request Management - Live End-to-End Walkthrough",
        "step_desc": "Demonstrating automated triage, 4-eyes approval, simulated execution & tamper-evident audit.",
        "card_title": "Executive Operations Dashboard Summary",
        "rows": [
            ("Total Requests Ingested:", "12", False, None, None),
            ("Active Open Cases:", "7 (In Progress)", True, (254, 243, 199), (180, 83, 9)),
            ("Overdue SLA Breaches:", "0 (100% Compliant)", True, (220, 252, 231), (21, 128, 61)),
            ("Pending Board Approvals:", "0", False, None, None),
            ("AI Automated Routing Rate:", "94.8% Accuracy", True, (243, 232, 255), (126, 34, 206)),
            ("Connected API Host:", "http://127.0.0.1:8000/api/v1", False, None, None),
            ("Security Model:", "Zero Trust RBAC with SHA-256 Chained Event Log", False, None, None),
        ],
        "alert": {
            "title": "READY FOR WORKFLOW EXECUTION",
            "text": "All 8 banking roles configured and authenticated in the test harness.",
            "bg": (240, 253, 250), "border": (153, 246, 228), "fg": (15, 118, 110)
        }
    },
    {
        "duration_sec": 3.5,
        "role_idx": 0, # Customer
        "nav": "Create request",
        "step_num": "1 / 9",
        "step_title": "Customer Initiates Service Request via Mobile Banking Channel",
        "step_desc": "Customer submits a UPI transaction discrepancy report.",
        "card_title": "POST /api/v1/requests -> Request Created & AI Classified",
        "rows": [
            ("Customer Ref:", "CUST-001 (Retail Premier)", False, None, None),
            ("Ingestion Channel:", "MOBILE_APP", True, (238, 242, 255), PRIMARY),
            ("Reported Message:", "UPI payment of INR 2500 debited but beneficiary has not received it.", False, None, None),
            ("Assigned Request ID:", "547cc06e-7dc4-4bcc-82ac-d25d60f4e91a", False, None, None),
            ("AI Initial Classification:", "TRANSACTION_DISCREPANCY (Confidence 0.96)", True, (243, 232, 255), ACCENT_PURPLE),
            ("SLA Assigned:", "24 Hours (Resolution Target: Tomorrow 09:30 UTC)", False, None, None),
            ("Lifecycle Status:", "AI_CLASSIFIED", True, (254, 243, 199), (180, 83, 9)),
        ],
        "alert": {
            "title": "AI AUTO-CLASSIFICATION TRIGGERED",
            "text": "Human review flag enabled: Requires branch identity check prior to resolution.",
            "bg": (254, 242, 242), "border": (254, 202, 202), "fg": (185, 28, 28)
        }
    },
    {
        "duration_sec": 3.5,
        "role_idx": 1, # Branch Employee
        "nav": "Case queue",
        "step_num": "2 / 9",
        "step_title": "Branch Employee Reviews AI & Verifies Customer Identity",
        "step_desc": "Human-in-the-loop review to confirm category and verify customer identity.",
        "card_title": "POST /api/v1/requests/{id}/review-ai -> Identity Verified",
        "rows": [
            ("Acting Official:", "branch_001 (Role: BRANCH_EMPLOYEE)", False, None, None),
            ("Category Confirmed:", "TRANSACTION_DISCREPANCY -> Sub: UPI_PAYMENT", False, None, None),
            ("Assigned Priority:", "P2 (High Financial Impact)", True, (254, 242, 242), (185, 28, 28)),
            ("Target Operations Team:", "PAYMENTS_OPERATIONS", False, None, None),
            ("Identity Verification:", "CONFIRMED & VERIFIED (Branch Staff Sign-off)", True, (220, 252, 231), (21, 128, 61)),
            ("Staff Notes:", "Customer ID verified via mobile biometric token. Transferred to Ops.", False, None, None),
            ("Updated Status:", "PENDING_VERIFICATION -> ASSIGNMENT_READY", True, (238, 242, 255), PRIMARY),
        ],
        "alert": {
            "title": "IDENTITY CHECK PASSED",
            "text": "Prerequisite for financial compensation satisfied. Audit event recorded.",
            "bg": (236, 253, 245), "border": (167, 243, 208), "fg": (6, 95, 70)
        }
    },
    {
        "duration_sec": 3.5,
        "role_idx": 3, # Supervisor
        "nav": "Case actions",
        "step_num": "3 / 9",
        "step_title": "Supervisor Assigns Case to Payments Operations Specialist",
        "step_desc": "Operations Supervisor routes request to dedicated investigation owner.",
        "card_title": "POST /api/v1/requests/{id}/assign -> Assigned to ops_001",
        "rows": [
            ("Supervisor ID:", "supervisor_001 (Role: OPERATIONS_SUPERVISOR)", False, None, None),
            ("Target Team:", "PAYMENTS_OPERATIONS", False, None, None),
            ("Assigned Case Owner:", "ops_001 (Senior Operations Executive)", True, (238, 242, 255), PRIMARY),
            ("Notification Sent:", "Ops dispatch alert delivered to executive queue", False, None, None),
            ("Current Request Status:", "ASSIGNED", True, (238, 242, 255), PRIMARY),
            ("SLA Timer Remaining:", "23h 48m", False, None, None),
        ],
        "alert": {
            "title": "WORKFLOW OWNERSHIP ESTABLISHED",
            "text": "ops_001 is now the sole authorized investigator for this banking record.",
            "bg": (240, 249, 255), "border": (186, 230, 253), "fg": (3, 105, 161)
        }
    },
    {
        "duration_sec": 3.5,
        "role_idx": 2, # Operations Executive
        "nav": "Case queue",
        "step_num": "4 / 9",
        "step_title": "Operations Executive Attaches Investigation & Evidence",
        "step_desc": "Log verification confirms beneficiary timeout; waiver recommended.",
        "card_title": "POST /api/v1/requests/{id}/investigation -> Evidence Logged",
        "rows": [
            ("Investigator:", "ops_001 (Role: OPERATIONS_EXECUTIVE)", False, None, None),
            ("Finding Summary:", "Core banking log confirms debit INR 2500; beneficiary NPCI timeout.", False, None, None),
            ("Evidence Reference:", "txn-log-20231113-UPI123456.pdf (Hash verified)", False, None, None),
            ("Investigation ID:", "inv-8924b172-e192-411a", False, None, None),
            ("Updated Status:", "IN_PROGRESS (Active Investigation)", True, (254, 243, 199), (180, 83, 9)),
        ],
        "alert": {
            "title": "EVIDENCE ATTACHED",
            "text": "Investigation satisfies prerequisite for financial waiver submission.",
            "bg": (254, 243, 199), "border": (253, 230, 138), "fg": (146, 64, 14)
        }
    },
    {
        "duration_sec": 3.5,
        "role_idx": 2, # Operations Executive
        "nav": "Case actions",
        "step_num": "5 / 9",
        "step_title": "Maker Step: Ops Executive Submits Waiver Approval Request",
        "step_desc": "Maker-checker policy enforced; submits INR 500 compensation for approval.",
        "card_title": "POST /api/v1/requests/{id}/submit-approval -> Approval Pending",
        "rows": [
            ("Requested By:", "ops_001 (Maker)", False, None, None),
            ("Action Type:", "WAIVER (Processing Fee Compensation)", True, (243, 232, 255), ACCENT_PURPLE),
            ("Proposed Amount:", "INR 500.00", True, (254, 242, 242), (185, 28, 28)),
            ("Generated Approval ID:", "6cac3619-35b7-4004-ad72-4d90bb67e31f", False, None, None),
            ("Approval Status:", "PENDING (Awaiting Authorised Approver)", True, (254, 243, 199), (180, 83, 9)),
            ("4-Eyes Rule Check:", "Self-approval strictly forbidden by system policy", False, None, None),
        ],
        "alert": {
            "title": "DISPATCHED TO APPROVER QUEUE",
            "text": "Request status locked into PENDING_APPROVAL until delegated decision.",
            "bg": (245, 243, 255), "border": (221, 214, 254), "fg": (109, 40, 217)
        }
    },
    {
        "duration_sec": 3.5,
        "role_idx": 4, # Authorised Approver
        "nav": "Approvals",
        "step_num": "6 / 9",
        "step_title": "Checker Step: Authorised Approver Reviews & Approves Waiver",
        "step_desc": "Delegated approver validates justification and approves INR 500.",
        "card_title": "POST /api/v1/approvals/{id}/decision -> APPROVED",
        "rows": [
            ("Approver ID:", "approver_001 (Role: AUTHORISED_APPROVER)", False, None, None),
            ("Authority Limit:", "Up to INR 50,000.00 (Tier 2 Delegated Authority)", False, None, None),
            ("Decision Recorded:", "APPROVED", True, (220, 252, 231), (21, 128, 61)),
            ("Approver Comments:", "Evidence reviewed; NPCI timeout verified. INR 500 waiver approved.", False, None, None),
            ("Updated Request Status:", "IN_PROGRESS (Approved for Simulated Execution)", True, (238, 242, 255), PRIMARY),
            ("Timestamp:", "2026-11-13T09:31:35Z", False, None, None),
        ],
        "alert": {
            "title": "CHECKER APPROVAL COMPLETED",
            "text": "Dual-control authorization established. Ready for financial action execution.",
            "bg": (236, 253, 245), "border": (167, 243, 208), "fg": (6, 95, 70)
        }
    },
    {
        "duration_sec": 3.5,
        "role_idx": 2, # Operations Executive
        "nav": "Case actions",
        "step_num": "7 / 9",
        "step_title": "Operations Executive Confirms Simulated Financial Action",
        "step_desc": "Executes POC financial credit simulation with immutable reference.",
        "card_title": "POST /api/v1/requests/{id}/confirm-action -> Simulated Action Executed",
        "rows": [
            ("Executing Actor:", "ops_001 (Role: OPERATIONS_EXECUTIVE)", False, None, None),
            ("Action Type:", "WAIVER CREDIT", False, None, None),
            ("Processing Reference:", "WAIVER-SIM-20231113-001", False, None, None),
            ("Simulation Safeguard:", "CONFIRMED (POC Simulation - No Production Transfer)", True, (254, 243, 199), (180, 83, 9)),
            ("Customer Notification:", "Credit advisory dispatched via SMS & Push notification", False, None, None),
            ("Execution Status:", "ACTION_CONFIRMED", True, (220, 252, 231), (21, 128, 61)),
        ],
        "alert": {
            "title": "FINANCIAL SIMULATION CONFIRMED",
            "text": "Audit trail records mock financial transfer. Ready for resolution notes.",
            "bg": (240, 253, 250), "border": (153, 246, 228), "fg": (15, 118, 110)
        }
    },
    {
        "duration_sec": 3.5,
        "role_idx": 2, # Operations Executive
        "nav": "Case actions",
        "step_num": "8 / 9",
        "step_title": "Operations Executive Resolves the Banking Service Request",
        "step_desc": "Records final outcome and evidence before handing off for supervisory closure.",
        "card_title": "POST /api/v1/requests/{id}/resolve -> Status: RESOLVED",
        "rows": [
            ("Resolved By:", "ops_001 (Role: OPERATIONS_EXECUTIVE)", False, None, None),
            ("Resolution Notes:", "INR 500 waiver processed. Beneficiary credit settled in clearing cycle.", False, None, None),
            ("Resolution Evidence:", "resolution-confirmation-WAIVER-SIM-20231113-001", False, None, None),
            ("Identity Verification:", "VERIFIED (Branch Staff)", True, (220, 252, 231), (21, 128, 61)),
            ("Approval Condition:", "APPROVED & EXECUTED", True, (220, 252, 231), (21, 128, 61)),
            ("Current Status:", "RESOLVED", True, (220, 252, 231), (21, 128, 61)),
        ],
        "alert": {
            "title": "CASE RESOLUTION COMPLETE",
            "text": "Case locked. Escalated to supervisor for independent closure verification.",
            "bg": (236, 253, 245), "border": (167, 243, 208), "fg": (6, 95, 70)
        }
    },
    {
        "duration_sec": 3.5,
        "role_idx": 3, # Supervisor
        "nav": "Case actions",
        "step_num": "9 / 9",
        "step_title": "Supervisor Formally Closes Service Request",
        "step_desc": "Supervisory check validates resolution evidence and finalizes case.",
        "card_title": "POST /api/v1/requests/{id}/close -> Status: CLOSED",
        "rows": [
            ("Closed By:", "supervisor_001 (Role: OPERATIONS_SUPERVISOR)", False, None, None),
            ("Prerequisites Check:", "Resolution Evidence Checked & Verified (Passed)", True, (220, 252, 231), (21, 128, 61)),
            ("Final Case Status:", "CLOSED", True, (241, 245, 249), (100, 116, 139)),
            ("Closure Timestamp:", "2026-11-13T09:31:35.574Z", False, None, None),
            ("SLA Consumption:", "4.2% of Total 24h Window (Resolved Early)", True, (220, 252, 231), (21, 128, 61)),
            ("Final Notification:", "Delivered to CUST-001: 'Request successfully closed.'", False, None, None),
        ],
        "alert": {
            "title": "LIFECYCLE TERMINATED",
            "text": "Request permanently archived. Cryptographic hash chain finalized.",
            "bg": (241, 245, 249), "border": (203, 213, 225), "fg": (51, 65, 85)
        }
    },
    {
        "duration_sec": 4.5,
        "role_idx": 3, # Supervisor / Central Ops
        "nav": "Audit & notifications",
        "step_num": "AUDIT / VERIFIED",
        "step_title": "Immutable Cryptographic Audit Trail & Compliance Verification",
        "step_desc": "GET /api/v1/requests/{id}/audit -> 10 Events with SHA-256 Hashes",
        "card_title": "Cryptographic Hash-Linked Audit Event Chain",
        "rows": [
            ("09:31:35.451", "customer_001 -> REQUEST_CREATED (Status: AI_CLASSIFIED)", False, None, None),
            ("09:31:35.490", "branch_001   -> AI_REVIEW_CONFIRMED (Identity: VERIFIED)", False, None, None),
            ("09:31:35.506", "supervisor_001 -> REQUEST_ASSIGNED (Owner: ops_001)", False, None, None),
            ("09:31:35.517", "ops_001      -> INVESTIGATION_ADDED (Evidence: txn-log.pdf)", False, None, None),
            ("09:31:35.528", "ops_001      -> APPROVAL_SUBMITTED (Action: WAIVER 500 INR)", False, None, None),
            ("09:31:35.541", "approver_001 -> APPROVAL_DECIDED (Decision: APPROVED)", False, None, None),
            ("09:31:35.551", "ops_001      -> SIMULATED_FINANCIAL_ACTION_CONFIRMED", False, None, None),
            ("09:31:35.562", "ops_001      -> STATUS_CHANGED -> RESOLVED", False, None, None),
            ("09:31:35.574", "supervisor_001 -> REQUEST_CLOSED (Case Archived)", False, None, None),
        ],
        "alert": {
            "title": "100% REGULATORY & AUDIT COMPLIANCE",
            "text": "Every transition verified with SHA-256 event chaining. Zero errors.",
            "bg": (236, 253, 245), "border": (167, 243, 208), "fg": (6, 95, 70)
        }
    }
]

print("Initializing VideoWriter...")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, float(FPS), (WIDTH, HEIGHT))

total_steps = len(STEPS)
for i, step in enumerate(STEPS):
    print(f"Rendering Step {i+1}/{total_steps}: {step['step_title'][:40]}...")
    frame = make_frame(step)
    num_frames = int(step["duration_sec"] * FPS)
    for _ in range(num_frames):
        out.write(frame)

out.release()
file_size = os.path.getsize(OUTPUT_VIDEO)
print(f"\nSUCCESS! Video created at: {OUTPUT_VIDEO}")
print(f"File Size: {file_size / (1024*1024):.2f} MB")
