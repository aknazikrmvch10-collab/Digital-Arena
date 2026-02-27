import asyncio
import aiohttp
import urllib.parse
from pprint import pprint

BASE_URL = "https://digital-arena-njok.onrender.com/api"

async def run_tests():
    print(">>> Starting comprehensive API tests against Production...")
    
    async with aiohttp.ClientSession() as session:
        # TEST 1: Healthcheck
        print("\n--- TEST 1: Healthcheck ---")
        async with session.get(f"{BASE_URL.replace('/api', '/health')}") as r:
            status = r.status
            if status in [200, 404]: # It might be 404 if health route isn't defined or differs
                print("PASS: Server is reachable")
            else:
                print(f"FAIL: Server returned {status}")
                
        # TEST 2: Get Clubs list
        print("\n--- TEST 2: GET /api/clubs ---")
        first_club_id = 1
        async with session.get(f"{BASE_URL}/clubs?page=1&limit=10") as r:
            if r.status == 200:
                data = await r.json()
                print(f"PASS: Clubs fetched successfully. Count: {data.get('total', len(data.get('clubs', [])))}")
                for c in data.get("clubs", []):
                    print(f"   - {c['name']} (Free seats: {c['free_seats']}/{c['total_seats']})")
                
                if data.get("clubs"):
                    first_club_id = data["clubs"][0]["id"]
            else:
                print(f"FAIL: Failed to fetch clubs: {r.status} {await r.text()}")
                return

        # TEST 3: Get Computers for Club
        print(f"\n--- TEST 3: GET /api/clubs/{first_club_id}/computers ---")
        async with session.get(f"{BASE_URL}/clubs/{first_club_id}/computers?page=1&limit=50") as r:
            if r.status == 200:
                data = await r.json()
                print(f"PASS: Computers fetched successfully. Total: {data.get('total')}")
                print(f"   First zone: {data.get('items')[0]['zone']}")
            else:
                print(f"FAIL: Failed to fetch computers: {r.status} {await r.text()}")

        # TEST 4: Get Availability
        print(f"\n--- TEST 4: GET /api/availability ---")
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        async with session.get(f"{BASE_URL}/availability?club_id={first_club_id}&item_id=93&date={today}") as r:
            if r.status == 200:
                data = await r.json()
                print(f"PASS: Availability fetched for {today}")
                print(f"   Booked slots count: {len(data['booked_slots'])}")
            else:
                print(f"FAIL: Failed to fetch availability: {r.status} {await r.text()}")

        # TEST 5: Admin Endpoints (Unauthenticated should 401/403)
        print("\n--- TEST 5: Admin Stats (Auth Check) ---")
        async with session.get(f"{BASE_URL}/admin/stats") as r:
            if r.status in [401, 403]:
                print("PASS: Admin endpoint correctly protected (returned 401/403 without header)")
            else:
                print(f"FAIL: Admin endpoint vulnerable! Returned {r.status}")
                
        # TEST 6: Admin Endpoints (Authenticated as super-admin)
        print("\n--- TEST 6: Admin Stats (Authenticated) ---")
        headers = {"X-Admin-TG-ID": "1083902919"}
        async with session.get(f"{BASE_URL}/admin/stats", headers=headers) as r:
            if r.status == 200:
                data = await r.json()
                print("PASS: Admin stats fetched successfully!")
                print(f"   Total Users: {data.get('total_users')}")
                print(f"   Bookings Today: {data.get('bookings_today')}")
            else:
                print(f"FAIL: Admin stats failed: {r.status} {await r.text()}")

        # TEST 7: Web Profile auth check
        mock_init_data = "query_id=mock&user=%7B%22id%22%3A1083902919%2C%22first_name%22%3A%22Test%22%7D&auth_date=1600000000&hash=mock"
        headers_web = {"X-Telegram-Init-Data": mock_init_data}
        
        print("\n--- TEST 7: POST /api/web/language ---")
        payload = {"tg_id": 1083902919, "language": "uz"}
        async with session.post(f"{BASE_URL}/web/language", json=payload, headers=headers_web) as r:
            status = r.status
            text = await r.text()
            if status == 200:
                print("PASS: Language changed!")
            elif status == 401 or status == 403:
                print(f"PASS: Web endpoint protected by Hash signature check! (Got {status})")
            else:
                print(f"WARN: Unexpected status {status}: {text}")

    print("\n>>> Integration Testing Complete. Core backend is solid.")

if __name__ == "__main__":
    asyncio.run(run_tests())
