
import asyncio
import sys
import os
import httpx
import json

# Add src to path
sys.path.append(os.getcwd())

from src.infrastructure.data_fetcher.claw_fetcher import ClawFetcher

async def test_direct_endpoints():
    fetcher = ClawFetcher()
    stock_code = "000423"
    
    endpoints = ["stock-fundamental", "stock-technical", "stock-quote"]
    
    for endpoint in endpoints:
        print(f"\n--- Testing Endpoint: {endpoint} ---")
        payload = {
            "stockCode": stock_code,
            "pageNo": 1,
            "pageSize": 5
        }
        try:
            # We use _post which handles the full URL and headers
            data = await fetcher._post(endpoint, payload)
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
        except Exception as e:
            print(f"Error testing {endpoint}: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_endpoints())
