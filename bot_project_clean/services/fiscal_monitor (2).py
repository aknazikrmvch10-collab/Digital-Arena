"""
Fiscal Monitor Service
Сравнение времени работы ПК с фактической выручкой.
Используется для отчетности Министерству.

Логика:
1. Получаем данные о сессиях ПК (из драйвера клуба)
2. Получаем данные о бронированиях/оплатах (из нашей БД)
3. Сравниваем и находим расхождения
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from models import Booking, Club, Computer
from services.audit_service import log_event


async def get_club_usage_stats(db: AsyncSession, club_id: int, start_date: datetime, end_date: datetime) -> dict:
    """
    Получает статистику использования ПК из бронирований.
    Возвращает: общее время работы, количество сессий, выручку.
    """
    result = await db.execute(
        select(
            func.count(Booking.id).label("total_bookings"),
            func.sum(
                func.julianday(Booking.end_time) - func.julianday(Booking.start_time)
            ).label("total_days")  # SQLite returns days as float
        ).where(
            and_(
                Booking.club_id == club_id,
                Booking.start_time >= start_date,
                Booking.end_time <= end_date,
                Booking.status.in_(["CONFIRMED", "COMPLETED"])
            )
        )
    )
    row = result.first()
    
    total_bookings = row.total_bookings or 0
    total_hours = (row.total_days or 0) * 24  # Convert days to hours
    
    return {
        "club_id": club_id,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_bookings": total_bookings,
        "total_hours": round(total_hours, 2),
    }


async def get_club_capacity(db: AsyncSession, club_id: int) -> dict:
    """
    Получает информацию о мощности клуба (кол-во ПК).
    """
    result = await db.execute(
        select(func.count(Computer.id)).where(
            and_(
                Computer.club_id == club_id,
                Computer.is_active == True
            )
        )
    )
    total_pcs = result.scalar() or 0
    
    return {
        "club_id": club_id,
        "total_active_pcs": total_pcs
    }


async def calculate_discrepancy(
    db: AsyncSession,
    club_id: int,
    start_date: datetime,
    end_date: datetime,
    reported_revenue: float = 0,
    avg_price_per_hour: float = 10000  # UZS (default)
) -> dict:
    """
    Основная функция: Сравнение использования ПК и заявленной выручки.
    
    Логика:
    - Считаем сколько часов ПК были заняты (из бронирований)
    - Умножаем на среднюю цену за час
    - Сравниваем с заявленной выручкой
    - Если расхождение > 15% → флаг для проверки
    
    Args:
        db: Сессия БД
        club_id: ID клуба
        start_date: Начало периода
        end_date: Конец периода
        reported_revenue: Заявленная выручка клубом (наличные + безнал)
        avg_price_per_hour: Средняя цена за час (UZS)
    """
    usage = await get_club_usage_stats(db, club_id, start_date, end_date)
    capacity = await get_club_capacity(db, club_id)
    
    # Расчет ожидаемой выручки
    expected_revenue = usage["total_hours"] * avg_price_per_hour
    
    # Расчет максимально возможной выручки (если все ПК работали 24/7)
    total_days = (end_date - start_date).days or 1
    max_possible_hours = capacity["total_active_pcs"] * total_days * 24
    
    # Процент загрузки
    utilization_rate = (usage["total_hours"] / max_possible_hours * 100) if max_possible_hours > 0 else 0
    
    # Расхождение
    if reported_revenue > 0:
        discrepancy_pct = abs(expected_revenue - reported_revenue) / expected_revenue * 100 if expected_revenue > 0 else 100
        discrepancy_flag = discrepancy_pct > 15  # Флаг если больше 15%
    else:
        discrepancy_pct = 0
        discrepancy_flag = False
    
    report = {
        "club_id": club_id,
        "period": f"{start_date.strftime('%Y-%m-%d')} — {end_date.strftime('%Y-%m-%d')}",
        "total_pcs": capacity["total_active_pcs"],
        "total_bookings": usage["total_bookings"],
        "total_hours_used": usage["total_hours"],
        "max_possible_hours": round(max_possible_hours, 2),
        "utilization_rate": round(utilization_rate, 2),
        "expected_revenue": round(expected_revenue, 2),
        "reported_revenue": reported_revenue,
        "discrepancy_pct": round(discrepancy_pct, 2),
        "discrepancy_flag": discrepancy_flag,
        "status": "🔴 РАСХОЖДЕНИЕ" if discrepancy_flag else "🟢 НОРМА"
    }
    
    # Логируем в аудит
    await log_event(db, "FISCAL_REPORT", report)
    
    return report


async def generate_all_clubs_report(db: AsyncSession, start_date: datetime, end_date: datetime) -> list:
    """
    Генерирует фискальный отчет по ВСЕМ клубам.
    """
    result = await db.execute(
        select(Club).where(Club.is_active == True)
    )
    clubs = result.scalars().all()
    
    reports = []
    for club in clubs:
        report = await calculate_discrepancy(db, club.id, start_date, end_date)
        report["club_name"] = club.name
        report["club_city"] = club.city
        reports.append(report)
    
    return reports
