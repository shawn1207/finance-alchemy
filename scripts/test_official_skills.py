"""Test script to verify official Eastmoney skills."""

import os
from dotenv import load_dotenv
from src.infrastructure.crewai_workers.tools.eastmoney_data_tool import EastmoneyFinancialDataTool
from src.infrastructure.crewai_workers.tools.eastmoney_search_tool import EastmoneyFinancialSearchTool
from src.infrastructure.crewai_workers.tools.eastmoney_tools import EastmoneySelectStockTool

load_dotenv()

def test_data_tool():
    print("\n--- Testing EastmoneyFinancialDataTool ---")
    tool = EastmoneyFinancialDataTool()
    result = tool._run(toolQuery="600519的最新Roe和净利润率")
    print(f"Result:\n{result[:500]}...")

def test_search_tool():
    print("\n--- Testing EastmoneyFinancialSearchTool ---")
    tool = EastmoneyFinancialSearchTool()
    result = tool._run(query="贵州茅台近期研报要点")
    print(f"Result:\n{result[:500]}...")

def test_select_tool():
    print("\n--- Testing EastmoneySelectStockTool ---")
    tool = EastmoneySelectStockTool()
    result = tool._run(keyword="今日涨幅超2%的白马股")
    print(f"Result:\n{result[:500]}...")

if __name__ == "__main__":
    try:
        test_data_tool()
        test_search_tool()
        test_select_tool()
    except Exception as e:
        print(f"Test failed: {e}")
