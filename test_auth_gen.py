import asyncio
from datetime import timedelta
import random

from database import async_session_factory, engine
from models import AppAuthCode, User, Base
from utils.timezone import now_tashkent

async def test():
    print("Testing DB...")
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    tg_id = 12345
    phone = "+998901112233"
    code = "123456"
    now = now_tashkent()
    expires = now + timedelta(minutes=10)

    try:
        async with async_session_factory() as session:
            # 1. Save phone number to base User model
            from sqlalchemy import select
            user_result = await session.execute(
                select(User).where(User.tg_id == tg_id)
            )
            user = user_result.scalars().first()
            if not user:
                user = User(tg_id=tg_id, phone=phone, full_name="Test User")
                session.add(user)
            else:
                user.phone = phone

            # 2. Invalidate any existing unused codes for this user
            from sqlalchemy import update
            await session.execute(
                update(AppAuthCode)
                .where(AppAuthCode.user_id == tg_id, AppAuthCode.used == False)
                .values(used=True)
            )

            # 3. Create new code
            auth_code = AppAuthCode(
                user_id=tg_id,
                phone=phone,
                code=code,
                expires_at=expires,
            )
            session.add(auth_code)
            await session.commit()
            print("SUCCESS! Code inserted")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
