"""
services/icafe_audit_service.py
================================
iCafe Audit Service — Cross-comparison engine.

Compares three data sources to detect shadow economy activity:
  1. Digital Arena bookings (local DB)
  2. iCafe sessions (synced from iCafe Cloud)
  3. Payment records (local DB)

Produces AuditDiscrepancy records that can be exported as reports
for tax authorities (ГНК/Soliq) or club owners.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from database import async_session_factory
from models import (
    Booking, Club, IcafeSession, AuditDiscrepancy, Payment, User
)
from utils.timezone import now_utc

logger = logging.getLogger(__name__)

# Thresholds
PRICE_MISMATCH_THRESHOLD_PERCENT = 15   # > 15% price difference = discrepancy
DURATION_MISMATCH_THRESHOLD_MIN = 20    # > 20 min difference = discrepancy
SESSION_MATCH_WINDOW_MIN = 30           # Sessions within ±30 min of booking are a "match"


# ─────────────────────────────────────────────────────────────────────────────
# Matching logic
# ─────────────────────────────────────────────────────────────────────────────

def _times_overlap(
    s1_start: datetime, s1_end: Optional[datetime],
    s2_start: datetime, s2_end: Optional[datetime],
    window_min: int = SESSION_MATCH_WINDOW_MIN,
) -> bool:
    """Returns True if two sessions/bookings overlap (within a tolerance window)."""
    if not s1_end:
        s1_end = s1_start + timedelta(minutes=60)
    if not s2_end:
        s2_end = s2_start + timedelta(minutes=60)
    # Expand both windows by `window_min` for fuzzy matching
    delta = timedelta(minutes=window_min)
    return s1_start - delta < s2_end and s1_end + delta > s2_start


# ─────────────────────────────────────────────────────────────────────────────
# Core audit run
# ─────────────────────────────────────────────────────────────────────────────

async def run_audit_for_club(
    club_id: int,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict:
    """
    Runs full audit for a specific club.
    Returns summary dict with discrepancy counts and estimated shadow revenue.
    """
    if not date_from:
        date_from = datetime.now(timezone.utc) - timedelta(days=1)
    if not date_to:
        date_to = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        # 1. Load Digital Arena bookings for this club in the period
        da_bookings_result = await db.execute(
            select(Booking).where(
                and_(
                    Booking.club_id == club_id,
                    Booking.start_time >= date_from,
                    Booking.start_time <= date_to,
                    Booking.status.in_(["CONFIRMED", "ACTIVE", "COMPLETED"]),
                )
            )
        )
        da_bookings: List[Booking] = da_bookings_result.scalars().all()

        # 2. Load iCafe sessions for this club in the period
        icafe_sessions_result = await db.execute(
            select(IcafeSession).where(
                and_(
                    IcafeSession.club_id == club_id,
                    IcafeSession.start_time >= date_from - timedelta(minutes=SESSION_MATCH_WINDOW_MIN),
                    IcafeSession.start_time <= date_to + timedelta(minutes=SESSION_MATCH_WINDOW_MIN),
                )
            )
        )
        icafe_sessions: List[IcafeSession] = icafe_sessions_result.scalars().all()

        # Tracking: which sessions/bookings have been matched
        matched_icafe_ids: set = set()
        matched_booking_ids: set = set()
        new_discrepancies: List[AuditDiscrepancy] = []
        total_shadow: int = 0

        # ── Check A: iCafe sessions WITHOUT matching DA booking ──────────────
        for isession in icafe_sessions:
            matched = False
            for booking in da_bookings:
                if _times_overlap(
                    isession.start_time, isession.end_time,
                    booking.start_time, booking.end_time,
                ):
                    matched_icafe_ids.add(isession.id)
                    matched_booking_ids.add(booking.id)
                    matched = True
                    break

            if not matched:
                # iCafe had a real session but Digital Arena has NO booking for it
                shadow = isession.icafe_price or isession.icafe_paid or 0
                total_shadow += shadow
                desc = (
                    f"iCafe session {isession.icafe_session_id} on PC '{isession.icafe_pc_name}' "
                    f"({isession.start_time.strftime('%d.%m %H:%M')} — "
                    f"{isession.end_time.strftime('%H:%M') if isession.end_time else '?'}) "
                    f"has NO matching Digital Arena booking. "
                    f"Possible shadow revenue: {shadow:,} UZS."
                )
                disc = AuditDiscrepancy(
                    club_id=club_id,
                    discrepancy_type="UNREGISTERED_SESSION",
                    icafe_session_id=isession.id,
                    icafe_amount=shadow,
                    shadow_amount=shadow,
                    session_date=isession.start_time,
                    pc_name=isession.icafe_pc_name,
                    description=desc,
                    detected_at=now_utc(),
                )
                new_discrepancies.append(disc)

        # ── Check B: DA bookings WITHOUT matching iCafe session ──────────────
        for booking in da_bookings:
            if booking.id in matched_booking_ids:
                continue
            desc = (
                f"Digital Arena booking #{booking.id} on '{booking.computer_name}' "
                f"({booking.start_time.strftime('%d.%m %H:%M')}) has NO matching iCafe session. "
                f"The PC may have been used without software logging (manual bypass)."
            )
            disc = AuditDiscrepancy(
                club_id=club_id,
                discrepancy_type="BOOKING_NO_SESSION",
                booking_id=booking.id,
                da_amount=booking.total_price,
                session_date=booking.start_time,
                pc_name=booking.computer_name,
                description=desc,
                detected_at=now_utc(),
            )
            new_discrepancies.append(disc)

        # ── Check C: Price mismatches for matched pairs ───────────────────────
        for isession in icafe_sessions:
            if isession.id not in matched_icafe_ids:
                continue

            # Find the best matching booking again
            for booking in da_bookings:
                if booking.id not in matched_booking_ids:
                    continue
                if not _times_overlap(
                    isession.start_time, isession.end_time,
                    booking.start_time, booking.end_time,
                ):
                    continue

                da_price = booking.total_price or 0
                icafe_price = isession.icafe_price or 0

                if da_price > 0 and icafe_price > 0:
                    diff_pct = abs(da_price - icafe_price) / max(da_price, icafe_price) * 100
                    if diff_pct > PRICE_MISMATCH_THRESHOLD_PERCENT:
                        shadow = max(0, icafe_price - da_price)
                        total_shadow += shadow
                        desc = (
                            f"Price mismatch on '{booking.computer_name}' "
                            f"({booking.start_time.strftime('%d.%m %H:%M')}): "
                            f"DA shows {da_price:,} UZS, iCafe shows {icafe_price:,} UZS "
                            f"(difference: {diff_pct:.1f}%). Shadow: {shadow:,} UZS."
                        )
                        disc = AuditDiscrepancy(
                            club_id=club_id,
                            discrepancy_type="PAYMENT_MISMATCH",
                            booking_id=booking.id,
                            icafe_session_id=isession.id,
                            da_amount=da_price,
                            icafe_amount=icafe_price,
                            shadow_amount=shadow,
                            session_date=booking.start_time,
                            pc_name=booking.computer_name,
                            description=desc,
                            detected_at=now_utc(),
                        )
                        new_discrepancies.append(disc)
                break

        # ── Save all new discrepancy records ──────────────────────────────────
        for disc in new_discrepancies:
            db.add(disc)
        await db.commit()

    summary = {
        "club_id": club_id,
        "period_from": date_from.isoformat(),
        "period_to": date_to.isoformat(),
        "da_bookings_checked": len(da_bookings),
        "icafe_sessions_checked": len(icafe_sessions),
        "discrepancies_found": len(new_discrepancies),
        "unregistered_sessions": sum(1 for d in new_discrepancies if d.discrepancy_type == "UNREGISTERED_SESSION"),
        "payment_mismatches": sum(1 for d in new_discrepancies if d.discrepancy_type == "PAYMENT_MISMATCH"),
        "bookings_no_session": sum(1 for d in new_discrepancies if d.discrepancy_type == "BOOKING_NO_SESSION"),
        "total_shadow_revenue_uzs": total_shadow,
        "ran_at": now_utc().isoformat(),
    }
    logger.info(f"[Audit] Club {club_id}: {summary}")
    return summary


async def run_audit_all_clubs(days_back: int = 1) -> List[Dict]:
    """Run audit for all iCafe-connected clubs. Called by scheduler."""
    date_from = datetime.now(timezone.utc) - timedelta(days=days_back)
    date_to = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        result = await db.execute(
            select(Club).where(Club.driver_type == "ICAFE", Club.is_active == True)
        )
        clubs = result.scalars().all()

    all_summaries = []
    for club in clubs:
        try:
            summary = await run_audit_for_club(club.id, date_from, date_to)
            all_summaries.append(summary)
        except Exception as e:
            logger.error(f"[Audit] Error auditing club {club.id}: {e}")
    return all_summaries


# ─────────────────────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────────────────────

async def get_discrepancies_for_club(
    club_id: int,
    include_resolved: bool = False,
    limit: int = 100,
) -> List[Dict]:
    """Returns list of discrepancy dicts for frontend display or export."""
    async with async_session_factory() as db:
        query = select(AuditDiscrepancy).where(AuditDiscrepancy.club_id == club_id)
        if not include_resolved:
            query = query.where(AuditDiscrepancy.is_resolved == False)
        query = query.order_by(AuditDiscrepancy.detected_at.desc()).limit(limit)
        result = await db.execute(query)
        records = result.scalars().all()
    return [r.to_dict() for r in records]


async def get_audit_summary_stats(club_id: Optional[int] = None) -> Dict:
    """Returns aggregate stats for the audit dashboard."""
    async with async_session_factory() as db:
        base = select(AuditDiscrepancy)
        if club_id:
            base = base.where(AuditDiscrepancy.club_id == club_id)

        total_result = await db.execute(base.with_only_columns(func.count()))
        total = total_result.scalar() or 0

        shadow_result = await db.execute(
            base.with_only_columns(func.sum(AuditDiscrepancy.shadow_amount))
        )
        total_shadow = shadow_result.scalar() or 0

        unresolved_result = await db.execute(
            base.where(AuditDiscrepancy.is_resolved == False).with_only_columns(func.count())
        )
        unresolved = unresolved_result.scalar() or 0

        # Count by type
        by_type: Dict[str, int] = {}
        for dtype in ["UNREGISTERED_SESSION", "PAYMENT_MISMATCH", "BOOKING_NO_SESSION", "DURATION_MISMATCH"]:
            type_result = await db.execute(
                base.where(AuditDiscrepancy.discrepancy_type == dtype).with_only_columns(func.count())
            )
            by_type[dtype] = type_result.scalar() or 0

    return {
        "total_discrepancies": total,
        "unresolved": unresolved,
        "total_shadow_revenue_uzs": int(total_shadow),
        "by_type": by_type,
    }


async def resolve_discrepancy(discrepancy_id: int, note: str) -> bool:
    """Marks a discrepancy as resolved."""
    async with async_session_factory() as db:
        result = await db.execute(select(AuditDiscrepancy).where(AuditDiscrepancy.id == discrepancy_id))
        disc = result.scalars().first()
        if not disc:
            return False
        disc.is_resolved = True
        disc.resolved_at = now_utc()
        disc.resolution_note = note
        await db.commit()
    return True
