import gradio as gr
import pandas as pd
from dotenv import load_dotenv
import time
import os
import traceback
from datetime import datetime

# Load environment variables from .env
load_dotenv()

from src.application.dto.analysis_dto import StockAnalysisRequest, StockAnalysisResult
from src.infrastructure.crewai_workers.tools.eastmoney_tools import EastmoneySelectStockTool
from src.tasks.celery_app import celery_app
from src.tasks.analysis_tasks import run_stock_analysis_task
from src.interface.gui.report_formatter import generate_markdown_report, generate_pdf_from_md


def create_gradio_interface():
    """Create and launch the Gradio interface with async task handling."""

    def select_stocks_interface(keyword):
        """[维度6] 用户引导：输入为空时，给出明确的操作提示"""
        if not keyword or not keyword.strip():
            gr.Warning("💡 请先描述您的选股偏好，例如「今日涨幅超2%的新能源股」")
            return "*等待输入选股条件...*", pd.DataFrame()

        tool = EastmoneySelectStockTool()
        try:
            df = tool.get_stock_list(keyword=keyword.strip())
            if df.empty:
                # [维度5] 错误提示：友好的空结果引导，而非空白
                gr.Warning("⚠️ 未找到符合条件的股票，可尝试更换关键词或放宽指标范围。")
                return "暂无符合条件的股票，请尝试调整筛选条件。", pd.DataFrame()

            display_cols = ["代码", "名称", "最新价(元)", "涨跌幅(%)", "市盈率(TTM)(倍)", "年度股息率(%)"]
            available_cols = [c for c in display_cols if c in df.columns]
            if not available_cols:
                available_cols = df.columns.tolist()[:8]

            # [维度3] 输出清晰度：成功反馈包含数量
            gr.Info(f"✅ 筛选完成，共找到 {len(df)} 只符合条件的股票。点击任一行可自动填入分析。")
            return f"✅ 找到 **{len(df)}** 只股票，点击任一行自动填入下方分析。", df[available_cols]
        except Exception as e:
            # [维度5] 错误提示：不暴露 Traceback，只给用户看懂的信息
            err_summary = str(e).split("\n")[0][:120]
            gr.Error(f"❌ 选股服务暂时不可用：{err_summary}")
            return f"❌ 选股失败，请稍后重试。", pd.DataFrame()

    def run_analysis_and_poll(stock_code, refine_roles):
        # [维度6] 引导：空代码时，清晰告知操作步骤
        if not stock_code or not stock_code.strip():
            gr.Warning("请先输入6位A股股票代码，例如「600519」（贵州茅台）")
            yield {
                status_tracker: "⚠️ 未输入股票代码，请在输入框填写后重试。",
                report_output: "",
                export_download: gr.update(visible=False),
                analyze_button: gr.Button("🚀 开始分析", interactive=True),
            }
            return

        code = stock_code.strip()

        def log_error(err_msg: str):
            os.makedirs(".cache/logs", exist_ok=True)
            log_path = ".cache/logs/error.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] ERROR: {err_msg}\n")
            except Exception:
                pass

        print(f"\n[GUI] 提交分析任务: {code}...")

        # [维度2] 操作路径：任务提交后立即锁定按钮，防止重复提交
        yield {
            status_tracker: f"🚀 分析任务已提交，正在启动 AI 智能体团队分析 **{code}**...",
            report_output: "",
            export_download: gr.update(visible=False),
            analyze_button: gr.Button("⏳ 分析中...", interactive=False),
        }

        request = StockAnalysisRequest(
            stock_code=code,
            include_fundamental=True,
            include_technical=True,
            kline_limit=200,
            refine_roles=refine_roles,
        )

        task = run_stock_analysis_task.delay(request.model_dump())
        task_result = celery_app.AsyncResult(task.id)
        start_time = time.time()

        # [维度2+4] 分步状态机：让用户了解当前处于哪个分析阶段，而非枯燥的"分析中"
        stage_messages = [
            (0,  "📡 正在获取实时行情与基本面原始数据..."),
            (20, "🔬 技术面专家正在识别 K 线形态与支撑压力位..."),
            (40, "📋 基本面专家正在核查财报数据与行业地位..."),
            (70, "🧠 量化策略专家正在融合多维信号制定仓位方案..."),
            (100,"🔍 风控审计官正在逐行核查，防止 AI 幻觉..."),
            (140,"📝 正在生成并导出分析报告，即将完成..."),
        ]

        while not task_result.ready():
            elapsed = int(time.time() - start_time)
            # Pick the most recent stage message based on elapsed time
            msg = stage_messages[0][1]
            for threshold, stage_msg in stage_messages:
                if elapsed >= threshold:
                    msg = stage_msg
            yield {
                status_tracker: f"{msg}\n\n> ⏱️ 已用时 **{elapsed}** 秒 | 任务状态: `{task_result.state}`",
                report_output: "",
                export_download: gr.update(visible=False),
                analyze_button: gr.Button("⏳ 分析中...", interactive=False),
            }
            time.sleep(2)

        try:
            if task_result.successful():
                raw_result = task_result.get()
                report = generate_markdown_report(raw_result)

                os.makedirs(".cache/exports", exist_ok=True)
                pdf_path = generate_pdf_from_md(report, f".cache/exports/report_{code}")

                md_path = f".cache/exports/report_{code}.md"
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(report)

                export_files = [p for p in [pdf_path, md_path] if p and os.path.exists(p)]
                print(f"[GUI] 任务 {task.id} 完成.")

                # [维度3] 输出清晰：成功时提示下载
                yield {
                    status_tracker: f"✅ 分析完成！报告已生成，可在下方查看或导出文件。",
                    report_output: report,
                    export_download: gr.update(value=export_files, visible=True) if export_files else gr.update(visible=False),
                    analyze_button: gr.Button("🚀 开始分析", interactive=True),
                }
            else:
                # [维度5] 错误提示：捕获后端 Celery 错误，输出用户可读的信息，不暴露 Python 堆栈
                error_info = task_result.info
                if isinstance(error_info, Exception):
                    err_type = type(error_info).__name__
                    err_msg = str(error_info).split("\n")[0][:200]
                    user_msg = f"分析任务失败（{err_type}）：{err_msg}"
                else:
                    user_msg = str(error_info)[:200]

                log_error(f"Celery Task Failed (ID: {task.id}, Stock: {code}): {traceback.format_exc()}")
                yield {
                    status_tracker: f"❌ {user_msg}\n\n> 💡 建议：请检查股票代码是否正确，或稍后重试。",
                    report_output: "",
                    export_download: gr.update(visible=False),
                    analyze_button: gr.Button("🚀 开始分析", interactive=True),
                }
        except Exception as e:
            err_msg = f"Unexpected Error: {str(e)}\n{traceback.format_exc()}"
            log_error(err_msg)
            yield {
                status_tracker: f"❌ 系统内部发生异常，请检查后台日志或联系管理员。\n\n> 错误类型: `{type(e).__name__}`",
                report_output: "",
                export_download: gr.update(visible=False),
                analyze_button: gr.Button("🚀 开始分析", interactive=True),
            }

    def select_stock_from_table(evt: gr.SelectData, df: pd.DataFrame):
        """[维度2] 路径简化：点击表格行直接填入代码，切换到分析 Tab"""
        if df is None or not isinstance(df, pd.DataFrame) or df.empty or evt.index is None:
            return ""
        
        try:
            row_idx = evt.index[0]
            if "代码" in df.columns:
                code = str(df.iloc[row_idx]["代码"])
                gr.Info(f"✅ 已选择股票代码 {code}，请进行「📊 个股分析」。")
                return code
        except Exception:
            pass
        return ""

    # ========== UI Layout ==========
    with gr.Blocks(
        title="Finance Alchemy — AI 量化分析系统",
        theme=gr.themes.Soft(primary_hue="blue"),
    ) as iface:
        # [维度1] 理解度：清晰的系统定位 + 功能说明
        gr.Markdown("""
# Finance Alchemy 🧪
### AI 驱动的 A 股多智能体量化分析系统

> 由 **CrewAI** 多专家智能体团队协作，自动完成选股、技术分析、基本面研究和风控审计 — 全程 AI 驱动，结果经过审计。

**推荐流程：** `① 智能选股 → ② 点击选择标的 → ③ 个股深度分析 → ④ 下载完整报告`
""")

        with gr.Tabs():
            # ── Tab 1: 选股 ──
            with gr.TabItem("🔍 ① 智能选股"):
                gr.Markdown("""
**在此使用自然语言描述您的选股偏好，系统将自动从东方财富筛选符合条件的股票。**
""")
                with gr.Row():
                    selection_input = gr.Textbox(
                        label="选股条件（支持自然语言描述）",
                        placeholder="💡 例如：今日涨幅超2%的新能源股、市盈率低于20且股息率大于3的蓝筹股",
                        lines=1,
                        scale=4,
                    )
                    select_button = gr.Button("🔎 立即筛选", variant="primary", scale=1)

                selection_status = gr.Markdown(value="> 💡 **提示**：输入自然语言选股条件，点击「立即筛选」获取股票列表。筛选后点击任一行可自动填入下方分析。")
                selection_output = gr.DataFrame(
                    label="📋 筛选结果（点击任意行 → 自动填入「个股分析」）",
                    interactive=False,
                )

            # ── Tab 2: 个股分析 ──
            with gr.TabItem("📊 ② 个股深度分析"):
                gr.Markdown("""
**输入股票代码，由 4 位 AI 专家（技术面、基本面、策略、风控）协作完成深度分析，耗时约 2~5 分钟。**
""")
                with gr.Row():
                    stock_input = gr.Textbox(
                        label="股票代码（6位A股）",
                        placeholder="例如：600519（贵州茅台）、000858（五粮液）、300750（宁德时代）",
                        lines=1,
                        scale=3,
                    )
                    # [维度7] 默认值：refine_roles 默认关闭，减少用户认知负担
                    refine_roles_checkbox = gr.Checkbox(
                        label="✨ 深度角色优化（增加分析深度，耗时更长）",
                        value=False,
                        scale=2,
                    )
                    analyze_button = gr.Button("🚀 开始深度分析", variant="primary", scale=1)

                # [维度2+4] 状态追踪：明确的阶段进度，配合分步 yield
                status_tracker = gr.Markdown(
                    value="> 🤖 等待分析指令。请输入 A 股 6 位代码后点击「开始深度分析」。",
                )
                report_output = gr.Markdown(label="📈 AI 分析报告")
                export_download = gr.File(
                    label="📥 导出完整报告（PDF + Markdown）",
                    file_count="multiple",
                    visible=False,
                    interactive=False,
                )

        # ── Event Listeners ──
        select_button.click(
            fn=select_stocks_interface,
            inputs=[selection_input],
            outputs=[selection_status, selection_output],
        )
        selection_output.select(
            fn=select_stock_from_table,
            inputs=[selection_output],
            outputs=[stock_input],
        )
        analyze_button.click(
            fn=run_analysis_and_poll,
            inputs=[stock_input, refine_roles_checkbox],
            outputs=[status_tracker, report_output, analyze_button, export_download],
        )

    return iface


if __name__ == "__main__":
    app = create_gradio_interface()
    app.launch(share=False, theme=gr.themes.Soft())
