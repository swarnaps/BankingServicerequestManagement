"""
Demo UI Screenshot Capture
Walks through the full banking service request workflow via Streamlit UI
and captures a screenshot at each step.
"""
import time
import os
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8501"
OUT_DIR = r"C:\Team6\AI_Friday_Banking_Service_Request_Complete_Solution\ai_friday_banking_solution\demo_screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

def ss(page, name):
    path = os.path.join(OUT_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    print(f"  [screenshot] {name}.png")

def select_role(page, role_label):
    """Select a role from the Demo Identity dropdown in the sidebar."""
    # Wait for sidebar dropdown
    page.wait_for_selector("select, [data-testid='stSelectbox']", timeout=10000)
    # Try to find and click the selectbox
    selects = page.locator("[data-testid='stSelectbox']").first
    selects.click()
    time.sleep(0.5)
    # Find option containing role_label
    page.get_by_text(role_label, exact=False).first.click()
    time.sleep(1)
    print(f"  [role] switched to: {role_label}")

def click_nav(page, label):
    """Click a sidebar navigation item."""
    try:
        page.get_by_text(label, exact=False).first.click()
        time.sleep(1.5)
    except Exception as e:
        print(f"  [warn] could not click nav '{label}': {e}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    page = context.new_page()

    print("\n=== Step 1: Dashboard (default role) ===")
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    time.sleep(3)
    ss(page, "01_dashboard")

    print("\n=== Step 2: Switch to Customer and Create Request ===")
    select_role(page, "customer_001")
    time.sleep(1)
    click_nav(page, "Create request")
    ss(page, "02_create_request_form")

    # Fill in the form
    try:
        # Channel
        channel = page.locator("[data-testid='stSelectbox']").nth(1)
        channel.click(); time.sleep(0.4)
        page.get_by_text("MOBILE_APP", exact=False).first.click(); time.sleep(0.4)

        # Request type
        rtype = page.locator("[data-testid='stSelectbox']").nth(2)
        rtype.click(); time.sleep(0.4)
        page.get_by_text("TRANSACTION_DISCREPANCY", exact=False).first.click(); time.sleep(0.4)

        # Message
        page.locator("textarea").first.fill(
            "UPI payment of INR 2500 was debited but beneficiary has not received it."
        )
        time.sleep(0.5)

        # Approval required checkbox
        try:
            page.get_by_text("Requires Approval", exact=False).first.click()
            time.sleep(0.4)
        except Exception:
            pass

        ss(page, "03_create_request_filled")

        # Submit
        page.get_by_role("button", name="Submit").click()
        time.sleep(3)
        ss(page, "04_create_request_submitted")
        print("  [OK] Request submitted")
    except Exception as e:
        print(f"  [warn] form fill issue: {e}")
        ss(page, "03_create_request_error")

    print("\n=== Step 3: Switch to Branch Employee – Case Queue ===")
    select_role(page, "branch_001")
    click_nav(page, "Case queue")
    time.sleep(2)
    ss(page, "05_case_queue_branch")

    # Click first request
    try:
        page.locator("table tbody tr").first.click()
        time.sleep(2)
        ss(page, "06_request_detail_branch")
    except Exception:
        try:
            page.locator("[data-testid='stExpander']").first.click()
            time.sleep(1)
            ss(page, "06_request_detail_branch")
        except Exception as e:
            print(f"  [warn] could not open request: {e}")

    print("\n=== Step 4: Supervisor – Assign Request ===")
    select_role(page, "supervisor_001")
    click_nav(page, "Case actions")
    time.sleep(2)
    ss(page, "07_case_actions_supervisor")

    print("\n=== Step 5: Ops Executive – Investigation + Approval ===")
    select_role(page, "ops_001")
    click_nav(page, "Case queue")
    time.sleep(2)
    ss(page, "08_case_queue_ops")

    print("\n=== Step 6: Approver – Approvals Queue ===")
    select_role(page, "approver_001")
    click_nav(page, "Approvals")
    time.sleep(2)
    ss(page, "09_approvals_queue")

    print("\n=== Step 7: Supervisor – Audit Trail ===")
    select_role(page, "supervisor_001")
    click_nav(page, "Audit")
    time.sleep(2)
    ss(page, "10_audit_trail")

    print("\n=== Step 8: Final Dashboard ===")
    click_nav(page, "Case queue")
    time.sleep(2)
    ss(page, "11_final_dashboard")

    browser.close()

print(f"\n[DONE] Screenshots saved to: {OUT_DIR}")
print("Files:")
for f in sorted(os.listdir(OUT_DIR)):
    print(f"  {f}")
