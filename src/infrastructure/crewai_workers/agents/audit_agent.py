"""Audit agent definition."""

from typing import Any, Optional

from crewai import Agent

def create_audit_agent(
    llm: Any,
    role: Optional[str] = None,
    goal: Optional[str] = None,
    backstory: Optional[str] = None,
) -> Agent:
    """Create the audit agent."""
    return Agent(
        role=role or "量化风控与数据审计专家",
        goal=goal or "发现并指出报告中的事实漏洞、夸张描述或可能的AI数据幻觉",
        backstory=backstory or "你是一位专注于对抗AI幻觉并精通金融指标的顶级风控风控官。",
        allow_delegation=False,
        llm=llm,
        verbose=True,
    )
