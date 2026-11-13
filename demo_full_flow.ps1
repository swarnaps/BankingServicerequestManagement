# ==============================================================
# AI Friday Banking - Full Demo Workflow
# Roles used (matching the UI Demo Identity dropdown):
#   customer_001   -> CUSTOMER
#   branch_001     -> BRANCH_EMPLOYEE
#   ops_001        -> OPERATIONS_EXECUTIVE
#   supervisor_001 -> OPERATIONS_SUPERVISOR
#   approver_001   -> AUTHORISED_APPROVER
#   central_001    -> CENTRAL_OPERATIONS
#   manager_001    -> SERVICE_MANAGER
#   admin_001      -> SYSTEM_ADMIN
# ==============================================================

$BASE = "http://127.0.0.1:8000/api/v1"

# --------------------------------------------------------------
# STEP 1 - CUSTOMER creates the service request
# --------------------------------------------------------------
Write-Host ""
Write-Host "[1/9] CUSTOMER - Creating service request..."
$create = Invoke-RestMethod -Method Post `
    -Uri "$BASE/requests" `
    -Headers @{ 'Content-Type'='application/json'; 'X-User-Id'='customer_001' } `
    -Body (ConvertTo-Json -Depth 5 @{
        customer_ref      = 'CUST-001'
        channel           = 'MOBILE_APP'
        request_type      = 'TRANSACTION_DISCREPANCY'
        message           = 'UPI payment of INR 2500 was debited but beneficiary has not received it.'
        fields            = @{}
        approval_required = $true
    })
$requestId = $create.request_id
Write-Host "   [OK] Request created  -> ID: $requestId  Status: $($create.status)"

# --------------------------------------------------------------
# STEP 2 - BRANCH EMPLOYEE reviews AI classification
# (sets identity_verified=true and confirms classification)
# --------------------------------------------------------------
Write-Host ""
Write-Host "[2/9] BRANCH EMPLOYEE - Reviewing AI classification and verifying identity..."
Invoke-RestMethod -Method Post `
    -Uri "$BASE/requests/$requestId/review-ai" `
    -Headers @{ 'Content-Type'='application/json'; 'X-User-Id'='branch_001' } `
    -Body (ConvertTo-Json -Depth 5 @{
        request_type      = 'TRANSACTION_DISCREPANCY'
        subcategory       = 'UPI_PAYMENT'
        priority          = 'P2'
        assigned_team     = 'PAYMENTS_OPERATIONS'
        identity_verified = $true
        corrected_summary = 'Customer reports UPI debit without credit to beneficiary. Identity verified by branch.'
    }) | Out-Null
Write-Host "   [OK] AI review confirmed + identity verified by branch_001"

# --------------------------------------------------------------
# STEP 3 - SUPERVISOR assigns request to Ops Executive
# --------------------------------------------------------------
Write-Host ""
Write-Host "[3/9] SUPERVISOR - Assigning request to ops_001..."
Invoke-RestMethod -Method Post `
    -Uri "$BASE/requests/$requestId/assign" `
    -Headers @{ 'Content-Type'='application/json'; 'X-User-Id'='supervisor_001' } `
    -Body (ConvertTo-Json -Depth 5 @{
        owner_id      = 'ops_001'
        assigned_team = 'PAYMENTS_OPERATIONS'
    }) | Out-Null
Write-Host "   [OK] Request assigned to ops_001"

# --------------------------------------------------------------
# STEP 4 - OPERATIONS EXECUTIVE adds investigation evidence
# --------------------------------------------------------------
Write-Host ""
Write-Host "[4/9] OPS EXECUTIVE - Adding investigation..."
Invoke-RestMethod -Method Post `
    -Uri "$BASE/requests/$requestId/investigation" `
    -Headers @{ 'Content-Type'='application/json'; 'X-User-Id'='ops_001' } `
    -Body (ConvertTo-Json -Depth 5 @{
        finding            = 'Transaction log confirms debit of INR 2500. Beneficiary bank rejected credit due to NEFT timeout. Waiver recommended.'
        evidence_reference = 'txn-log-20231113-UPI123456.pdf'
    }) | Out-Null
Write-Host "   [OK] Investigation evidence added"

