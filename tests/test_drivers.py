"""
Tests for the MockDriver (database-backed booking driver).
"""
import pytest
from datetime import timedelta


class TestMockDriver:
    """Test the MockDriver used for demos and standalone clubs."""

    async def _make_club_and_pc(self, db_session):
        """Helper: create a club with one computer."""
        from models import Club, Computer
        club = Club(name="Driver Club", city="Tashkent", address="Test",
                    driver_type="MOCK", is_active=True)
        db_session.add(club)
        await db_session.flush()

        pc = Computer(club_id=club.id, name="PC-DRV-1", zone="VIP",
                      price_per_hour=20000, is_active=True)
        db_session.add(pc)
        await db_session.flush()

        user_model = __import__("models").User
        user = user_model(tg_id=7777, full_name="Driver Tester")
        db_session.add(user)
        await db_session.commit()

        return club, pc, user

    async def test_get_computers(self, db_session):
        from drivers.mock import MockDriver
        club, pc, user = await self._make_club_and_pc(db_session)

        driver = MockDriver({"club_id": club.id})
        computers = await driver.get_computers()
        assert len(computers) >= 1
        assert any(c.name == "PC-DRV-1" for c in computers)

    async def test_get_club_zones(self, db_session):
        from drivers.mock import MockDriver
        club, pc, user = await self._make_club_and_pc(db_session)

        driver = MockDriver({"club_id": club.id})
        zones = await driver.get_club_zones()
        assert len(zones) >= 1
        assert zones[0].name == "VIP"

    async def test_check_availability_open_slot(self, db_session):
        from drivers.mock import MockDriver
        from utils.timezone import now_utc
        club, pc, user = await self._make_club_and_pc(db_session)

        driver = MockDriver({"club_id": club.id})
        start = now_utc() + timedelta(hours=5)
        available = await driver.check_availability(str(pc.id), start, 60)
        assert available is True

    async def test_reserve_pc_success(self, db_session):
        from drivers.mock import MockDriver
        from utils.timezone import now_utc
        club, pc, user = await self._make_club_and_pc(db_session)

        driver = MockDriver({"club_id": club.id})
        start = now_utc() + timedelta(hours=6)
        result = await driver.reserve_pc(str(pc.id), user.id, start, 60)
        assert result.success is True
        assert result.booking_id is not None

    async def test_reserve_pc_conflict(self, db_session):
        from drivers.mock import MockDriver
        from utils.timezone import now_utc
        club, pc, user = await self._make_club_and_pc(db_session)

        driver = MockDriver({"club_id": club.id})
        start = now_utc() + timedelta(hours=7)

        # First reservation should succeed
        r1 = await driver.reserve_pc(str(pc.id), user.id, start, 60)
        assert r1.success is True

        # Second reservation at same time should fail
        r2 = await driver.reserve_pc(str(pc.id), user.id, start, 60)
        assert r2.success is False

    async def test_reserve_pc_adjacent_no_conflict(self, db_session):
        from drivers.mock import MockDriver
        from utils.timezone import now_utc
        club, pc, user = await self._make_club_and_pc(db_session)

        driver = MockDriver({"club_id": club.id})
        start1 = now_utc() + timedelta(hours=8)
        start2 = now_utc() + timedelta(hours=9)

        r1 = await driver.reserve_pc(str(pc.id), user.id, start1, 60)
        assert r1.success is True

        # Adjacent timeslot — should NOT conflict
        r2 = await driver.reserve_pc(str(pc.id), user.id, start2, 60)
        assert r2.success is True
