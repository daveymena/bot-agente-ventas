import asyncio
import aiohttp
from urllib.parse import quote

async def test_connection():
    server_url = "https://evoapi2-evolution-api.ovw3ar.easypanel.host"
    instance_name = "03d935e9-4711-4011-9ead-4983e4f6b2b5"
    api_key = "429683C4C977415CAAFCCE10F7D57E11"

    endpoints = [
        f"/instance/info/{quote(instance_name)}",
        f"/instance/connectionState/{quote(instance_name)}",
        "/instance/fetchInstances",
        f"/instance/qrbase64/{quote(instance_name)}",
        f"/instance/status/{quote(instance_name)}"
    ]

    headers = {"apikey": api_key}

    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            url = f"{server_url}{endpoint}"
            try:
                print(f"Testing: {url}")
                async with session.get(url, headers=headers) as response:
                    print(f"Status: {response.status}")
                    text = await response.text()
                    print(f"Response: {text[:200]}...")
                    print("-" * 50)
            except Exception as e:
                print(f"Error: {e}")
                print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_connection())
