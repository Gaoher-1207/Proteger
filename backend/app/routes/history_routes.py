from fastapi import APIRouter
from app.database.database import connect
from app.services.scan_service import list_scans
router=APIRouter()
@router.get("/scans")
def history(): return list_scans()
@router.get("/dashboard")
def dashboard():
    rows=list_scans(); return {"total_scans":len(rows),"high_risk_scans":sum(x["risk_level"] in ("HIGH","CRITICAL") for x in rows),"findings":sum(x["total_findings"] for x in rows),"latest":rows[:5],"distribution":{k:sum(x["risk_level"]==k for x in rows) for k in ("LOW","MEDIUM","HIGH","CRITICAL")}}
