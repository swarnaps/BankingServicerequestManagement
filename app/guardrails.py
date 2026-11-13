import re
from fastapi import HTTPException

SENSITIVE = re.compile(r"\b(pin|cvv|cvc|otp|one.time.password|password)\b", re.I)
ACCOUNT = re.compile(r"\b\d{10,19}\b")
def sanitise_customer_text(text: str) -> str:
    if SENSITIVE.search(text):
        raise HTTPException(422, "Do not submit PIN, CVV, password or OTP. Remove sensitive authentication data.")
    # Mask long digit sequences before sending text to AI or storing the message.
    return ACCOUNT.sub(lambda m: "*" * (len(m.group(0))-4) + m.group(0)[-4:], text)

def assert_safe_ai_output(data: dict):
    allowed_types = {"BANK_STATEMENT", "TRANSACTION_DISCREPANCY"}
    allowed_priority = {"P1", "P2", "P3", "P4"}
    if data.get("request_type") not in allowed_types:
        raise ValueError("Invalid request_type")
    if data.get("recommended_priority") not in allowed_priority:
        raise ValueError("Invalid priority")
    if not isinstance(data.get("extracted_fields", {}), dict):
        raise ValueError("Invalid extracted_fields")
    # Model-generated transaction reference is never accepted as verified evidence.
    data["extracted_fields"].pop("verified_transaction_reference", None)
    return data

def assert_customer_safe_message(message: str):
    blocked = ["internal escalation", "approver comments", "internal note", "system prompt"]
    if any(x in message.lower() for x in blocked):
        raise HTTPException(422, "Customer message contains internal-only information")
    return message
