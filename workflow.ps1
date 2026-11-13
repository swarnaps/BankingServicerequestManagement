## End‑to‑end demo workflow (PowerShell)
# 1️⃣ Create a request that requires approval
$create = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/requests \
    -Headers @{ "Content-Type"="application/json"; "X-User-Id"="customer_001" } \
    -Body (@{ 
        customer_ref = "CUST-001";
        channel = "MOBILE_APP";
        request_type = "TRANSACTION_DISCREPANCY";
        message = "UPI payment of INR 2500 was debited but not received.";
        fields = @{};
        approval_required = $true 
    } | ConvertTo-Json -Depth 5)

$requestId = $create.request_id
Write-Host "Created request ID: $requestId"

# 2️⃣ Add an investigation (required before approval)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/requests/$requestId/investigation" \
    -Headers @{ "Content-Type"="application/json"; "X-User-Id"="ops_001" } \
    -Body (@{ 
        finding = "Customer provided screenshot of the failed UPI transaction.";
        evidence_reference = "screenshot-20231113-upipay.jpg" 
    } | ConvertTo-Json -Depth 5) | Out-Null
Write-Host "Investigation added."

# 3️⃣ Submit an approval (waiver)
$approval = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/requests/$requestId/submit-approval" \
    -Headers @{ "Content-Type"="application/json"; "X-User-Id"="ops_001" } \
    -Body (@{ 
        action_type = "WAIVER";
        amount = 500;
        currency = "INR";
        justification = "Customer was incorrectly charged; waive per POC policy." 
    } | ConvertTo-Json -Depth 5)

$approvalId = $approval.approval_id
Write-Host "Submitted approval ID: $approvalId"

# 4️⃣ Approver records decision (APPROVED)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/approvals/$approvalId/decision" \
    -Headers @{ "Content-Type"="application/json"; "X-User-Id"="approver_001" } \
    -Body (@{ 
        decision = "APPROVED";
        comments = "All checks passed; waiver approved." 
    } | ConvertTo-Json -Depth 5) | Out-Null
Write-Host "Approval decision recorded."

# 5️⃣ Resolve the request (record outcome)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/requests/$requestId/resolve" \
    -Headers @{ "Content-Type"="application/json"; "X-User-Id"="ops_001" } \
    -Body (@{ 
        notes = "Waiver executed; simulated refund of INR 500 sent to customer.";
        evidence = "simulated-refund-receipt-20231113" 
    } | ConvertTo-Json -Depth 5) | Out-Null
Write-Host "Request resolved."

# 6️⃣ Close the request
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/requests/$requestId/close" \
    -Headers @{ "X-User-Id"="supervisor_001" } | Out-Null
Write-Host "Request closed."

# 7️⃣ Retrieve the full audit trail
$audit = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/requests/$requestId/audit" \
    -Headers @{ "X-User-Id"="supervisor_001" }

Write-Host "--- Audit Trail ---"
$audit | ConvertTo-Json -Depth 5
