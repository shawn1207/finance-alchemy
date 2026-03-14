import time
from datetime import datetime
from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI


from ...config import load_yaml_config
from ...infrastructure.crewai_workers.agents import (
    create_fundamental_agent,
    create_strategy_agent,
    create_technical_agent,
    create_audit_agent,
)
from ...domain.repositories.analysis_repository import AnalysisRepository
from ..dto.analysis_dto import (
    FundamentalReport,
    StockAnalysisRequest,
    StockAnalysisResult,
    StrategyReport,
    TechnicalReport,
    AuditReport,
)


class AnalyzeStockUseCase:
    """Application-layer orchestrator for multi-agent stock analysis."""

    def __init__(self, llm=None, repository: AnalysisRepository = None) -> None:
        self._llm = llm
        self._repository = repository
        self._agents_config = load_yaml_config("agents.yaml")
        self._tasks_config = load_yaml_config("tasks.yaml")

    def _refine_agent_roles(self, stock_code: str, stock_name: str) -> None:
        """Use LLM to refine agent roles and backstories based on context."""
        if not self._llm or not self._agents_config:
            return

        print(f"✨ 正在使用大模型修饰 {stock_name} ({stock_code}) 的智能体角色...")
        for agent_key, config in self._agents_config.items():
            prompt = (
                f"你是一个分析专家。请根据股票 '{stock_name}' (代码: {stock_code}) 的行业背景、业务重点和当前市场地位，"
                f"优化以下智能体的 role, goal 和 backstory，使其在分析该特定股票时更具针对性。\n\n"
                f"原始配置:\n{config}\n\n"
                "输出格式必须是严格的 YAML (仅包含 role, goal, backstory 三个字段)。"
            )
            try:
                # Basic LLM call to get refined config
                response = self._llm.invoke(prompt)
                import yaml

                content = str(response.content)
                # Simple extraction of YAML from markdown code block if present
                if "```yaml" in content:
                    content = content.split("```yaml")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                refined_config = yaml.safe_load(content)
                if refined_config:
                    self._agents_config[agent_key].update(refined_config)
            except Exception as e:
                print(f"警告: 修饰智能体 {agent_key} 失败: {e}。将使用默认配置。")

    def execute(self, request: StockAnalysisRequest) -> StockAnalysisResult:
        """Run the analysis crew and return a structured result."""
        start_time = time.time()
        code = request.stock_code

        # 0. Fetch Stock Name for grounding
        from ...infrastructure.data_fetcher.akshare_fetcher import AkShareFetcher
        import asyncio
        _fetcher = AkShareFetcher()
        def _async_run(coro):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                     import concurrent.futures
                     with concurrent.futures.ThreadPoolExecutor() as pool:
                         return pool.submit(asyncio.run, coro).result()
                return loop.run_until_complete(coro)
            except RuntimeError:
                return asyncio.run(coro)
        
        stock_name = _async_run(_fetcher.get_stock_name(code))
        print(f"🚀 开始分析：{stock_name} ({code})")

        # 1. Dynamic role refinement
        if request.refine_roles:
            self._refine_agent_roles(code, stock_name)

        # 2. Sequential/Iterative Crew Execution Loop
        max_retries = 2
        current_retry = 0
        audit_log = []
        final_result = None

        while current_retry <= max_retries:
            # Initialize/Reset agents for each attempt to ensure fresh state if needed 
            # (or we could keep them, but resetting ensures prompt efficacy)
            fundamental_agent = create_fundamental_agent(
                llm=self._llm,
                role=self._agents_config.get("fundamental_agent", {}).get("role"),
                goal=self._agents_config.get("fundamental_agent", {}).get("goal"),
                backstory=self._agents_config.get("fundamental_agent", {}).get("backstory"),
            )
            technical_agent = create_technical_agent(
                llm=self._llm,
                role=self._agents_config.get("technical_agent", {}).get("role"),
                goal=self._agents_config.get("technical_agent", {}).get("goal"),
                backstory=self._agents_config.get("technical_agent", {}).get("backstory"),
            )
            strategy_agent = create_strategy_agent(
                llm=self._llm,
                role=self._agents_config.get("strategy_agent", {}).get("role"),
                goal=self._agents_config.get("strategy_agent", {}).get("goal"),
                backstory=self._agents_config.get("strategy_agent", {}).get("backstory"),
            )
            audit_agent = create_audit_agent(
                llm=self._llm,
                role=self._agents_config.get("audit_agent", {}).get("role"),
                goal=self._agents_config.get("audit_agent", {}).get("goal"),
                backstory=self._agents_config.get("audit_agent", {}).get("backstory"),
            )

            context_tasks: list[Task] = []
            current_date_str = datetime.now().strftime("%Y年%m月%d日")
            time_prompt = f"【系统安全提示：当前真实系统时间是 {current_date_str}。你的所有数据获取和分析逻辑必须严格遵守当前时间序列，绝对禁止套用过去的历史数据来编造现在的结论，否则将面临严重惩罚！】\n\n"
            
            feedback_prompt = ""
            if audit_log:
                feedback_prompt = f"【!!! 重大修正警告 !!!】\n上一轮分析因以下数据幻觉/事实错误被风控打回，请务必在本次分析中通过调用工具核实并修正：\n" + "\n".join(audit_log[-1:]) + "\n\n"

            # -- Fundamental task --------------------------------------------------
            if request.include_fundamental:
                f_config = self._tasks_config.get("fundamental_task", {})
                f_desc = f_config.get("description", "").format(code=f"{stock_name}({code})")
                fundamental_task = Task(
                    description=time_prompt + feedback_prompt + f_desc,
                    agent=fundamental_agent,
                    expected_output=f_config.get("expected_output", ""),
                    async_execution=True,
                    output_pydantic=FundamentalReport,
                )
                context_tasks.append(fundamental_task)

            # -- Technical task ----------------------------------------------------
            if request.include_technical:
                t_config = self._tasks_config.get("technical_task", {})
                t_desc = t_config.get("description", "").format(
                    code=f"{stock_name}({code})", kline_limit=request.kline_limit
                )
                technical_task = Task(
                    description=time_prompt + feedback_prompt + t_desc,
                    agent=technical_agent,
                    expected_output=t_config.get("expected_output", ""),
                    async_execution=True,
                    output_pydantic=TechnicalReport,
                )
                context_tasks.append(technical_task)

            # -- Strategy task -----------------------------------------------------
            s_config = self._tasks_config.get("strategy_task", {})
            s_desc = s_config.get("description", "").format(code=f"{stock_name}({code})")
            strategy_task = Task(
                description=time_prompt + feedback_prompt + s_desc,
                agent=strategy_agent,
                expected_output=s_config.get("expected_output", ""),
                context=context_tasks if context_tasks else None,
                output_pydantic=StrategyReport,
            )
            context_tasks.append(strategy_task)

            # -- Audit task --------------------------------------------------------
            a_config = self._tasks_config.get("audit_task", {})
            a_desc = a_config.get("description", "").format(code=f"{stock_name}({code})")
            audit_task = Task(
                description=time_prompt + a_desc,
                agent=audit_agent,
                expected_output=a_config.get("expected_output", ""),
                context=context_tasks,
                output_pydantic=AuditReport,
            )

            all_tasks = context_tasks + [audit_task]
            all_agents = [fundamental_agent, technical_agent, strategy_agent, audit_agent]

            crew = Crew(
                agents=all_agents,
                tasks=all_tasks,
                process=Process.sequential,
                verbose=True,
                cache=False,
                memory=False,
            )

            raw_result = crew.kickoff()
            
            # Extract current reports
            strategy_report = strategy_task.output.pydantic
            fundamental_report = fundamental_task.output.pydantic if request.include_fundamental else None
            technical_report = technical_task.output.pydantic if request.include_technical else None
            audit_report = audit_task.output.pydantic if hasattr(audit_task.output, "pydantic") else None

            if audit_report and audit_report.is_verified:
                print(f"✅ 审计通过 (Retry {current_retry})")
                final_result = StockAnalysisResult(
                    request=request,
                    fundamental=fundamental_report,
                    technical=technical_report,
                    strategy=strategy_report,
                    audit=audit_report,
                    audit_log=audit_log,
                    duration_seconds=time.time() - start_time,
                )
                break
            else:
                warnings = ", ".join(audit_report.risk_warnings) if audit_report else "未知审计错误"
                print(f"⚠️ 审计驳回 (Retry {current_retry}): {warnings}")
                audit_log.append(f"第 {current_retry+1} 次尝试驳回理由: {warnings}")
                current_retry += 1
                if current_retry > max_retries:
                    print("🚨 达到最大尝试次数，输出最后一份报告。")
                    final_result = StockAnalysisResult(
                        request=request,
                        fundamental=fundamental_report,
                        technical=technical_report,
                        strategy=strategy_report,
                        audit=audit_report,
                        audit_log=audit_log,
                        duration_seconds=time.time() - start_time,
                    )

        result = final_result

        # 4. Run Backtest and generate Raw Data Appendix
        raw_appendix_lines = [
            f"### 原始数据参照表 - {stock_name} ({code})",
            "这是在AI分析之前，从东方财富/新浪财经接口实时拉取的真实原始数据。如果在报告中发现有矛盾的数据，请以这里的客观数据为对比基准。",
            ""
        ]
        
        try:
            from ...infrastructure.data_fetcher.akshare_fetcher import AkShareFetcher
            from ...domain.services.backtesting_service import BacktestingService
            import asyncio

            # Fetch financial metrics for the appendix
            try:
                from ...infrastructure.data_fetcher.claw_fetcher import ClawFetcher
                _claw = ClawFetcher()
                claw_metrics = _async_run(_claw.fetch_financial_metrics(code))
                if isinstance(claw_metrics, dict) and "error" not in claw_metrics:
                    raw_appendix_lines.append("#### 官方核心财务指标 (Eastmoney High-Fidelity)")
                    raw_appendix_lines.append("| 指标名称 | 当前数值 | 详情/报表周期 |")
                    raw_appendix_lines.append("| -- | -- | -- |")
                    for k, v in claw_metrics.items():
                        if k.startswith("_"): continue
                        if isinstance(v, str) and "|" in v:
                            parts = v.split("|")
                            raw_appendix_lines.append(f"| {k} | {parts[0]} | {parts[1]} |")
                        else:
                            raw_appendix_lines.append(f"| {k} | {v} | - |")
                    raw_appendix_lines.append("")
                
                # Fetch technical indicators for appendix
                claw_tech = _async_run(_claw.fetch_technical_analysis(code))
                if isinstance(claw_tech, dict) and claw_tech.get("indicators"):
                    raw_appendix_lines.append("#### 官方深度技术指标实时数据")
                    raw_appendix_lines.append("| 指标名称 | 当前数值 |")
                    raw_appendix_lines.append("| -- | -- |")
                    for k, v in claw_tech["indicators"].items():
                        raw_appendix_lines.append(f"| {k} | {v} |")
                    raw_appendix_lines.append("")

                # Fallback to AkShare metrics if needed
                metrics_res = _async_run(_fetcher.get_financial_metrics(code))
                if isinstance(metrics_res, dict):
                    raw_appendix_lines.append("#### 核心财务指标查册")
                    raw_appendix_lines.append("| 指标名称 | 当前数值 |")
                    raw_appendix_lines.append("| -- | -- |")
                    for k, v in metrics_res.items():
                        raw_appendix_lines.append(f"| {k} | {v} |")
                    raw_appendix_lines.append("")
                elif isinstance(metrics_res, str):
                    raw_appendix_lines.append("#### 核心财务/行情信息")
                    raw_appendix_lines.append("```text\n" + metrics_res + "\n```\n")
            except Exception as e:
                pass


            # Fetch Kline and Backtest
            df = _async_run(_fetcher.fetch_kline(code, interval="daily", limit=60))
            if not df.empty:
                backtest_result = BacktestingService.run_simple_backtest(df, days=30)
                result.backtest = backtest_result
                
                # Append last 5 days K-line to raw data appendix
                raw_appendix_lines.append("#### 近5日极简K线数据查册")
                tail_df = df.tail(5)
                markdown_table = tail_df.to_markdown(index=False)
                if markdown_table:
                    raw_appendix_lines.append(markdown_table)
                    raw_appendix_lines.append("")

            # Set the appendix
            result.raw_data_appendix = "\n".join(raw_appendix_lines)

        except Exception as bte:
            print(f"警告: 历史回测失败: {bte}")

        # 5. Save to repository if available
        if self._repository:
            try:
                self._repository.save(result)
            except Exception as e:
                print(f"警告: 结果保存至数据库失败: {e}")

        return result
