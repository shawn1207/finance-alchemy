"""CrewAI tool for Eastmoney stock screening."""

import json
import os

import httpx
import pandas as pd
from cachetools import TTLCache, cached
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from src.config import get_settings
from src.infrastructure.data_fetcher.utils import rate_limit

# Cache for 10 minutes (600 seconds), with a max size of 128
cache = TTLCache(maxsize=128, ttl=600)


class EastmoneySelectStockInput(BaseModel):
    keyword: str = Field(..., description="选股条件自然语言描述，如 '今日涨幅2%的股票'")
    pageNo: int = Field(default=1, description="页码")
    pageSize: int = Field(default=20, description="每页数据条数")


class EastmoneySelectStockTool(BaseTool):
    name: str = "eastmoney_select_stock"
    description: str = (
        "基于自然语言查询进行选股（支持 A股、港股、美股）。"
        "可筛选行情指标、财务指标，查询行业/板块成分股，以及股票/板块推荐。"
        "返回全量数据的 CSV 文件路径及数据说明。"
    )
    args_schema: Type[BaseModel] = EastmoneySelectStockInput

    @staticmethod
    @cached(cache)
    @rate_limit(calls_per_second=0.5, label="eastmoney")
    def get_stock_list(keyword: str, pageNo: int = 1, pageSize: int = 20) -> pd.DataFrame:
        """Helper for GUI to get data as DataFrame."""
        settings = get_settings()
        api_key = settings.eastmoney_api_key
        url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/stock-screen"
        
        headers = {
            "Content-Type": "application/json",
            "apikey": api_key
        }
        
        payload = {
            "keyword": keyword,
            "pageNo": pageNo,
            "pageSize": pageSize
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

        if result.get("status") != 0 or result.get("data", {}).get("code") != "100":
            return pd.DataFrame()
        
        inner_data = result.get("data", {}).get("data", {})
        data_list = inner_data.get("result", {}).get("dataList", [])
        columns_def = inner_data.get("result", {}).get("columns", [])
        
        if not data_list:
            return pd.DataFrame()

        col_map = {col['key']: col['title'] for col in columns_def if 'key' in col and 'title' in col}
        df = pd.DataFrame(data_list)
        df.rename(columns=col_map, inplace=True)
        return df

    @rate_limit(calls_per_second=0.5, label="eastmoney")
    def _run(self, keyword: str, pageNo: int = 1, pageSize: int = 20) -> str:
        settings = get_settings()
        api_key = settings.eastmoney_api_key
        url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/stock-screen"
        
        headers = {
            "Content-Type": "application/json",
            "apikey": api_key
        }
        
        payload = {
            "keyword": keyword,
            "pageNo": pageNo,
            "pageSize": pageSize
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
        except Exception as e:
            return f"调用东方财富选股接口失败: {str(e)}"

        # Check status
        if result.get("status") != 0:
            msg = result.get('message', '未知错误')
            if "上限" in msg or "limit" in msg.lower():
                return f"⚠️ 选股接口今日调用次数已达上限。\n\n> 💡 **建议**：您可以尝试直接访问 [东方财富妙想官网](https://miaoxiang.eastmoney.com/) 进行选股，或稍后再试。"
            return f"接口返回错误: {msg}"
        
        data_section = result.get("data", {})
        if data_section.get("code") != "100":
            return f"选股业务处理失败: {data_section.get('msg', '未知错误')}"
        
        inner_data = data_section.get("data", {})
        result_data = inner_data.get("result", {})
        data_list = result_data.get("dataList", [])
        columns_def = result_data.get("columns", [])
        
        if not data_list:
            return "未找到符合条件的股票。提示：您可以尝试前往东方财富妙想AI进行更详细的选股查询。"

        # Map columns: key -> title
        col_map = {col['key']: col['title'] for col in columns_def if 'key' in col and 'title' in col}
        
        # Create DataFrame
        df = pd.DataFrame(data_list)
        
        # Rename columns using the map
        df.rename(columns=col_map, inplace=True)
        
        # Ensure directory exists
        output_dir = "outputs/eastmoney"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filenames
        safe_keyword = "".join([c for c in keyword if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_')
        csv_path = os.path.join(output_dir, f"select_stock_{safe_keyword}.csv")
        desc_path = os.path.join(output_dir, f"select_stock_{safe_keyword}_desc.txt")
        
        # Save CSV
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # Save description file
        with open(desc_path, 'w', encoding='utf-8') as f:
            f.write(f"选股关键词: {keyword}\n")
            f.write(f"总计结果数: {result_data.get('total', '未知')}\n")
            f.write(f"本次返回条数: {len(data_list)}\n")
            f.write("-" * 20 + "\n")
            f.write("筛选条件详情:\n")
            cond_list = inner_data.get("responseConditionList", [])
            for cond in cond_list:
                f.write(f"- {cond.get('describe')}: {cond.get('stockCount')} 只匹配\n")
            
            total_cond = inner_data.get("totalCondition", {})
            f.write(f"\n组合条件描述: {total_cond.get('describe', 'N/A')}\n")
            f.write(f"组合条件总计匹配: {total_cond.get('stockCount', 'N/A')} 只\n")
            
            f.write("\n解析文本: " + inner_data.get("parserText", "N/A") + "\n")

        return (
            f"成功完成选股查询！\n"
            f"关键词: {keyword}\n"
            f"符合条件股票总数: {result_data.get('total', '未知')}\n"
            f"数据已保存至:\n"
            f"- CSV 数据文件: {csv_path}\n"
            f"- 筛选条件说明: {desc_path}\n"
            f"提示：若数据结果为空，建议前往东方财富妙想AI进行选股。"
        )
