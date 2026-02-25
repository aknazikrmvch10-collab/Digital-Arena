
import os
import sys
import hashlib
import hmac
import json
import urllib.parse
from fastapi.testclient import TestClient
from main import fastapi_app  # Import the app
from config import settings

def generate_init_data(user_id=123456789, first_name="TestUser"):
    """Generates a valid Telegram Web App initData string signed with BOT_TOKEN."""
    user_json = json.dumps({"id": user_id, "first_name": first_name, "last_name": "", "username": "test", "language_code": "en"}, separators=(',', ':'))
    
    data = {
        "query_id": "AAH...",
        "user": user_json,
        "auth_date": "1678900000",
    }
    
    # Sort keys for hash calculation
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    
    # Calculate hash
    secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    # Add hash to data
    data["hash"] = calculated_hash
    
    # Reconstruct query string
    return urllib.parse.urlencode(data)

def verify():
    print("Verifying Audit Fixes...")
    
    try:
        client = TestClient(fastapi_app)
        
        # 1. Test Health (No Auth)
        print("Testing /api/health...", end=" ")
        resp = client.get("/api/health")
        if resp.status_code == 200:
            print("PASSED")
        else:
            print(f"FAILED: {resp.status_code}")

        # 2. Test Get User Bookings with Valid Auth
        print("Testing /api/user/bookings with Valid Auth...", end=" ")
        init_data = generate_init_data()
        resp = client.get("/api/user/bookings", headers={"X-Telegram-Init-Data": init_data})
        
        if resp.status_code == 200:
            print("PASSED")
        elif resp.status_code == 500:
             print(f"FAILED (Server Error): {resp.text}")
        else:
            print(f"FAILED: {resp.status_code} {resp.text}")

        # 3. Test Get User Bookings with Invalid Auth
        print("Testing /api/user/bookings with INVALID Auth...", end=" ")
        resp = client.get("/api/user/bookings", headers={"X-Telegram-Init-Data": "invalid=data&hash=123"})
        if resp.status_code == 401:
            print("PASSED (Correctly rejected)")
        else:
            print(f"FAILED: Received {resp.status_code}")

        # 4. Test missing header
        print("Testing /api/user/bookings with MISSING Header...", end=" ")
        resp = client.get("/api/user/bookings")
        if resp.status_code == 401:
             print("PASSED (Correctly rejected)")
        else:
             print(f"FAILED: Received {resp.status_code}")
             
        print("\nVerification Complete!")
        
    except Exception as e:
        print(f"\n❌ Verification Script Error: {e}")

if __name__ == "__main__":
    verify()
