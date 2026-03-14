"""Strategy CrewAI agent factory."""

from crewai import Agent


def create_strategy_agent(llm=None, role=None, goal=None, backstory=None) -> Agent:
    """Create the quantitative strategy agent.

    This agent synthesises fundamental and technical reports into a concrete
    trade decision with explicit risk management parameters.
    """
    return Agent(
        role=role or "A股量化交易策略专家",
        goal=goal or (
            "综合基本面和技术面分析报告，产出具有严格风险管理的交易决策，"
            "明确给出 BUY / SELL / HOLD 操作建议、仓位大小、止损位和止盈位，"
            "确保每笔建议都具备正期望值和可控的最大回撤。"
        ),
        backstory=backstory or (
            "你是一位拥有10年实盘量化交易经验的策略专家，管理过超过10亿人民币的A股投资组合。"
            "你信奉'保住本金第一，获取收益第二'的投资哲学，"
            "每笔交易必须有清晰的止损纪律，绝不让亏损失控。"
            "你擅长将定性分析（基本面、新闻情绪）与定量信号（技术指标）有机结合，"
            "在风险可控的前提下寻找高确定性的交易机会。"
            "你的决策框架：趋势 → 动量 → 估值 → 催化剂 → 风险/收益比。"
        ),
        tools=[],  # Synthesises context from other agents — no direct data tools needed
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
