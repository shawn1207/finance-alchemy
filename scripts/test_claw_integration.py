
import asyncio
import sys
import os
import pandas as pd

# Add src to path
sys.path.append(os.getcwd())

from src.infrastructure.data_fetcher.claw_fetcher import ClawFetcher

async def test_claw_fetcher():
    fetcher = ClawFetcher()
    stock_code = "000423" # 东阿阿胶
    
    print(f"--- 正在测试 CLAW Fetcher: {stock_code} ---")
    
    # 1. Test Financial Metrics
    try:
        print("\n[1] 测试基本面指标...")
        metrics = await fetcher.fetch_financial_metrics(stock_code)
        print(f"成功获取指标: {list(metrics.keys())[:10]}...")
    except Exception as e:
        print(f"基本面指标获取失败: {e}")
        
    # 2. Test News
    try:
        print("\n[2] 测试官方资讯...")
        news = await fetcher.fetch_news(stock_code, limit=3)
        print(f"成功获取新闻 {len(news)} 条")
        for item in news:
            print(f"  - {item.get('title')}")
    except Exception as e:
        print(f"资讯获取失败: {e}")
        
    # 3. Test Technical Analysis
    try:
        print("\n[3] 测试官方技术分析...")
        tech = await fetcher.fetch_technical_analysis(stock_code)
        print(f"分析结论: {tech.get('summary', '无')}")
        print(f"指标状态: {tech.get('indicators', {})}")
    except Exception as e:
        print(f"技术分析获取失败: {e}")

    # 4. Test Realtime Quote
    try:
        print("\n[4] 测试实时行情...")
        quote = await fetcher.fetch_realtime_quote(stock_code)
        print(f"实时价格: {quote.get('price')}, 涨跌幅: {quote.get('changePercent')}%")
    except Exception as e:
        print(f"实时行情获取失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_claw_fetcher())
