import asyncio
from database import async_session_factory
from models import Booking, User
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(Booking))
        bookings = result.scalars().all()
        for b in bookings:
            user = await session.get(User, b.user_id)
            print(f"Booking {b.id}: User ID {user.id}, tg_id {user.tg_id}")

            from handlers.api import get_user_bookings
            from handlers.dependencies import PaginationParams
            
            # Call the function directly to see if it raises an exception
            try:
                res = await get_user_bookings(
                    request=None,
                    user_data={"id": user.tg_id},
                    pagination=PaginationParams(page=1, limit=50)
                )
                print(f"Result: {res}")
            except Exception as e:
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
