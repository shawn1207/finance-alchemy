
import asyncio
import sys
import os
import json

# Add src to path
sys.path.append(os.getcwd())

from src.infrastructure.data_fetcher.claw_fetcher import ClawFetcher

async def probe_keywords():
    fetcher = ClawFetcher()
    stock_code = "000423"
    tech_kw = f"{stock_code} MA指标 RSI指标 MACD指标 支撑位 压力位 技术面评分"
    print(f"\n--- Testing Bulk Tech Keyword: {tech_kw} ---")
    payload = {
        "keyword": tech_kw,
        "pageNo": 1,
        "pageSize": 5
    }
    try:
        data = await fetcher._post("stock-screen", payload)
        result = data.get("data", {}).get("result", {})
        items = result.get("dataList", [])
        columns = result.get("columns", [])
        
        if items:
            print(f"✅ Bulk Tech Query Found {len(items)} items")
            for col in columns:
                title = col.get("title")
                key = col.get("key")
                val = items[0].get(key)
                print(f"  {title} = {val}")
        else:
            print("❌ Bulk Tech Query No data found")
    except Exception as e:
        print(f"Error testing tech query: {e}")

if __name__ == "__main__":
    asyncio.run(probe_keywords())
