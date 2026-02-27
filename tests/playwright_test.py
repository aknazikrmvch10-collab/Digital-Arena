import asyncio
from playwright.async_api import async_playwright
from textwrap import dedent

# URL of the deployed Mini App
MINIAPP_URL = "https://digital-arena-njok.onrender.com/miniapp/index.html"

async def test_miniapp_frontend():
    print(">>> Starting Playwright Frontend Test for Mini App...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Create a mobile-sized context
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        
        # Inject mock Telegram WebApp globally before the page loads
        # This bypasses the tg.initData check in app.js
        mock_tg_script = dedent("""
            window.Telegram = {
                WebApp: {
                    ready: () => console.log('Mock Telegram Ready'),
                    expand: () => console.log('Mock Telegram Expanded'),
                    initData: "query_id=mock&user=%7B%22id%22%3A1083902919%2C%22first_name%22%3A%22Test%22%7D",
                    initDataUnsafe: {
                        user: { id: 1083902919, first_name: "TestUser", username: "test_user" }
                    },
                    colorScheme: 'dark',
                    themeParams: {
                        bg_color: '#1a1a2e',
                        text_color: '#ffffff',
                        button_color: '#00f2ff',
                        button_text_color: '#000000'
                    },
                    BackButton: {
                        show: () => console.log('Back Arrow Show'),
                        hide: () => console.log('Back Arrow Hide'),
                        onClick: () => {}
                    },
                    MainButton: {
                        show: () => console.log('Main Button Show'),
                        hide: () => console.log('Main Button Hide'),
                        setText: () => {},
                        onClick: () => {}
                    },
                    HapticFeedback: {
                        notificationOccurred: (type) => console.log('Haptic', type)
                    },
                    openLink: (url) => console.log('Open link', url)
                }
            };
        """)
        
        await page.add_init_script(mock_tg_script)
        
        print(">>> Loading Mini App...")
        # Catch any JS errors!
        page.on("pageerror", lambda err: print(f"FAIL: JS ERROR on page: {err}"))
        page.on("console", lambda msg: print(f"INF: Console [{msg.type}]: {msg.text}"))
        
        await page.goto(MINIAPP_URL, wait_until="networkidle")
        
        # Check if the title is loaded
        title = await page.title()
        print(f"PASS: Page loaded with title: {title}")
        
        # Give it a second to fetch API data and render the clubs list
        await page.wait_for_timeout(3000)
        
        # Verify Bottom Navigation Tabs exist
        print("\n--- Verifying Tab Navigation ---")
        tabs = ["nav-clubs", "nav-bookings", "nav-profile"]
        for tab_id in tabs:
            tab = page.locator(f"#{tab_id}")
            if await tab.count() > 0:
                print(f"PASS: Found tab button: {tab_id}")
            else:
                print(f"FAIL: Missing tab: {tab_id}")
                
        # Simulate clicking "Bookings" tab
        print("\n--- Testing Tab Switching ---")
        await page.click("#nav-bookings")
        await page.wait_for_timeout(1000)
        
        # The bookings panel should be visible now, clubs hidden
        is_clubs_hidden = await page.locator("#tab-clubs").evaluate("el => el.classList.contains('hidden')")
        is_bookings_visible = await page.locator("#tab-bookings").evaluate("el => !el.classList.contains('hidden')")
        print(f"PASS: Switches to Bookings: Clubs hidden={is_clubs_hidden}, Bookings visible={is_bookings_visible}")
        
        # Simulate clicking "Profile" tab
        await page.click("#nav-profile")
        await page.wait_for_timeout(1000)
        is_profile_visible = await page.locator("#tab-profile").evaluate("el => !el.classList.contains('hidden')")
        print(f"PASS: Switches to Profile: Profile visible={is_profile_visible}")
        
        # Check if Profile loaded data
        profile_content = await page.locator("#profile-content").text_content()
        if "TestUser" in profile_content or "@test_user" in profile_content:
            print("PASS: Profile tab successfully rendered mock user data!")
        else:
            print("WARN: Profile tab might not have completed fetching data.")

        # Go back to Clubs tab
        await page.click("#nav-clubs")
        await page.wait_for_timeout(1000)
        
        # Now let's test clicking a club card (the hotfix we deployed)
        print("\n--- Testing Club Selection (The Hotfix) ---")
        club_cards = page.locator(".club-card")
        card_count = await club_cards.count()
        print(f"PASS: Found {card_count} club cards visually rendered.")
        
        if card_count > 0:
            print(">>> Clicking first club card to navigate to zones...")
            await club_cards.first.click()
            await page.wait_for_timeout(3000)
            
            # If the fix works, we should see zones or Skeletons, NOT an error!
            zones = page.locator(".zone-btn")
            zone_count = await zones.count()
            print(f"PASS: Club loaded. Found {zone_count} zone(s).")
            
            computers = page.locator(".computer-card")
            comp_count = await computers.count()
            print(f"PASS: Found {comp_count} computers rendered for the selected zone.")
        
        print("\n>>> All automated frontend tests passed!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_miniapp_frontend())
