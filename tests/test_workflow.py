from app.workflow import TRANSITIONS

def test_close_only_after_resolved():
    assert "CLOSED" not in TRANSITIONS["IN_PROGRESS"]
    assert "CLOSED" in TRANSITIONS["RESOLVED"]

def test_pending_approval_returns_to_in_progress():
    assert TRANSITIONS["PENDING_APPROVAL"] == {"IN_PROGRESS"}
