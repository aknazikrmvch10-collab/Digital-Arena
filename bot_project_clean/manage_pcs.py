import asyncio
import sys
from sqlalchemy import select, update
from database import async_session_factory
from models import Club, Computer

async def list_pcs():
    async with async_session_factory() as session:
        result = await session.execute(select(Computer))
        pcs = result.scalars().all()
        print("\n=== Список компьютеров в базе ===")
        print(f"{'ID':<5} | {'ClubID':<8} | {'Name':<15} | {'Zone':<15} | {'Active':<8}")
        print("-" * 60)
        for pc in pcs:
            print(f"{pc.id:<5} | {pc.club_id:<8} | {pc.name:<15} | {pc.zone:<15} | {pc.is_active:<8}")
        print("-" * 60)

async def toggle_pc(pc_id: int, active: bool):
    async with async_session_factory() as session:
        async with session.begin():
            pc = await session.get(Computer, pc_id)
            if pc:
                pc.is_active = active
                print(f"✅ ПК {pc.name} (ID: {pc.id}) теперь {'АКТИВЕН' if active else 'ДЕАКТИВИРОВАН'}")
            else:
                print(f"❌ ПК с ID {pc_id} не найден")

async def add_pc(club_id: int, name: str, zone: str = "Standard", price: int = 10000):
    async with async_session_factory() as session:
        async with session.begin():
            new_pc = Computer(
                club_id=club_id,
                name=name,
                zone=zone,
                price_per_hour=price,
                is_active=True
            )
            session.add(new_pc)
            print(f"✅ ПК {name} добавлен в клуб {club_id}")

async def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python manage_pcs.py list                - Показать все ПК")
        print("  python manage_pcs.py off <ID>            - Выключить ПК (сделать админским)")
        print("  python manage_pcs.py on <ID>             - Включить ПК (сделать игровым)")
        print("  python manage_pcs.py add <ClubID> <Name> - Добавить новый ПК")
        return

    cmd = sys.argv[1]
    if cmd == "list":
        await list_pcs()
    elif cmd == "off" and len(sys.argv) > 2:
        await toggle_pc(int(sys.argv[2]), False)
    elif cmd == "on" and len(sys.argv) > 2:
        await toggle_pc(int(sys.argv[2]), True)
    elif cmd == "add" and len(sys.argv) > 3:
        await add_pc(int(sys.argv[2]), sys.argv[3])
    else:
        print("Неизвестная команда или нехватка аргументов")

if __name__ == "__main__":
    asyncio.run(main())
