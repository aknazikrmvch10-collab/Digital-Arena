import asyncio
from database import async_session_factory
from services.audit_service import log_event, verify_chain

async def main():
    async with async_session_factory() as session:
        print("Logging test events...")
        
        # Log 1
        await log_event(session, "TEST_EVENT_1", {"data": "test1"})
        print("Logged Event 1")
        
        # Log 2
        await log_event(session, "TEST_EVENT_2", {"data": "test2"})
        print("Logged Event 2")
        
        print("\nVerifying chain integrity...")
        is_valid = await verify_chain(session)
        
        if is_valid:
            print("SUCCESS: Audit Chain is VALID.")
        else:
            print("FAILURE: Audit Chain is BROKEN.")

if __name__ == "__main__":
    asyncio.run(main())
