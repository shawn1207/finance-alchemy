"""Fundamental analysis CrewAI agent factory."""

from crewai import Agent

from ..tools import (
    EastmoneySelectStockTool,
    FetchFinancialMetricsTool,
    FetchMacroIndicatorsTool,
    FetchStockNewsTool,
)


def create_fundamental_agent(llm=None, role=None, goal=None, backstory=None) -> Agent:
    """Create the fundamental analysis agent.

    This agent specialises in evaluating a company's financial health,
    profitability, growth trajectory and macroeconomic context.
    """
    return Agent(
        role=role or "A股基本面分析专家",
        goal=goal or (
            "深度分析A股上市公司的财务健康状况、盈利能力和成长潜力，"
            "结合宏观经济环境和最新市场新闻，给出专业的基本面评级。"
        ),
        backstory=backstory or (
            "你是一位拥有20年经验产生A股基本面分析师，曾任职于顶级券商研究所。"
            "你精通财务报表分析，擅长通过ROE、现金流、负债率等核心指标识别优质企业。"
            "你深刻理解中国宏观经济政策对行业和个股的传导机制，"
            "能够将财务数字与商业逻辑紧密结合，发现市场低估的投资机会。"
        ),
        tools=[
            EastmoneySelectStockTool(),
            FetchFinancialMetricsTool(),
            FetchMacroIndicatorsTool(),
            FetchStockNewsTool(),
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )
