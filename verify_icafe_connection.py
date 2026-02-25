import asyncio
from drivers.icafe import ICafeDriver
from datetime import datetime

async def test_icafe_connection():
    config = {
        "cafe_id": "88217",
        "api_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI2IiwianRpIjoiNTliNDg2NDYzMGUzOTMyNmRlNDc2YWQ0NWQzZmY0NDQwOTBmY2NmZDRmNGE1NGZlZDUzMGUxY2ZmMjk3YjM0ZDRhMTBkYTIxNTNiMDJiNmMiLCJpYXQiOjE3NzE2OTY1MTEuNjM1MDIyLCJuYmYiOjE3NzE2OTY1MTEuNjM1MDI0LCJleHAiOjQ5MjczNzAxMTEuNjMxNjkxLCJzdWIiOiI3MzQ3NzQ1MjU1ODgyMTciLCJzY29wZXMiOltdfQ.D71qeWDdAVyasAavE1Gl-NmgpDMC9fIXJXQaq9-tVaSJakdabVXcqrswvoirkj5Vc-NPOWJqVKGYqwSdFPVXm4vPnNaZiOJf1RhMDdvtC3THXWXWY7rKRpPZogiXfyWtB5FkpQ36lQbHsVBRJB8TdwvBdTjC7wBNmkprzHIgV_6PEz1LrJPDH7coHW8rNHnKtZuOuF7_IX1jOaERgMtZsBtuROvOpvKl1Ju3gWJckbB_VZVziYl6ZuqNNKsGwOf6n8Wzxifq7gSVW4uFhX75Es1kVQlUwq9ohgX2hbV40WAOidhwdWmWZv-aKfnOzaAX6gVTwwirmiUZg6G6bNp1i4Ol9qJUh6Tqdl7YxNjjso0q8LF_7nzZ0xBirMa1eZKLt1yfF8fF5zvaA3uOLBP4q6caijyrUtx0z0uYFGsBod_V3XmupfE60oLE3r4VhEJEa4lKVSPCzEsy2DwP_vuah2eNO504CEPwtHjZZwlPi_egv_RbNmG-Ms2pKQbmNTpt7O5PkSeMCyM9ceqArTr5-HhVCOE9l4JrKNvrebkXgAxtXGDMWOVOwIBw5fDa7lz_ncQIepHCNo39JtV5oVqYCkK8-byO4_A35F_fRR3f04vaXPjWFvR-Ia2CnuG9gvnkuAniocf_E-FEUYVY9rDaZq7gGqMu70BrbiB6ijxJxSs"
    }
    
    driver = ICafeDriver(config)
    print("Testing connection to iCafeCloud API...")
    
    try:
        computers = await driver.get_computers()
        print(f"Successfully connected! Found {len(computers)} computers.")
        for pc in computers:
            status = "Available" if pc.is_available else "Busy/Offline"
            print(f"- PC: {pc.name} (ID: {pc.id}) | Status: {status}")
            
        zones = await driver.get_club_zones()
        print(f"\nFound {len(zones)} zones:")
        for zone in zones:
            print(f"- Zone: {zone.name} | PCs: {zone.available_pcs}/{zone.total_pcs}")
            
    except Exception as e:
        print(f"Connection failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_icafe_connection())
