from app.services.scan_service import recommendations

def build_report(scan):
    return {"scan_id": scan["id"], "risk_score": scan["risk_score"], "risk_level": scan["risk_level"], "recommendations": recommendations(scan["findings"])}
