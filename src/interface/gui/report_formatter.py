from datetime import datetime


def generate_markdown_report(result: dict) -> str:
    """Generate a clean, visually rich Markdown report from the analysis results."""
    req = result.get('request', {})
    fund = result.get('fundamental', {})
    tech = result.get('technical', {})
    strat = result.get('strategy', {})
    audit = result.get('audit', {})
    backtest = result.get('backtest', {})
    raw_appendix = result.get('raw_data_appendix', '')

    code = req.get('stock_code', '未知')
    stock_name = fund.get('stock_name', code)  # [维度3] 显示股票名称，而非只显示代码

    decision = strat.get('decision', '未知')
    try:
        confidence = float(strat.get('confidence', 0)) * 100
    except (ValueError, TypeError):
        confidence = 0.0

    risk = strat.get('risk_level', '未知')
    pos = strat.get('position_size_pct', 0)
    stop = strat.get('stop_loss_pct', 0)
    profit = strat.get('take_profit_pct', 0)

    roe = fund.get('roe', 'N/A')
    pe = fund.get('pe_ratio', 'N/A')
    growth = fund.get('revenue_growth', 'N/A')
    gross_margin = fund.get('gross_margin', 'N/A')
    net_profit_growth = fund.get('net_profit_growth', 'N/A')
    sentiment = fund.get('sentiment', 'N/A')

    trend = tech.get('trend', 'N/A')
    rsi = tech.get('rsi', 'N/A')
    macd = tech.get('macd_signal', 'N/A')
    support = tech.get('support_level', 'N/A')
    resistance = tech.get('resistance_level', 'N/A')
    vol = "⚠️ 异常放量" if tech.get('volume_anomaly') else "✅ 正常"

    fund_text = fund.get('analysis_text', '暂无详细分析')
    tech_text = tech.get('analysis_text', '暂无详细分析')
    strat_text = strat.get('rationale', '暂无详细分析')

    # [维度4] 信息负荷：决策用高亮颜色区分，视觉聚焦
    if decision == "BUY":
        decision_emoji = "🟢"
        decision_color = "#34c759"
        decision_label = "建议买入"
    elif decision == "SELL":
        decision_emoji = "🔴"
        decision_color = "#ff3b30"
        decision_label = "建议卖出"
    else:
        decision_emoji = "🟡"
        decision_color = "#ffcc00"
        decision_label = "建议持有/观望"

    # [维度3] 输出清晰度：报告头部突出核心决策
    md = f"""# 🧪 Finance Alchemy 分析报告
## {stock_name}（{code}）
> 📅 **分析时间：** {datetime.now().strftime('%Y年%m月%d日 %H:%M')} | ⚙️ 由 CrewAI 多智能体团队生成

---

## {decision_emoji} 核心决策：{decision_label}

| 置信度 | 风险评级 | 建议仓位 | 止损位 | 止盈目标 |
| :---: | :---: | :---: | :---: | :---: |
| **{confidence:.1f}%** | **{risk}** | **{pos}%** | **-{stop}%** | **+{profit}%** |

> **策略核心逻辑：**
> {strat_text.replace(chr(10), chr(10) + '> ')}

---
"""

    # [维度8] 解释性：审计结果让用户理解 AI 的可信度
    if audit:
        is_verified = audit.get("is_verified", False)
        audit_icon = "✅ 数据已通过审计" if is_verified else "⚠️ 数据存在疑点"
        warnings = audit.get("risk_warnings", [])
        warnings_md = ""
        if warnings:
            warnings_md = "\n\n**🚨 风控警告（请重点关注以下问题）：**\n"
            for w in warnings:
                warnings_md += f"- ⚠️ {w}\n"

        md += f"""
### 🛡️ AI 审计结论：{audit_icon}
> {audit.get('audit_notes', '无审计意见')}
{warnings_md}

---
"""

    # 回测结果（如有）
    if backtest and backtest.get("status") == "success":
        md += f"""
### ⏱️ 近期历史回测（{backtest.get('period_days', 30)} 天）

| 回测起始日 | 期初价格 | 最高收益 | 当前收益率 | 最大回撤 | 最新收盘 |
| :---: | :---: | :---: | :---: | :---: | :---: |
| {backtest.get('entry_date')} | ¥{backtest.get('entry_price')} | +{backtest.get('max_return')}% | **{backtest.get('returns_pct')}%** | {backtest.get('max_drawdown')}% | ¥{backtest.get('current_price')} |

---
"""

    # [维度4] 负荷管理：关键指标一览表，详细分析折叠
    md += f"""
### 📊 基本面快照

| 指标 | 数值 | 指标 | 数值 |
| :--- | :--- | :--- | :--- |
| ROE（净资产收益率）| {roe}% | 市盈率 PE（TTM）| {pe} 倍 |
| 营收增速 | {growth}% | 归母净利润增速 | {net_profit_growth}% |
| 销售毛利率 | {gross_margin}% | 市场情绪 | {sentiment} |

<details>
<summary><b>🔍 展开基本面详细分析报告...</b></summary>
<br>

{fund_text}

</details>

---

### 📈 技术面快照

| 指标 | 数值 | 指标 | 数值 |
| :--- | :--- | :--- | :--- |
| 当前趋势 | **{trend}** | RSI 指标 | {rsi} |
| MACD 信号 | {macd} | 成交量异动 | {vol} |
| 支撑位 | {support} | 压力位 | {resistance} |

<details>
<summary><b>🔍 展开技术面详细分析报告...</b></summary>
<br>

{tech_text}

</details>

---

*⚠️ 免责声明：本报告由 AI 自动生成，仅供参考，不构成投资建议。投资有风险，交易需谨慎。*
"""

    # 原始数据附录（折叠）
    if raw_appendix:
        md += f"""
<details>
<summary><b>📎 原始数据附录（供审计核查使用）</b></summary>
<br>

{raw_appendix}

</details>
"""

    return md


def generate_pdf_from_md(md_content: str, filename: str) -> str:
    """Convert Markdown content to a PDF file and return the file path."""
    try:
        import markdown
        from xhtml2pdf import pisa
        import os

        html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

        html_with_css = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: a4; margin: 2cm; }}
                body {{ font-family: Helvetica, Arial, sans-serif; color: #1d1d1f; line-height: 1.7; font-size: 13px; }}
                h1 {{ color: #0071e3; border-bottom: 3px solid #0071e3; padding-bottom: 10px; font-size: 22px; }}
                h2 {{ color: #1d1d1f; border-left: 5px solid #0071e3; padding-left: 12px; margin-top: 24px; font-size: 16px; }}
                h3 {{ color: #444; margin-top: 18px; font-size: 14px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 12px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px 14px; text-align: left; }}
                th {{ background-color: #f5f5f7; font-weight: bold; color: #0071e3; }}
                tr:nth-child(even) {{ background-color: #fafafa; }}
                blockquote {{ background: #f0f7ff; border-left: 4px solid #0071e3; margin: 12px 0; padding: 10px 16px; border-radius: 4px; color: #333; }}
                p {{ margin: 8px 0; }}
                em {{ color: #888; font-size: 11px; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        output_dir = ".cache/exports"
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = f"{filename}.pdf"

        with open(pdf_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html_with_css, dest=f)

        if pisa_status.err:
            return ""

        return pdf_path
    except Exception as e:
        print(f"[PDF Generation] Error: {e}")
        return ""
