"""
handlers/audit.py
==================
FastAPI router for the iCafe Audit module.

Endpoints:
  POST /api/audit/sync/{club_id}            - Manually trigger iCafe sync
  POST /api/audit/run/{club_id}             - Run audit comparison for a club
  GET  /api/audit/discrepancies/{club_id}   - List discrepancies
  GET  /api/audit/stats                     - Aggregate audit stats (for dashboard)
  GET  /api/audit/stats/{club_id}           - Per-club stats
  POST /api/audit/resolve/{discrepancy_id}  - Mark discrepancy as resolved
  GET  /api/audit/export/{club_id}          - Export discrepancies as CSV

Access: Super-admins only (X-Admin-TG-ID header cross-checked against admins table).
"""
import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from database import async_session_factory
from models import Admin
from sqlalchemy import select
from services.icafe_service import sync_club_sessions, sync_all_icafe_clubs
from services.icafe_audit_service import (
    run_audit_for_club,
    run_audit_all_clubs,
    get_discrepancies_for_club,
    get_audit_summary_stats,
    resolve_discrepancy,
)

router = APIRouter(prefix="/audit", tags=["audit"])
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Auth helper
# ─────────────────────────────────────────────────────────────────────────────

async def _require_super_admin(tg_id_header: Optional[str]):
    if not tg_id_header:
        raise HTTPException(status_code=401, detail="X-Admin-TG-ID header required")
    try:
        tg_id = int(tg_id_header)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid TG ID")

    async with async_session_factory() as db:
        result = await db.execute(select(Admin).where(Admin.tg_id == tg_id))
        admin = result.scalars().first()
    # Super-admins have club_id = None
    if not admin or admin.club_id is not None:
        raise HTTPException(status_code=403, detail="Super-admin access required")
    return tg_id


# ─────────────────────────────────────────────────────────────────────────────
# Sync endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/sync/{club_id}")
async def sync_icafe_club(
    club_id: int,
    since_hours: int = Query(default=25, ge=1, le=720),
    x_admin_tg_id: Optional[str] = Header(None, alias="X-Admin-TG-ID"),
):
    """Manually pull new iCafe sessions for a specific club."""
    await _require_super_admin(x_admin_tg_id)

    async with async_session_factory() as db:
        from models import Club
        club = await db.get(Club, club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")
        if club.driver_type != "ICAFE":
            raise HTTPException(status_code=400, detail="Club is not using iCafe driver")

    count = await sync_club_sessions(club, since_hours=since_hours)
    return {"success": True, "club_id": club_id, "new_sessions_synced": count}


@router.post("/sync-all")
async def sync_all_clubs(
    since_hours: int = Query(default=25, ge=1, le=720),
    x_admin_tg_id: Optional[str] = Header(None, alias="X-Admin-TG-ID"),
):
    """Sync all iCafe-connected clubs at once."""
    await _require_super_admin(x_admin_tg_id)
    results = await sync_all_icafe_clubs(since_hours=since_hours)
    return {"success": True, "results": results}


# ─────────────────────────────────────────────────────────────────────────────
# Audit run endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/run/{club_id}")
async def run_audit(
    club_id: int,
    days_back: int = Query(default=1, ge=1, le=90),
    x_admin_tg_id: Optional[str] = Header(None, alias="X-Admin-TG-ID"),
):
    """Run audit comparison for a specific club."""
    await _require_super_admin(x_admin_tg_id)

    date_from = datetime.now(timezone.utc) - timedelta(days=days_back)
    date_to = datetime.now(timezone.utc)
    summary = await run_audit_for_club(club_id, date_from, date_to)
    return summary


@router.post("/run-all")
async def run_all_audits(
    days_back: int = Query(default=1, ge=1, le=30),
    x_admin_tg_id: Optional[str] = Header(None, alias="X-Admin-TG-ID"),
):
    """Run audit for all iCafe clubs."""
    await _require_super_admin(x_admin_tg_id)
    summaries = await run_audit_all_clubs(days_back=days_back)
    return {"results": summaries, "clubs_audited": len(summaries)}


# ─────────────────────────────────────────────────────────────────────────────
# Query endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def audit_global_stats(
    x_admin_tg_id: Optional[str] = Header(None, alias="X-Admin-TG-ID"),
):
    """Global audit statistics — used by the main admin dashboard."""
    await _require_super_admin(x_admin_tg_id)
    return await get_audit_summary_stats()


@router.get("/stats/{club_id}")
async def audit_club_stats(
    club_id: int,
    x_admin_tg_id: Optional[str] = Header(None, alias="X-Admin-TG-ID"),
):
    """Per-club audit statistics."""
    await _require_super_admin(x_admin_tg_id)
    return await get_audit_summary_stats(club_id=club_id)


@router.get("/discrepancies/{club_id}")
async def list_discrepancies(
    club_id: int,
    include_resolved: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    x_admin_tg_id: Optional[str] = Header(None, alias="X-Admin-TG-ID"),
):
    """List all audit discrepancies for a club."""
    await _require_super_admin(x_admin_tg_id)
    records = await get_discrepancies_for_club(club_id, include_resolved=include_resolved, limit=limit)
    return {"club_id": club_id, "total": len(records), "discrepancies": records}


# ─────────────────────────────────────────────────────────────────────────────
# Resolution endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/resolve/{discrepancy_id}")
async def resolve(
    discrepancy_id: int,
    note: str = Query(default="Resolved by admin"),
    x_admin_tg_id: Optional[str] = Header(None, alias="X-Admin-TG-ID"),
):
    """Mark a discrepancy as resolved (explained manually)."""
    await _require_super_admin(x_admin_tg_id)
    ok = await resolve_discrepancy(discrepancy_id, note=note)
    if not ok:
        raise HTTPException(status_code=404, detail="Discrepancy not found")
    return {"success": True, "discrepancy_id": discrepancy_id, "note": note}


# ─────────────────────────────────────────────────────────────────────────────
# CSV Export (for ГНК / Налоговый Комитет)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/export/{club_id}")
async def export_csv(
    club_id: int,
    include_resolved: bool = Query(default=False),
    x_admin_tg_id: Optional[str] = Header(None, alias="X-Admin-TG-ID"),
):
    """
    Export audit discrepancies as CSV for submission to tax authorities (ГНК).
    Returns a downloadable .csv file.
    """
    await _require_super_admin(x_admin_tg_id)

    records = await get_discrepancies_for_club(club_id, include_resolved=include_resolved, limit=10000)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "detected_at", "discrepancy_type", "pc_name",
        "session_date", "da_amount", "icafe_amount", "shadow_amount",
        "is_resolved", "description"
    ])
    writer.writeheader()
    for r in records:
        writer.writerow({
            "id": r.get("id"),
            "detected_at": r.get("detected_at", "")[:19],
            "discrepancy_type": r.get("discrepancy_type"),
            "pc_name": r.get("pc_name", ""),
            "session_date": (r.get("session_date") or "")[:19],
            "da_amount": r.get("da_amount", 0),
            "icafe_amount": r.get("icafe_amount", 0),
            "shadow_amount": r.get("shadow_amount", 0),
            "is_resolved": r.get("is_resolved"),
            "description": r.get("description", ""),
        })

    output.seek(0)
    filename = f"audit_club_{club_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
