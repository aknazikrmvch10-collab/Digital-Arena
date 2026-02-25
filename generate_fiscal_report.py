"""
Генератор HTML-отчета для Министерства.
Создает визуальный дашборд с данными по всем клубам.

Запуск:
    python generate_fiscal_report.py
"""
import asyncio
from datetime import datetime, timedelta
from database import init_db, async_session_factory
from services.fiscal_monitor import generate_all_clubs_report, calculate_discrepancy
from models import Club
from sqlalchemy import select


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digital Arena — Фискальный Отчет</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.2em;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            color: #888;
            font-size: 1.1em;
        }}
        .header .period {{
            color: #aaa;
            margin-top: 8px;
            font-size: 0.95em;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            backdrop-filter: blur(10px);
        }}
        .card .value {{
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .card .label {{
            color: #999;
            margin-top: 8px;
            font-size: 0.9em;
        }}
        .table-container {{
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: rgba(0,210,255,0.1);
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            color: #00d2ff;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 0.95em;
        }}
        tr:hover {{
            background: rgba(255,255,255,0.03);
        }}
        .status-ok {{
            color: #00e676;
            font-weight: bold;
        }}
        .status-warn {{
            color: #ff5252;
            font-weight: bold;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .bar-container {{
            width: 100%;
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }}
        .bar {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }}
        .bar-green {{ background: linear-gradient(90deg, #00e676, #69f0ae); }}
        .bar-yellow {{ background: linear-gradient(90deg, #ffd740, #ffab40); }}
        .bar-red {{ background: linear-gradient(90deg, #ff5252, #ff1744); }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #555;
            font-size: 0.85em;
        }}
        .footer a {{
            color: #3a7bd5;
            text-decoration: none;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .badge-ok {{ background: rgba(0,230,118,0.15); color: #00e676; }}
        .badge-warn {{ background: rgba(255,82,82,0.15); color: #ff5252; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎮 Digital Arena — Фискальный Мониторинг</h1>
        <div class="subtitle">Министерство Цифровых Технологий Республики Узбекистан</div>
        <div class="period">Период: {period}</div>
        <div class="period">Сгенерировано: {generated_at}</div>
    </div>

    <div class="summary-cards">
        <div class="card">
            <div class="value">{total_clubs}</div>
            <div class="label">Подключенных клубов</div>
        </div>
        <div class="card">
            <div class="value">{total_bookings}</div>
            <div class="label">Бронирований</div>
        </div>
        <div class="card">
            <div class="value">{total_hours}ч</div>
            <div class="label">Часов использования</div>
        </div>
        <div class="card">
            <div class="value">{flags_count}</div>
            <div class="label">⚠️ Флагов расхождения</div>
        </div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Клуб</th>
                    <th>Город</th>
                    <th>ПК</th>
                    <th>Броней</th>
                    <th>Часов</th>
                    <th>Загрузка</th>
                    <th>Ожидаемая выручка</th>
                    <th>Статус</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>

    <div class="footer">
        <p>Digital Arena Platform &copy; 2025 | 
        Данные защищены криптографической подписью (SHA-256 Audit Chain)</p>
        <p style="margin-top: 8px;">
            <a href="mailto:info@digitalarena.uz">info@digitalarena.uz</a>
        </p>
    </div>
</body>
</html>"""


def get_bar_class(utilization: float) -> str:
    if utilization > 60:
        return "bar-green"
    elif utilization > 30:
        return "bar-yellow"
    return "bar-red"


def format_currency(amount: float) -> str:
    """Format as UZS currency."""
    return f"{amount:,.0f} UZS"


async def generate_html_report(output_path: str = "fiscal_report.html"):
    """Generate HTML fiscal report for all clubs."""
    await init_db()
    
    # Period: last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    async with async_session_factory() as session:
        reports = await generate_all_clubs_report(session, start_date, end_date)
    
    # Build table rows
    table_rows = ""
    total_bookings = 0
    total_hours = 0
    flags_count = 0
    
    for r in reports:
        total_bookings += r["total_bookings"]
        total_hours += r["total_hours_used"]
        if r["discrepancy_flag"]:
            flags_count += 1
        
        bar_class = get_bar_class(r["utilization_rate"])
        status_class = "status-warn" if r["discrepancy_flag"] else "status-ok"
        badge_class = "badge-warn" if r["discrepancy_flag"] else "badge-ok"
        
        table_rows += f"""
                <tr>
                    <td><strong>{r.get('club_name', 'N/A')}</strong></td>
                    <td>{r.get('club_city', 'N/A')}</td>
                    <td>{r['total_pcs']}</td>
                    <td>{r['total_bookings']}</td>
                    <td>{r['total_hours_used']}</td>
                    <td>
                        <div class="bar-container">
                            <div class="bar {bar_class}" style="width: {min(r['utilization_rate'], 100)}%"></div>
                        </div>
                        <small>{r['utilization_rate']}%</small>
                    </td>
                    <td>{format_currency(r['expected_revenue'])}</td>
                    <td><span class="badge {badge_class}">{r['status']}</span></td>
                </tr>"""
    
    # Fill template
    html = HTML_TEMPLATE.format(
        period=f"{start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')}",
        generated_at=datetime.now().strftime('%d.%m.%Y %H:%M'),
        total_clubs=len(reports),
        total_bookings=total_bookings,
        total_hours=round(total_hours, 1),
        flags_count=flags_count,
        table_rows=table_rows if table_rows else "<tr><td colspan='8' style='text-align:center; padding:30px;'>Нет данных</td></tr>"
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"[OK] Отчет сгенерирован: {output_path}")
    print(f"   Клубов: {len(reports)}")
    print(f"   Бронирований: {total_bookings}")
    print(f"   Часов: {round(total_hours, 1)}")
    print(f"   Флагов: {flags_count}")
    
    return output_path


if __name__ == "__main__":
    asyncio.run(generate_html_report())
