def recommendations(findings, extraction_status):
    unreadable = extraction_status != "Complete"
    if findings:
        from app.services.scan_service import recommendations as base_recommendations
        result=base_recommendations(findings)
    elif unreadable:
        result=[]
    else:
        from app.services.scan_service import recommendations as base_recommendations
        result=base_recommendations(findings)
    if unreadable:
        result.insert(0, f"Extraction note: {extraction_status} Review the original file manually because some or all content could not be scanned.")
    return result
