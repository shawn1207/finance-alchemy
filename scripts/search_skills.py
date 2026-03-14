
import asyncio
import sys
import os
import json

# Add src to path
sys.path.append(os.getcwd())

from src.infrastructure.data_fetcher.claw_fetcher import ClawFetcher

async def search_skills():
    fetcher = ClawFetcher()
    queries = ["财务", "指标", "利润", "技术分析", "报告", "K线"]
    
    for q in queries:
        print(f"\n--- Searching Skills for: {q} ---")
        payload = {
            "query": q,
            "pageNo": 1,
            "pageSize": 10
        }
        try:
            # news-search uses 'query', maybe other meta endpoints do too?
            # Let's try a hypothetical 'skill-search'
            data = await fetcher._post("news-search", payload) # Re-using news-search to see if it acts as a general search
            print(f"News Search Data for '{q}': {len(data.get('data', []))} results")
            for item in data.get("data", [])[:3]:
                print(f"  - {item.get('chunk')[:100]}...")
        except Exception as e:
            print(f"Error searching {q}: {e}")

if __name__ == "__main__":
    asyncio.run(search_skills())
