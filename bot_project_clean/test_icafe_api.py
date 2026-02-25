"""
Тестовый скрипт для проверки ICAFE API
"""
import asyncio
import aiohttp

API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI2IiwianRpIjoiZTVjOWMzNDdiZmM1ZWMxNTY1Yzc4MWY0NjA1MzA2ZjliNmMyZWU5OTE0MTVkYmJiMjgzODIwYjUwNWYyODgxZTY2YTlmY2ZjZjFiNDMwNzgiLCJpYXQiOjE3NjQxNDI4MDYuNzU3MDk1LCJuYmYiOjE3NjQxNDI4MDYuNzU3MDk4LCJleHAiOjE3OTU2Nzg4MDYuNzUzMTEzLCJzdWIiOiI3MzQ3NzQyMDMzODY0MTkiLCJzY29wZXMiOltdfQ.psI3lUQD1Uc1glYoE8EYVPipVChba1fz7Kq8vhNKziBplK84UtjS4zPTnADztg8r3qKbovHp8IKI1Z82aCjfplFY0LAQBzxQXf3pgrdd69ZvNMTwT3rQJH8Cc8j8UfvI323l01xaW7tbAynJfjgw-BzUZirEp05MjXMI8NYc8NDOPd2P5ZqaiVqbLZGXhVvBvJiAW5fcjvZkqdE4_mMkgj0PQvEugHJ2RvJ4vJBBmV8TaudbBZK-sSbxPubGV00qLHByY7UbKNuy6Vz1agCafCVWqlZogKvOzzpHO9gNeKeGzy8v7iqJM2eobXhB75f_Jf0EqMGtW1H1IRb0CzWyksCh08SuhwY6WHtBIVY_-JvtEV0jus2DU2Jor9fvNhPeqqRQiYiILmqzAUsYtf6NRvJt5xSwHjk4G_pD-1SebKwdkNHjJ1ptIquRjXL0MwYQrpDH1CaArftD27DMPRF5Q1-ysxdIDYnTjOpy3YTjbzxdeOsTO0u7GuLDo2As6Ms5Ba7KfkwyrAqgPeiIWRu8EkMDEKGL4YVO8rhkHhZ9P1QqSnwRERUuEcSE9rRBS70iWfVm25Log_aQ89kthRS0QCcFg9u6nq3zDZeifV6XyinMeEGrMaHJLCIG1-roay_TFGyY8zsC8GxB_WvXzJilkmIH0iW1HeThXIuTP2UsNek"
IP = "185.78.137.16"

# Попробуем разные варианты URL
test_urls = [
    f"http://{IP}/api",
    f"http://{IP}:8080/api",
    f"http://{IP}:3000/api",
    f"https://{IP}/api",
    f"https://{IP}:443/api",
    "https://api.icefleecloud.com/api",
    "https://dev.icefleecloud.com/api",
]

async def test_url(url):
    """Тестирует подключение к URL"""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                status = response.status
                text = await response.text()
                return {
                    "url": url,
                    "status": status,
                    "success": True,
                    "response": text[:200]  # Первые 200 символов
                }
    except Exception as e:
        return {
            "url": url,
            "success": False,
            "error": str(e)[:100]
        }

async def main():
    print("🔍 Тестирование ICAFE API...\n")
    
    tasks = [test_url(url) for url in test_urls]
    results = await asyncio.gather(*tasks)
    
    print("✅ УСПЕШНЫЕ:")
    for result in results:
        if result["success"]:
            print(f"  ✓ {result['url']}")
            print(f"    Статус: {result['status']}")
            print(f"    Ответ: {result['response']}\n")
    
    print("\n❌ НЕУДАЧНЫЕ:")
    for result in results:
        if not result["success"]:
            print(f"  ✗ {result['url']}")
            print(f"    Ошибка: {result['error']}\n")

if __name__ == "__main__":
    asyncio.run(main())
