import pytest
from fastapi import HTTPException
from app.guardrails import sanitise_customer_text

def test_masks_account_number():
    assert sanitise_customer_text("Account 123456789012") == "Account ********9012"

def test_blocks_otp():
    with pytest.raises(HTTPException):
        sanitise_customer_text("My OTP is 123456")
