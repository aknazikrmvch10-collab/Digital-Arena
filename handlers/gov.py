"""
handlers/gov.py
================
Government Analytics Portal API — Read-only, public statistics endpoint.

Provides aggregated, anonymized industry data for state monitoring authorities:
  - Ministry of Sports (Министерство Спорта)
  - Ministry of Information Technologies
  - State Tax Committee (ГНК / Soliq)
  - IT Park Uzbekistan

All endpoints are READ-ONLY and return AGGREGATED data only.
No personal user data is ever exposed.

Access: Protected by GOV_API_TOKEN env variable (set on Render).
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_factory
from models import Club, Computer, User, Booking, Payment

router = APIRouter(prefix="/gov", tags=["government"])
logger = logging.getLogger(__name__)

GOV_TOKEN = os.getenv("GOV_API_TOKEN", "digital-arena-gov-2026")


def _check_token(token: Optional[str]):
    """Simple token-based auth for the government read-only API."""
    if token != GOV_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid or missing Gov API token")


# ─────────────────────────────────────────────────────────────────────────────
# Main stats endpoint — the most important one
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_government_stats(
    x_gov_token: Optional[str] = Header(None, alias="X-Gov-Token"),
    token: Optional[str] = Query(None),  # Also allow ?token= for browser
):
    """
    Main government analytics endpoint.
    Returns comprehensive industry statistics.
    """
    _check_token(x_gov_token or token)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0)

    async with async_session_factory() as db:

        # 1. ── CLUBS ──────────────────────────────────────────────────────
        total_clubs = (await db.execute(select(func.count(Club.id)))).scalar() or 0
        active_clubs = (await db.execute(
            select(func.count(Club.id)).where(Club.is_active == True)
        )).scalar() or 0

        # 2. ── USERS / PLAYERS ────────────────────────────────────────────
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

        # Active players: users with a booking in last 30 days
        active_players_result = await db.execute(
            select(func.count(func.distinct(Booking.user_id))).where(
                Booking.start_time >= month_ago
            )
        )
        active_players = active_players_result.scalar() or 0

        # Active RIGHT NOW: bookings with ACTIVE status
        playing_now = (await db.execute(
            select(func.count(Booking.id)).where(Booking.status == "ACTIVE")
        )).scalar() or 0

        # New users today
        new_users_today = (await db.execute(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )).scalar() or 0

        # 3. ── BOOKINGS ───────────────────────────────────────────────────
        total_bookings = (await db.execute(select(func.count(Booking.id)))).scalar() or 0

        bookings_today = (await db.execute(
            select(func.count(Booking.id)).where(Booking.start_time >= today_start)
        )).scalar() or 0

        bookings_week = (await db.execute(
            select(func.count(Booking.id)).where(Booking.start_time >= week_ago)
        )).scalar() or 0

        bookings_month = (await db.execute(
            select(func.count(Booking.id)).where(Booking.start_time >= month_ago)
        )).scalar() or 0

        # Completed vs no-show
        completed = (await db.execute(
            select(func.count(Booking.id)).where(
                and_(Booking.status == "COMPLETED", Booking.start_time >= month_ago)
            )
        )).scalar() or 0

        no_show = (await db.execute(
            select(func.count(Booking.id)).where(
                and_(Booking.status == "NO_SHOW", Booking.start_time >= month_ago)
            )
        )).scalar() or 0

        # Average booking duration (minutes)
        avg_duration_result = await db.execute(
            select(func.avg(
                func.julianday(Booking.end_time) - func.julianday(Booking.start_time)
            )).where(Booking.start_time >= month_ago)
        )
        avg_duration_days = avg_duration_result.scalar()
        avg_duration_min = round(avg_duration_days * 24 * 60) if avg_duration_days else 0

        # 4. ── REVENUE ────────────────────────────────────────────────────
        # Total revenue from confirmed/completed bookings
        revenue_month = (await db.execute(
            select(func.sum(Booking.total_price)).where(
                and_(
                    Booking.start_time >= month_ago,
                    Booking.status.in_(["CONFIRMED", "ACTIVE", "COMPLETED"]),
                    Booking.total_price.isnot(None),
                )
            )
        )).scalar() or 0

        revenue_week = (await db.execute(
            select(func.sum(Booking.total_price)).where(
                and_(
                    Booking.start_time >= week_ago,
                    Booking.status.in_(["CONFIRMED", "ACTIVE", "COMPLETED"]),
                    Booking.total_price.isnot(None),
                )
            )
        )).scalar() or 0

        revenue_total = (await db.execute(
            select(func.sum(Booking.total_price)).where(
                and_(
                    Booking.status.in_(["CONFIRMED", "ACTIVE", "COMPLETED"]),
                    Booking.total_price.isnot(None),
                )
            )
        )).scalar() or 0

        avg_revenue_per_club = round(int(revenue_month) / active_clubs) if active_clubs else 0
        avg_check = round(int(revenue_month) / bookings_month) if bookings_month else 0

        # 5. ── PAYMENT METHODS ────────────────────────────────────────────
        # Based on provider field in payments table
        payment_methods_result = await db.execute(
            select(Payment.provider, func.count(Payment.id), func.sum(Payment.amount))
            .where(Payment.status == "paid")
            .group_by(Payment.provider)
        )
        payment_rows = payment_methods_result.fetchall()
        payment_methods = [
            {
                "provider": row[0],
                "label": {
                    "click": "Click",
                    "payme": "Payme",
                    "uzum": "Uzum Bank",
                    "balance": "Внутренний баланс",
                    "test": "Тестовая оплата",
                }.get(row[0], row[0]),
                "count": row[1],
                "total_uzs": int(row[2] or 0),
            }
            for row in payment_rows
        ]

        # 6. ── DAILY ACTIVITY (last 7 days) ───────────────────────────────
        daily_data = []
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            count = (await db.execute(
                select(func.count(Booking.id)).where(
                    and_(Booking.start_time >= day_start, Booking.start_time < day_end)
                )
            )).scalar() or 0
            rev = (await db.execute(
                select(func.sum(Booking.total_price)).where(
                    and_(
                        Booking.start_time >= day_start,
                        Booking.start_time < day_end,
                        Booking.total_price.isnot(None),
                    )
                )
            )).scalar() or 0
            daily_data.append({
                "date": day_start.strftime("%d.%m"),
                "bookings": count,
                "revenue_uzs": int(rev),
            })

        # 7. ── TOP CLUBS ───────────────────────────────────────────────────
        top_clubs_result = await db.execute(
            select(
                Club.name, Club.city,
                func.count(Booking.id).label("bookings"),
                func.sum(Booking.total_price).label("revenue"),
            )
            .join(Booking, Booking.club_id == Club.id)
            .where(Booking.start_time >= month_ago)
            .group_by(Club.id, Club.name, Club.city)
            .order_by(func.count(Booking.id).desc())
            .limit(10)
        )
        top_clubs = [
            {
                "name": row[0],
                "city": row[1],
                "bookings_month": row[2],
                "revenue_month_uzs": int(row[3] or 0),
            }
            for row in top_clubs_result.fetchall()
        ]

        # 8. ── HOUR DISTRIBUTION (peak hours) ─────────────────────────────
        hourly_result = await db.execute(
            select(
                func.strftime('%H', Booking.start_time).label("hour"),
                func.count(Booking.id).label("count"),
            )
            .where(Booking.start_time >= month_ago)
            .group_by(func.strftime('%H', Booking.start_time))
            .order_by("hour")
        )
        hourly = [
            {"hour": int(row[0]), "count": row[1]}
            for row in hourly_result.fetchall()
        ]

        # 9. ── CLUBS BY CITY ───────────────────────────────────────────────
        cities_result = await db.execute(
            select(Club.city, func.count(Club.id).label("count"))
            .where(Club.is_active == True)
            .group_by(Club.city)
            .order_by(func.count(Club.id).desc())
        )
        clubs_by_city = [
            {"city": row[0], "clubs": row[1]}
            for row in cities_result.fetchall()
        ]

    return {
        "generated_at": now.isoformat(),
        "period": "Last 30 days (bookings), all-time (totals)",

        # Clubs
        "clubs": {
            "total": total_clubs,
            "active": active_clubs,
            "by_city": clubs_by_city,
        },

        # Users / Players
        "players": {
            "total_registered": total_users,
            "active_last_30d": active_players,
            "playing_right_now": playing_now,
            "new_today": new_users_today,
        },

        # Bookings
        "bookings": {
            "total_all_time": total_bookings,
            "today": bookings_today,
            "this_week": bookings_week,
            "this_month": bookings_month,
            "completed_month": completed,
            "no_show_month": no_show,
            "avg_duration_minutes": avg_duration_min,
        },

        # Revenue (UZS)
        "revenue": {
            "total_all_time_uzs": int(revenue_total),
            "this_month_uzs": int(revenue_month),
            "this_week_uzs": int(revenue_week),
            "avg_per_club_month_uzs": avg_revenue_per_club,
            "avg_booking_check_uzs": avg_check,
        },

        # Payment methods
        "payment_methods": payment_methods,

        # Charts
        "daily_activity_7d": daily_data,
        "peak_hours": hourly,
        "top_clubs_by_bookings": top_clubs,
    }


@router.get("/health")
async def gov_health():
    """Health check — always public, no auth needed."""
    return {"status": "ok", "service": "Digital Arena Government API", "version": "1.0"}
