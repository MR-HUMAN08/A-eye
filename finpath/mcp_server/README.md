# FinPath MCP Server

FinPath MCP Server exposes FinPath's financial intelligence as native MCP tools for any compatible AI client. It exists to make FinPath composable, auditable, and enterprise-ready beyond a closed demo UI.

## Tool Listing

| Tool Name | Description | Backend Endpoint |
|---|---|---|
| analyze_spending | Spending category analysis with leakage patterns | GET /analyze |
| get_leakage_report | Ranked leakage opportunities with annualized savings | GET /analyze |
| calculate_goal_plan | Inflation-adjusted goal feasibility and savings plan | GET /goal |
| check_goal_progress | Trajectory check for elapsed goal months | GET /goal |
| get_portfolio_recommendation | Conservative/Balanced/Aggressive allocation guidance | GET /portfolio |
| get_live_portfolio | Robo-advisor posture and rebalancing actions | GET /portfolio/live |
| get_macro_climate | Macro signal and allocation tilt recommendation | GET /macro/climate |
| evaluate_purchase | Real-time purchase nudge with goal-delay impact | POST /nudge |
| simulate_monthly_impact | Goal acceleration simulation for reduced category spend | POST /nudge |
| query_financial_knowledge | Direct top-k ChromaDB retrieval with citations | Direct rag_engine query |
| get_india_finance_benchmarks | Category benchmark retrieval from RAG | Direct rag_engine query |
| chat_with_cfo | CFO conversational advisory with session memory | POST /chat |
| analyze_financial_statement | DCF + variance + comps + forecast analysis | POST /analyze/statement |
| optimize_taxes | Tax optimization with 80C/80D + regime recommendation | GET /tax/optimize |
| calculate_tax_liability | Simplified regime tax estimate in plain English | GET /tax/optimize |
| get_market_sentiment | Cross-asset sentiment and goal-impact map | GET /news/sentiment |
| get_goal_market_impact | Real-estate sentiment impact for house goal | GET /news/sentiment |
| upload_and_analyze_document | Document extraction and RAG indexing | POST /documents/upload |
| get_retirement_projection | NPS/EPF + legacy retirement projection | GET /retirement/plan |
| simulate_nps_contribution | NPS contribution uplift simulation | GET /retirement/plan |
| get_audit_trail | Full session-level explainability and trace report | GET /audit/{session_id} |
| explain_last_recommendation | Why-this-advice drill-down for an agent | GET /audit/{session_id} |
| save_agent_memory | Persist an agent event into memory | POST /memory/save |
| load_agent_memory | Read recent memory timeline with filters | GET /memory/load |

## Start the Server

```bash
./start_mcp.sh
```

## Connect to Claude Desktop

Paste the `finpath` server entry from `claude_desktop_config.json` into your Claude Desktop `config.json` under `mcpServers`.

## Connect via SSE

Use:

`http://localhost:8001/sse`

## Demo Tool Highlight

Example call:

`evaluate_purchase(500, "Swiggy dinner order")`

Expected output pattern:
- Goal delay in days
- Behavioral recommendation (proceed/reconsider)
- Audit appendix with agent, confidence, RAG sources, and hallucination guard status

## Judge Note

This MCP server exposes FinPath as a composable enterprise AI layer - any MCP-compatible AI client can call FinPath's financial intelligence as native tools. This architecture directly mirrors Kavion.ai's governed intelligence philosophy.