# --------------------------------------------------------------
# STEP 5 - OPERATIONS EXECUTIVE submits approval (waiver)
# --------------------------------------------------------------
Write-Host ""
Write-Host "[5/9] OPS EXECUTIVE - Submitting waiver approval request..."
$approval = Invoke-RestMethod -Method Post `
    -Uri "$BASE/requests/$requestId/submit-approval" `
    -Headers @{ 'Content-Type'='application/json'; 'X-User-Id'='ops_001' } `
    -Body (ConvertTo-Json -Depth 5 @{
        action_type   = 'WAIVER'
        amount        = 500
        currency      = 'INR'
        justification = 'Customer incorrectly charged due to NEFT timeout. Waiver of INR 500 processing fee recommended per POC policy.'
    })
$approvalId = $approval.approval_id
Write-Host "   [OK] Waiver approval submitted -> Approval ID: $approvalId"

# --------------------------------------------------------------
# STEP 6 - AUTHORISED APPROVER decides on the waiver
# --------------------------------------------------------------
Write-Host ""
Write-Host "[6/9] AUTHORISED APPROVER - Recording approval decision..."
Invoke-RestMethod -Method Post `
    -Uri "$BASE/approvals/$approvalId/decision" `
    -Headers @{ 'Content-Type'='application/json'; 'X-User-Id'='approver_001' } `
    -Body (ConvertTo-Json -Depth 5 @{
        decision = 'APPROVED'
        comments = 'Evidence reviewed. Waiver of INR 500 approved. Refund to be processed within 2 business days.'
    }) | Out-Null
Write-Host "   [OK] Waiver APPROVED by approver_001"

# --------------------------------------------------------------
# STEP 7 - OPERATIONS EXECUTIVE confirms simulated financial action
# --------------------------------------------------------------
Write-Host ""
Write-Host "[7/9] OPS EXECUTIVE - Confirming simulated financial action..."
Invoke-RestMethod -Method Post `
    -Uri "$BASE/requests/$requestId/confirm-action" `
    -Headers @{ 'Content-Type'='application/json'; 'X-User-Id'='ops_001' } `
    -Body (ConvertTo-Json -Depth 5 @{
        processing_reference = 'WAIVER-SIM-20231113-001'
        confirmation         = 'CONFIRMED'
    }) | Out-Null
Write-Host "   [OK] Simulated waiver action confirmed (POC - no real transaction)"

# --------------------------------------------------------------
# STEP 8 - OPERATIONS EXECUTIVE resolves the request
# --------------------------------------------------------------
Write-Host ""
Write-Host "[8/9] OPS EXECUTIVE - Resolving the request..."
Invoke-RestMethod -Method Post `
    -Uri "$BASE/requests/$requestId/resolve" `
    -Headers @{ 'Content-Type'='application/json'; 'X-User-Id'='ops_001' } `
    -Body (ConvertTo-Json -Depth 5 @{
        notes    = 'INR 500 waiver processed. Customer notified. Beneficiary credit confirmed in next settlement cycle.'
        evidence = 'resolution-confirmation-WAIVER-SIM-20231113-001'
    }) | Out-Null
Write-Host "   [OK] Request RESOLVED by ops_001"

# --------------------------------------------------------------
# STEP 9 - SUPERVISOR closes the request
# --------------------------------------------------------------
Write-Host ""
Write-Host "[9/9] SUPERVISOR - Closing the request..."
Invoke-RestMethod -Method Post `
    -Uri "$BASE/requests/$requestId/close" `
    -Headers @{ 'X-User-Id'='supervisor_001' } | Out-Null
Write-Host "   [OK] Request CLOSED by supervisor_001"

# ==============================================================
# AUDIT - Any authorised staff can view audit trail
# ==============================================================
Write-Host ""
Write-Host "[AUDIT] SUPERVISOR - Fetching full audit trail..."
$audit = Invoke-RestMethod -Method Get `
    -Uri "$BASE/requests/$requestId/audit" `
    -Headers @{ 'X-User-Id'='supervisor_001' }

Write-Host ""
Write-Host "========== AUDIT TRAIL =========================================="
$audit | ForEach-Object {
    Write-Host ("  [{0}]  {1}  ->  {2}" -f $_.timestamp, $_.actor_id, $_.action)
}
Write-Host "================================================================="
Write-Host ""
Write-Host "[DONE] Full end-to-end flow completed for request: $requestId"
