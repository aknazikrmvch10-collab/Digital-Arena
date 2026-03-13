"""
services/icafe_service.py
=========================
iCafe Cloud Synchronization Service.

Fetches real-time session logs from iCafe Cloud API and stores them locally
in `icafe_sessions` table for later cross-comparison with Digital Arena bookings.

Sync is triggered:
  - Manually via admin API endpoint
  - Automatically every hour by a background task scheduler
"""
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import async_session_factory
from models import Club, IcafeSession
from utils.timezone import now_utc

logger = logging.getLogger(__name__)

ICAFE_BASE_URL = "https://api.icafecloud.com/api/v2"


# ─────────────────────────────────────────────────────────────────────────────
# Low-level API client
# ─────────────────────────────────────────────────────────────────────────────

async def _icafe_get(
    cafe_id: str,
    api_token: str,
    endpoint: str,
    params: Optional[Dict] = None,
) -> Any:
    """Low-level async GET wrapper for iCafe Cloud API."""
    url = f"{ICAFE_BASE_URL}/cafe/{cafe_id}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            return await resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# Fetch sessions from iCafe
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_icafe_sessions(
    cafe_id: str,
    api_token: str,
    since_hours: int = 25,
) -> List[Dict]:
    """
    Pulls session history from iCafe Cloud for the last `since_hours` hours.
    Returns a list of raw session dicts.
    """
    since_dt = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    params = {
        "start_date": since_dt.strftime("%Y-%m-%d"),
        "page": 1,
        "per_page": 500,
    }
    try:
        response = await _icafe_get(cafe_id, api_token, "sessions", params=params)
        sessions = response.get("data", [])
        logger.info(f"[iCafe] Fetched {len(sessions)} sessions for cafe_id={cafe_id}")
        return sessions
    except Exception as e:
        logger.error(f"[iCafe] Failed to fetch sessions for cafe_id={cafe_id}: {e}")
        return []


async def fetch_icafe_computers(cafe_id: str, api_token: str) -> List[Dict]:
    """Pulls current PC list from iCafe Cloud."""
    try:
        response = await _icafe_get(cafe_id, api_token, "pcs/action/getPcsList", params={"pc_console_type": 0})
        return response.get("data", [])
    except Exception as e:
        logger.error(f"[iCafe] Failed to fetch computers for cafe_id={cafe_id}: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Sync to local DB
# ─────────────────────────────────────────────────────────────────────────────

async def sync_club_sessions(club: Club, since_hours: int = 25) -> int:
    """
    Sync iCafe sessions for a single club to local DB.
    Returns the number of newly inserted sessions.
    """
    config = club.connection_config or {}
    cafe_id = config.get("cafe_id")
    api_token = config.get("api_token")

    if not cafe_id or not api_token:
        logger.warning(f"[iCafe Sync] Club {club.id} ({club.name}) missing cafe_id or api_token — skipping.")
        return 0

    raw_sessions = await fetch_icafe_sessions(cafe_id, api_token, since_hours=since_hours)
    if not raw_sessions:
        return 0

    inserted = 0
    async with async_session_factory() as db:
        # Load already-known session IDs to skip duplicates
        existing_ids_result = await db.execute(
            select(IcafeSession.icafe_session_id).where(IcafeSession.club_id == club.id)
        )
        existing_ids = {row[0] for row in existing_ids_result.fetchall()}

        for raw in raw_sessions:
            session_id = str(raw.get("id") or raw.get("session_id") or "")
            if not session_id or session_id in existing_ids:
                continue

            # Parse times — iCafe usually returns ISO strings
            def _parse_dt(val) -> Optional[datetime]:
                if not val:
                    return None
                try:
                    return datetime.fromisoformat(val.replace("Z", "+00:00"))
                except Exception:
                    return None

            start_time = _parse_dt(raw.get("start_time") or raw.get("start"))
            end_time = _parse_dt(raw.get("end_time") or raw.get("end"))

            if not start_time:
                continue  # skip malformed entries

            duration = raw.get("duration") or raw.get("duration_minutes")
            if not duration and end_time:
                duration = int((end_time - start_time).total_seconds() / 60)

            new_session = IcafeSession(
                club_id=club.id,
                icafe_session_id=session_id,
                icafe_pc_id=str(raw.get("pc_id") or raw.get("computer_id") or ""),
                icafe_pc_name=raw.get("pc_name") or raw.get("computer_name"),
                start_time=start_time,
                end_time=end_time,
                duration_minutes=int(duration) if duration else None,
                icafe_price=int(raw.get("price") or raw.get("amount") or 0),
                icafe_paid=int(raw.get("paid") or raw.get("paid_amount") or 0),
                raw_data=raw,
                synced_at=now_utc(),
            )
            db.add(new_session)
            existing_ids.add(session_id)
            inserted += 1

        await db.commit()

    logger.info(f"[iCafe Sync] Club {club.id} ({club.name}): inserted {inserted} new sessions.")
    return inserted


async def sync_all_icafe_clubs(since_hours: int = 25) -> Dict[int, int]:
    """
    Runs sync for ALL clubs that use the ICAFE driver.
    Returns a dict {club_id: inserted_count}.
    Called by the hourly background scheduler.
    """
    results: Dict[int, int] = {}
    async with async_session_factory() as db:
        result = await db.execute(select(Club).where(Club.driver_type == "ICAFE", Club.is_active == True))
        clubs = result.scalars().all()

    logger.info(f"[iCafe Sync] Syncing {len(clubs)} iCafe-connected clubs...")

    for club in clubs:
        try:
            count = await sync_club_sessions(club, since_hours=since_hours)
            results[club.id] = count
        except Exception as e:
            logger.error(f"[iCafe Sync] Error syncing club {club.id}: {e}")
            results[club.id] = -1  # -1 indicates error

    return results
