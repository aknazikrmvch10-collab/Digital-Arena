#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Status Script
Быстрый обзор состояния проекта CyberArena
Запускай каждый раз перед началом работы: python project_status.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Ensure we're using the venv
venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'Lib', 'site-packages')
if os.path.exists(venv_path) and venv_path not in sys.path:
    sys.path.insert(0, venv_path)

from sqlalchemy import select, func
from database import async_session_factory, init_db
from models import Club, Computer, RestaurantTable, Booking, User, Admin

async def get_project_status():
    await init_db()
    
    print("=" * 60)
    print("CYBERARENA PROJECT STATUS")
    print("=" * 60)
    print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    async with async_session_factory() as session:
        # 1. Клубы и заведения
        print("🏢 ЗАВЕДЕНИЯ:")
        clubs_result = await session.execute(select(Club))
        clubs = clubs_result.scalars().all()
        
        if clubs:
            for club in clubs:
                venue_icon = "🍽️" if club.venue_type == "restaurant" else "🖥️"
                print(f"  {venue_icon} [{club.id}] {club.name} ({club.city})")
                print(f"      Тип: {club.venue_type} | Драйвер: {club.driver_type}")
        else:
            print("  ⚠️  Нет заведений в базе")
        print()
        
        # 2. Компьютеры
        print("💻 КОМПЬЮТЕРНЫЕ КЛУБЫ:")
        computers_result = await session.execute(select(Computer))
        computers = computers_result.scalars().all()
        
        if computers:
            # Группируем по клубам
            comp_by_club = {}
            for comp in computers:
                if comp.club_id not in comp_by_club:
                    comp_by_club[comp.club_id] = []
                comp_by_club[comp.club_id].append(comp)
            
            for club_id, comps in comp_by_club.items():
                club = await session.get(Club, club_id)
                zones = set([c.zone for c in comps])
                print(f"  🎮 {club.name}: {len(comps)} ПК в {len(zones)} зонах")
        else:
            print("  ℹ️  Нет компьютеров")
        print()
        
        # 3. Рестораны
        print("🍽️  РЕСТОРАНЫ:")
        tables_result = await session.execute(select(RestaurantTable))
        tables = tables_result.scalars().all()
        
        if tables:
            # Группируем по клубам
            tables_by_club = {}
            for table in tables:
                if table.club_id not in tables_by_club:
                    tables_by_club[table.club_id] = []
                tables_by_club[table.club_id].append(table)
            
            for club_id, tbls in tables_by_club.items():
                club = await session.get(Club, club_id)
                zones = set([t.zone for t in tbls])
                print(f"  🪑 {club.name}: {len(tbls)} столов в {len(zones)} зонах")
        else:
            print("  ℹ️  Нет ресторанов")
        print()
        
        # 4. Пользователи и брони
        print("👥 ПОЛЬЗОВАТЕЛИ И БРОНИ:")
        users_count = await session.scalar(select(func.count()).select_from(User))
        bookings_count = await session.scalar(select(func.count()).select_from(Booking))
        active_bookings = await session.scalar(
            select(func.count()).select_from(Booking).where(Booking.status == "CONFIRMED")
        )
        
        print(f"  👤 Пользователей: {users_count}")
        print(f"  📅 Всего броней: {bookings_count}")
        print(f"  ✅ Активных броней: {active_bookings}")
        print()
        
        # 5. Админы
        print("🔐 АДМИНИСТРАТОРЫ:")
        admins_result = await session.execute(select(Admin))
        admins = admins_result.scalars().all()
        
        if admins:
            for admin in admins:
                print(f"  👑 Telegram ID: {admin.tg_id}")
        else:
            print("  ⚠️  Нет администраторов")
        print()
        
        # 6. Файлы проекта
        print("📁 КЛЮЧЕВЫЕ ФАЙЛЫ:")
        important_files = [
            ("main.py", "Основной бот"),
            ("handlers/api.py", "API для Mini App"),
            ("miniapp/app.js", "Frontend Mini App"),
            ("website/", "Веб-сайт (если есть)"),
            ("bot_database.db", "База данных"),
        ]
        
        for file_path, description in important_files:
            full_path = os.path.join(os.path.dirname(__file__), file_path)
            exists = "✅" if os.path.exists(full_path) else "❌"
            print(f"  {exists} {file_path} - {description}")
        print()
        
        # 7. Быстрые команды
        print("⚡ БЫСТРЫЕ КОМАНДЫ:")
        print("  python main.py                    # Запустить бота")
        print("  python setup_demo_club.py         # Создать демо клуб")
        print("  python setup_demo_restaurant.py   # Создать демо ресторан")
        print("  python add_admin.py               # Добавить админа")
        print()
        
        # 8. Следующие шаги (из task.md если есть)
        task_file = os.path.join(
            os.path.expanduser("~"),
            ".gemini/antigravity/brain/cdacbb5c-310e-4d1a-b8af-040702131dd5/task.md"
        )
        
        if os.path.exists(task_file):
            print("📋 ТЕКУЩИЕ ЗАДАЧИ:")
            with open(task_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                in_progress = [line.strip() for line in lines if '[/]' in line or '[ ]' in line]
                for task in in_progress[:5]:  # Показываем первые 5
                    print(f"  {task}")
            print()
        
    print("=" * 60)
    print("💡 Готов к работе! Спроси меня 'что дальше?' для продолжения")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(get_project_status())
