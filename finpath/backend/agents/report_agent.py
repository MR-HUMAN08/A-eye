from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from agents.behavioral_agent import analyze_transactions
from agents.goal_agent import calculate_goal_plan
from agents.macro_agent import macro_climate
from agents.portfolio_agent import recommend_portfolio
from agents.sentiment_agent import analyze_news_sentiment
from agents.tax_agent import optimize_tax
from agents.audit import build_audit


def generate_monthly_report(profile: dict, tx_csv: str, session_id: str) -> dict:
    behavior = analyze_transactions(tx_csv, session_id)
    goal = calculate_goal_plan(profile, behavior["monthly_variable_spend"], session_id)
    portfolio = recommend_portfolio(profile, goal, session_id)
    tax = optimize_tax(profile, session_id)
    sentiment = analyze_news_sentiment(session_id)
    macro = macro_climate(session_id)

    report_dir = Path(__file__).resolve().parents[1] / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / f"finpath_report_{datetime.now().strftime('%Y%m')}.pdf"

    c = canvas.Canvas(str(out_path), pagesize=A4)
    y = 800
    lines = [
        f"FinPath Monthly CFO Report - {datetime.now().strftime('%B %Y')} - {profile.get('name', 'Current User')}",
        "Executive Summary:",
        f"- Variable spend: {behavior['monthly_variable_spend']}",
        f"- Goal feasibility: {goal['goal_feasibility']}",
        "- Portfolio recommendation generated",
        f"- Tax saved estimate: {tax['tax_saved']}",
        f"- Market signal: {macro['macro_signal']}",
        "Recommendations next month:",
        "1) Reduce food delivery by 20%.",
        "2) Automate house-goal SIP transfer.",
        "3) Fill 80C/80D tax headroom.",
    ]
    for line in lines:
        c.drawString(40, y, line[:120])
        y -= 18
    c.showPage()
    c.save()

    audit = build_audit(
        "report_agent",
        [
            "Step 1: Called behavioral, goal, portfolio, tax, sentiment, and macro agents internally.",
            "Step 2: Compiled decision-ready sections into monthly report layout.",
            "Step 3: Generated and saved PDF report under backend/reports.",
        ],
        ["multi_agent_orchestration"],
        "high",
        "passed",
        session_id=session_id,
    )
    return {
        "pdf_path": str(out_path),
        "report_summary": {
            "behavioral": behavior["summary"],
            "goal": goal["summary"],
            "portfolio": portfolio["summary"],
            "tax_saved": tax["tax_saved"],
            "sentiment_count": sentiment["headlines_analyzed"],
        },
        **audit,
    }
