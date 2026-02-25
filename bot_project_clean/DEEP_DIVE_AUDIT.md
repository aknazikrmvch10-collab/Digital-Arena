# 🕵️‍♂️ Deep Dive Audit Report (Round 2)

**Date:** 2026-02-12
**Status:** 🚨 CRITICAL LOGIC FLAWS DETECTED
**Focus:** Business Logic, Restaurant Support, Deployment Readiness

## 1. 🍽️ Restaurant Logic (Major Flaw)
> [!IMPORTANT]
> The current system treats Restaurants exactly like Computer Clubs, which is **fundamentally wrong**.

*   **Terminology:** The bot hardcodes the word **"Компьютер"** (Computer) everywhere.
    *   *Result:* Users booking a table will see messages like "Компьютер: Стол 1". This looks unprofessional.
*   **Pricing Logic:**
    *   *Current:* `Price = Hourly_Rate * Duration`.
    *   *The Problem:* Restaurants operate on **Deposit** (fixed amount) or **Free** booking logic. They rarely charge "50,000 sums per hour" like a PC club.
    *   *Impact:* The pricing calculation in `app.js` is incorrect for the restaurant demo (`setup_demo_restaurant.py`).

## 2. 🌍 Timezone & Localization (Critical for Production)
*   **The Issue:** The code uses `datetime.now()` (Server Local Time).
*   **The Risk:** If you deploy this to a cloud server (USA/Europe), the bot will be **5 hours behind** Tashkent time. Users will book for "14:00" but the system might think it's "09:00".
*   **Recommendation:** EVERYTHING must be explicitly converted to `Asia/Tashkent` timezone using `pytz` or `zoneinfo`.

## 3. 📱 Data Collection (Missing Phone Number)
*   **The Issue:** The bot auto-registers users using their Telegram Name/ID.
*   **The Risk:** You have **no way to contact** the client if they don't show up.
*   **Recommendation:** You MUST request the user's phone number (via `request_contact` button) before allowing the first booking.

## 4. 🚀 Deployment Readiness (Will Fail on Render)
*   **Host/Port:** `main.py` hardcodes `host="127.0.0.1"`.
    *   *Impact:* This will **FAIL** on almost all hosting providers (Render, Railway), which require binding to `0.0.0.0`.
*   **Seeding:** `seed_test_clubs()` runs on *every* startup.
    *   *Risk:* In production, restarting the bot might reset club data or create duplicates.

## 5. 🎨 Design (CSS)
*   **Verdict:** The "Cyberpunk" design (`style.css`) is actually quite good! It uses modern glassmorphism.
*   **Note:** It relies on a fixed max-width container, which is fine for Telegram Mini Apps (mobile-first).

---

## 🛠️ Updated Action Plan

1.  **Refactor Terminology:** Update `handlers/clubs.py` to check `club.venue_type`. If `restaurant`: Say "Стол" / "Table".
2.  **Fix Pricing Engine:** Update `miniapp/app.js` to handle `venue_type` logic (Deposit vs Hourly).
3.  **Deploy Fixes:** Change `uvicorn` host to `0.0.0.0` and use `os.getenv("PORT")`.
4.  **Add Phone Request:** Add middleware to ask for `contact` if `user.phone` is missing.
