import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        try:
            print("Fetching /api/clubs...")
            response = await client.get("http://127.0.0.1:8000/api/clubs", timeout=5.0)
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
    
    # Test computers for club 1
    async def test_computers():
        async with httpx.AsyncClient() as client:
            try:
                print("\nFetching /api/clubs/1/computers...")
                response = await client.get("http://127.0.0.1:8000/api/clubs/1/computers", timeout=5.0)
                print(f"Status: {response.status_code}")
                # print(f"Body: {response.text}") # Too long?
                print(f"Body length: {len(response.text)}")
            except Exception as e:
                print(f"Error: {e}")

    asyncio.run(test_computers())
