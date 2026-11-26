from fastapi import APIRouter
from app.database import get_sync_db
from app.analytics.metrics import (
    get_weekly_overview_metrics,
    get_deployment_health_metrics,
    get_resolution_tracking_metrics,
    get_security_scan_metrics
)
from app.analytics.patterns import detect_recurring_patterns

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/weekly")
def weekly_overview():
    db = get_sync_db()
    return get_weekly_overview_metrics(db)

@router.get("/patterns")
def recurring_patterns():
    patterns = detect_recurring_patterns()
    return {"patterns": patterns}

@router.get("/deployment")
def deployment_health():
    db = get_sync_db()
    return get_deployment_health_metrics(db)

@router.get("/resolution")
def resolution_tracking():
    db = get_sync_db()
    return get_resolution_tracking_metrics(db)

@router.get("/security")
def security_scan_results():
    db = get_sync_db()
    return get_security_scan_metrics(db)
