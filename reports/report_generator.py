def generate_summary(scan):
    return {"scan_id": scan["id"], "filename": scan["filename"], "risk_score": scan["risk_score"], "risk_level": scan["risk_level"], "total_findings": scan["total_findings"], "recommendations": scan.get("recommendations", [])}
