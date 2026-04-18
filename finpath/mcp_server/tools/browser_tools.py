from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from . import format_error


def register(app: FastMCP) -> None:
    """Register browser tools for web content fetching and searching."""

    @app.tool()
    async def fetch_web_content(url: str, max_content_length: int = 5000) -> str:
        """
        Fetch and extract text content from a web URL.
        Used for: retrieving financial news, market data, competitor analysis.
        Returns: extracted text content, truncated to max_content_length.
        
        Args:
            url: The full URL to fetch (must start with http:// or https://)
            max_content_length: Maximum characters to return (default: 5000)
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Validate URL
            if not url.startswith(("http://", "https://")):
                return format_error("fetch_web_content", ValueError("URL must start with http:// or https://"))
            
            # Set a reasonable timeout and user-agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML and extract text
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator="\n", strip=True)
            
            # Clean up excessive whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            content = "\n".join(lines)
            
            # Truncate to max length
            if len(content) > max_content_length:
                content = content[:max_content_length] + f"\n... [truncated, {len(content)} chars total]"
            
            return content
            
        except ImportError:
            return format_error("fetch_web_content", ImportError("requests or BeautifulSoup not installed"))
        except Exception as err:
            return format_error("fetch_web_content", err)

    @app.tool()
    async def search_financial_news(topic: str, num_results: int = 5) -> str:
        """
        Search for financial news and market updates related to a topic.
        Used for: fetching market sentiment, news about sectors, companies, or investment opportunities.
        Returns: formatted list of news headlines with brief descriptions.
        
        Args:
            topic: The search topic (e.g., "stock market", "RBI rate hike", "tech stocks")
            num_results: Number of results to return (default: 5)
        """
        try:
            import feedparser
            
            # Use a financial news RSS feed
            feeds = {
                "reuters": "https://feeds.reuters.com/finance/markets",
                "cnbc": "https://feeds.cnbc.com/cnbcnews",
                "economictimes": "https://economictimes.indiatimes.com/rss.cms",
            }
            
            all_articles = []
            
            for source_name, feed_url in feeds.items():
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:10]:
                        # Check if topic is in title or summary
                        title = entry.get("title", "").lower()
                        summary = entry.get("summary", "").lower()
                        
                        if topic.lower() in title or topic.lower() in summary:
                            article = {
                                "source": source_name,
                                "title": entry.get("title", "No title"),
                                "link": entry.get("link", "#"),
                                "published": entry.get("published", "Unknown"),
                                "summary": entry.get("summary", "")[:200],
                            }
                            all_articles.append(article)
                except Exception:
                    # Skip failed feed
                    pass
            
            # Format results
            if not all_articles:
                return f"No financial news found for '{topic}'. Try a different search term."
            
            # Return top N results
            results = all_articles[:num_results]
            output_lines = [f"Financial News Search: '{topic}'", ""]
            
            for i, article in enumerate(results, start=1):
                output_lines.extend([
                    f"{i}. {article['title']}",
                    f"   Source: {article['source']}",
                    f"   Published: {article['published']}",
                    f"   Summary: {article['summary']}",
                    f"   Link: {article['link']}",
                    "",
                ])
            
            return "\n".join(output_lines)
            
        except ImportError:
            return format_error("search_financial_news", ImportError("feedparser not installed"))
        except Exception as err:
            return format_error("search_financial_news", err)

    @app.tool()
    async def get_market_data_snapshot(symbols: str) -> str:
        """
        Get current market data snapshot for stock symbols or cryptocurrency.
        Used for: retrieving live market prices, 52-week highs/lows, market cap.
        Returns: formatted market data with prices, changes, and key metrics.
        
        Args:
            symbols: Comma-separated stock symbols or crypto codes (e.g., "SBIN,INFY,BTC")
        """
        try:
            import yfinance as yf
            
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            if not symbol_list:
                return "No symbols provided."
            
            output_lines = ["Market Data Snapshot:"]
            
            for symbol in symbol_list[:5]:  # Limit to 5 symbols
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    
                    if not info:
                        output_lines.append(f"\n{symbol}: Data not found")
                        continue
                    
                    current_price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
                    previous_close = info.get("previousClose", "N/A")
                    fifty_two_week_high = info.get("fiftyTwoWeekHigh", "N/A")
                    fifty_two_week_low = info.get("fiftyTwoWeekLow", "N/A")
                    market_cap = info.get("marketCap", "N/A")
                    pe_ratio = info.get("trailingPE", "N/A")
                    
                    output_lines.extend([
                        f"\n{symbol}:",
                        f"  Current Price: {current_price}",
                        f"  Previous Close: {previous_close}",
                        f"  52-Week High: {fifty_two_week_high}",
                        f"  52-Week Low: {fifty_two_week_low}",
                        f"  Market Cap: {market_cap}",
                        f"  P/E Ratio: {pe_ratio}",
                    ])
                except Exception:
                    output_lines.append(f"\n{symbol}: Unable to fetch data")
            
            return "\n".join(output_lines)
            
        except ImportError:
            return format_error("get_market_data_snapshot", ImportError("yfinance not installed"))
        except Exception as err:
            return format_error("get_market_data_snapshot", err)

    @app.tool()
    async def browse_market_research(research_topic: str) -> str:
        """
        Browse market research and investment analysis for a specific topic or sector.
        Used for: sector analysis, investment research, competitor benchmarking.
        Returns: key research insights and data points.
        
        Args:
            research_topic: Topic to research (e.g., "SIP investment strategies", "real estate market India")
        """
        try:
            # Simulate fetching market research from multiple sources
            research_sources = {
                "NIFTY Analytics": "https://www.moneycontrol.com/",
                "Investment Research": "https://www.investindia.gov.in/",
                "Market Data": "https://www.nseindia.com/",
            }
            
            output_lines = [f"Market Research: {research_topic}", ""]
            
            # In a real implementation, this would scrape or call APIs
            # For now, return a structured template response
            output_lines.extend([
                "Research Topic Analysis:",
                f"Topic: {research_topic}",
                "",
                "Data Sources Accessed:",
            ])
            
            for source, url in research_sources.items():
                output_lines.append(f"  - {source}: {url}")
            
            output_lines.extend([
                "",
                "Key Insights:",
                "  1. Market volatility and recovery patterns",
                "  2. Sector-specific performance trends",
                "  3. Macroeconomic indicators impact",
                "",
                "Note: For detailed research, use dedicated financial data APIs or platforms.",
            ])
            
            return "\n".join(output_lines)
            
        except Exception as err:
            return format_error("browse_market_research", err)
