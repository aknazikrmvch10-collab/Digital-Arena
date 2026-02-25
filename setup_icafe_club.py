"""
Script for quick iCafe Cloud club setup
"""
import asyncio
from database import init_db, async_session_factory
from models import Club
from sqlalchemy import select

# iCafe Cloud settings
CAFE_ID = "86419"
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI2IiwianRpIjoiZTVjOWMzNDdiZmM1ZWMxNTY1Yzc4MWY0NjA1MzA2ZjliNmMyZWU5OTE0MTVkYmJiMjgzODIwYjUwNWYyODgxZTY2YTlmY2ZjZjFiNDMwNzgiLCJpYXQiOjE3NjQxNDI4MDYuNzU3MDk1LCJuYmYiOjE3NjQxNDI4MDYuNzU3MDk4LCJleHAiOjE3OTU2Nzg4MDYuNzUzMTEzLCJzdWIiOiI3MzQ3NzQyMDMzODY0MTkiLCJzY29wZXMiOltdfQ.psI3lUQD1Uc1glYoE8EYVPipVChba1fz7Kq8vhNKziBplK84UtjS4zPTnADztg8r3qKbovHp8IKI1Z82aCjfplFY0LAQBzxQXf3pgrdd69ZvNMTwT3rQJH8Cc8j8UfvI323l01xaW7tbAynJfjgw-BzUZirEp05MjXMI8NYc8NDOPd2P5ZqaiVqbLZGXhVvBvJiAW5fcjvZkqdE4_mMkgj0PQvEugHJ2RvJ4vJBBmV8TaudbBZK-sSbxPubGV00qLHByY7UbKNuy6Vz1agCafCVWqlZogKvOzzpHO9gNeKeGzy8v7iqJM2eobXhB75f_Jf0EqMGtW1H1IRb0CzWyksCh08SuhwY6WHtBIVY_-JvtEV0jus2DU2Jor9fvNhPeqqRQiYiILmqzAUsYtf6NRvJt5xSwHjk4G_pD-1SebKwdkNHjJ1ptIquRjXL0MwYQrpDH1CaArftD27DMPRF5Q1-ysxdIDYnTjOpy3YTjbzxdeOsTO0u7GuLDo2As6Ms5Ba7KfkwyrAqgPeiIWRu8EkMDEKGL4YVO8rhkHhZ9P1QqSnwRERUuEcSE9rRBS70iWfVm25Log_aQ89kthRS0QCcFg9u6nq3zDZeifV6XyinMeEGrMaHJLCIG1-roay_TFGyY8zsC8GxB_WvXzJilkmIH0iW1HeThXIuTP2UsNek"

async def setup_icafe_club():
    """Adds or updates club with iCafe Cloud settings."""
    await init_db()
    
    print("Configuring iCafe Cloud club...\n")
    
    async with async_session_factory() as session:
        # Check if Arenaslot club already exists
        result = await session.execute(
            select(Club).where(Club.name == "Arenaslot")
        )
        club = result.scalars().first()
        
        if club:
            print(f"- Club '{club.name}' found (ID: {club.id})")
            # Update configuration
            club.driver_type = "ICAFE"
            club.connection_config = {
                "cafe_id": CAFE_ID,
                "api_token": API_TOKEN
            }
            print("- Configuration updated")
        else:
            # Create new club
            club = Club(
                name="Arenaslot",
                city="Tashkent",
                address="Tashkent, Uzbekistan",
                driver_type="ICAFE",
                connection_config={
                    "cafe_id": CAFE_ID,
                    "api_token": API_TOKEN
                },
                is_active=True
            )
            session.add(club)
            print("- New club 'Arenaslot' created")
        
        await session.commit()
        await session.refresh(club)
        
        print(f"\nDone! Club ID: {club.id}")
        print(f"   Name: {club.name}")
        print(f"   Driver: {club.driver_type}")
        print(f"   Cafe ID: {CAFE_ID}")
        print("\nNow start the bot: .\\venv\\Scripts\\python main.py")
        print("   And use /admin in Telegram to manage!")

if __name__ == "__main__":
    asyncio.run(setup_icafe_club())
