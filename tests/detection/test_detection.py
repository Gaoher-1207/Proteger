import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from detection.pii_detector import detect
from detection.risk_engine import assess

def test_detects_and_masks_email_phone_aadhaar_and_secrets():
    items=detect("test@example.com 9876543210 1234 5678 9012 API_KEY=fake_demo_key_123456789 password:examplepass")
    kinds={x["type"] for x in items}
    assert {"EMAIL","PHONE","AADHAAR_LIKE","API_KEY","PASSWORD_LIKE"} <= kinds
    assert all("test@example.com" != x["value"] for x in items)

def test_risk_is_capped_and_classified():
    findings=detect("API_KEY=fake_demo_key_123456789 SECRET_TOKEN=demo_token_12345678")*4
    result=assess(findings)
    assert result["risk_score"] <= 100
    assert result["risk_level"] in {"LOW","MEDIUM","HIGH","CRITICAL"}
