"""
🧪 Автоматические тесты для API бронирования

Эти тесты проверяют:
1. ✅ Успешное создание брони
2. ❌ Двойное бронирование (должно блокироваться)
3. 🔒 БЕЗОПАСНОСТЬ: Попытка отменить чужую бронь (должна провалиться)

Как запустить:
    pytest tests/test_api_bookings.py -v
"""

import pytest
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
from main import fastapi_app
from database import init_db, async_session_factory
from models import User, Club, Computer, Booking
from sqlalchemy import select



@pytest.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Инициализация тестовой базы данных"""
    await init_db()
    
    # Создаем тестовых пользователей и клуб
    async with async_session_factory() as session:
        # Пользователь 1
        user1 = User(
            tg_id=111111,
            full_name="Test User 1",
            age_confirmed=True
        )
        session.add(user1)
        
        # Пользователь 2 (злоумышленник)
        user2 = User(
            tg_id=222222,
            full_name="Evil User",
            age_confirmed=True
        )
        session.add(user2)
        
        # Тестовый клуб
        club = Club(
            name="Test Club",
            city="Tashkent",
            address="Test St. 1",
            driver_type="MOCK"
        )
        session.add(club)
        await session.flush()
        
        # Компьютер
        computer = Computer(
            club_id=club.id,
            name="TEST-PC-1",
            zone="Test",
            price_per_hour=10000
        )
        session.add(computer)
        
        await session.commit()


@pytest.mark.asyncio
async def test_create_booking_success():
    """
    ✅ ТЕСТ 1: Успешное создание брони
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
        
        response = await client.post("/api/bookings", json={
            "user_id": 111111,
            "club_id": 1,
            "computer_id": "1",
            "start_time": tomorrow.isoformat(),
            "duration_minutes": 60
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "booking_id" in data
        
        print("✅ ТЕСТ ПРОЙДЕН: Бронь успешно создана")


@pytest.mark.asyncio
async def test_double_booking_blocked():
    """
    ❌ ТЕСТ 2: Попытка забронировать занятое время
    Должна вернуть ошибку
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
        
        # Первая бронь
        response1 = await client.post("/api/bookings", json={
            "user_id": 111111,
            "club_id": 1,
            "computer_id": "1",
            "start_time": tomorrow.isoformat(),
            "duration_minutes": 60
        })
        assert response1.status_code == 200
        
        # Попытка забронировать то же время
        response2 = await client.post("/api/bookings", json={
            "user_id": 222222,  # Другой пользователь
            "club_id": 1,
            "computer_id": "1",
            "start_time": tomorrow.isoformat(),
            "duration_minutes": 60
        })
        
        # Должна вернуть success: false
        data = response2.json()
        assert data["success"] is False
        assert "conflict" in data or "занят" in data.get("message", "").lower()
        
        print("✅ ТЕСТ ПРОЙДЕН: Двойное бронирование заблокировано")


@pytest.mark.asyncio
async def test_cancel_foreign_booking_blocked():
    """
    🔒 ТЕСТ 3: БЕЗОПАСНОСТЬ — Попытка отменить чужую бронь
    Это самый важный тест! Злоумышленник не должен иметь возможность
    отменить бронь другого пользователя.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Пользователь 1 создает бронь
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0)
        
        response = await client.post("/api/bookings", json={
            "user_id": 111111,
            "club_id": 1,
            "computer_id": "1",
            "start_time": tomorrow.isoformat(),
            "duration_minutes": 60
        })
        
        data = response.json()
        booking_id = data["booking_id"]
        
        # Пользователь 2 (злоумышленник) пытается отменить эту бронь
        cancel_response = await client.delete(
            f"/api/bookings/{booking_id}?user_id=222222"
        )
        
        # Должна вернуть 404 (чтобы не показывать, что бронь существует)
        assert cancel_response.status_code == 404
        
        error_data = cancel_response.json()
        assert "не найдена" in error_data["detail"].lower() or "не принадлежит" in error_data["detail"].lower()
        
        # Проверяем, что бронь ВСЁ ЕЩЁ существует в БД
        async with async_session_factory() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == booking_id)
            )
            booking = result.scalars().first()
            assert booking is not None
            assert booking.status == "CONFIRMED"  # НЕ отменена!
        
        print("✅ ТЕСТ ПРОЙДЕН: Злоумышленник не смог отменить чужую бронь!")


@pytest.mark.asyncio
async def test_cancel_own_booking_success():
    """
    ✅ ТЕСТ 4: Владелец может отменить свою бронь
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Создаем бронь
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)
        
        response = await client.post("/api/bookings", json={
            "user_id": 111111,
            "club_id": 1,
            "computer_id": "1",
            "start_time": tomorrow.isoformat(),
            "duration_minutes": 60
        })
        
        booking_id = response.json()["booking_id"]
        
        # Владелец отменяет свою бронь
        cancel_response = await client.delete(
            f"/api/bookings/{booking_id}?user_id=111111"
        )
        
        assert cancel_response.status_code == 200
        data = cancel_response.json()
        assert data["success"] is True
        
        # Проверяем статус в БД
        async with async_session_factory() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == booking_id)
            )
            booking = result.scalars().first()
            assert booking.status == "CANCELLED"
        
        print("✅ ТЕСТ ПРОЙДЕН: Владелец успешно отменил свою бронь")


if __name__ == "__main__":
    print("Запустите тесты командой: pytest tests/test_api_bookings.py -v")
