"""Technical analysis CrewAI agent factory."""

from crewai import Agent

from ..tools.technical_tools import (
    CalculateTechnicalIndicatorsTool,
    DetectVolumeAnomalyTool,
    FetchKLineTool,
    FetchRealtimeQuoteTool,
)


def create_technical_agent(llm=None, role=None, goal=None, backstory=None) -> Agent:
    """Create the technical analysis agent.

    This agent reads price/volume action, computes indicators, and identifies
    trend direction, momentum and anomalies in trading activity.
    """
    return Agent(
        role=role or "A股技术分析专家",
        goal=goal or (
            "通过量价关系和多维技术指标全面分析A股个股走势，"
            "精准识别当前市场趋势、超买超卖状态和主力资金动向，"
            "为交易策略提供客观的技术面依据。"
        ),
        backstory=backstory or (
            "你是一位专注A股市场15年的技术分析师，精通MA、RSI、MACD、KDJ、布林带等指标。"
            "你善于在噪音中识别真实信号，特别擅长通过成交量异常发现主力操盘行为。"
            "你坚持用数据说话，拒绝主观臆测，每一个判断都有充分的技术指标作为支撑。"
            "你深知趋势的重要性：顺势而为是稳定盈利的核心原则。"
        ),
        tools=[
            FetchKLineTool(),
            CalculateTechnicalIndicatorsTool(),
            DetectVolumeAnomalyTool(),
            FetchRealtimeQuoteTool(),
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )
