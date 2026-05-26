"""Bright Data MCP + SERP helpers for macro/social context."""

import json
import os

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()


def _format_tool_result(result) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        parts = []
        for item in result:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(result)


async def _invoke_mcp_tool(tool_name: str, arguments: dict) -> str:
    bd_token = os.getenv("BRIGHTDATA_TOKEN")
    if not bd_token:
        raise ValueError("Missing BRIGHTDATA_TOKEN")

    client = MultiServerMCPClient({
        "bright_data": {
            "url": f"https://mcp.brightdata.com/mcp?token={bd_token}",
            "transport": "streamable_http",
        }
    })
    tools = {t.name: t for t in await client.get_tools()}
    tool = tools.get(tool_name)
    if not tool:
        available = ", ".join(sorted(tools.keys()))
        raise ValueError(f"MCP tool '{tool_name}' not found (available: {available})")

    result = await tool.ainvoke(arguments)
    return _format_tool_result(result)


async def _serp_macro_fallback(query_topic: str) -> str:
    from brightdata_utils import get_market_trends_serp, parse_serp_results

    serp_data = await get_market_trends_serp(
        f"{query_topic} crypto market macroeconomic context"
    )
    parsed = parse_serp_results(serp_data)
    if parsed.get("error"):
        return (
            "Macro analysis unavailable: SERP fallback failed "
            f"({parsed.get('error')}: {parsed.get('details', '')})"
        )

    lines = []
    for item in parsed.get("organic_results", [])[:5]:
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        if title:
            lines.append(f"- {title}: {snippet}".strip())

    if not lines:
        return "Macro analysis unavailable: no SERP results returned."

    return "Recent macro context from search:\n" + "\n".join(lines)


async def get_brightdata_market_context(query_topic: str, tool_group: str = None) -> str:
    """
    Fetch macro or topical context via Bright Data MCP (search_engine) with SERP fallback.
    """
    if tool_group == "social":
        search_query = f"{query_topic} social media sentiment crypto"
    elif tool_group == "ecommerce":
        search_query = f"{query_topic} crypto hardware market pricing"
    else:
        search_query = f"{query_topic} crypto market macroeconomic trends 2026"

    try:
        return await _invoke_mcp_tool("search_engine", {"query": search_query})
    except Exception as e:
        print(f"⚠️ Bright Data MCP Error: {e}")
        try:
            return await _serp_macro_fallback(query_topic)
        except Exception as serp_err:
            print(f"⚠️ Bright Data SERP fallback error: {serp_err}")
            return "Could not retrieve real-time data due to an upstream connection anomaly."


async def get_brightdata_ecommerce_data(product_query: str) -> str:
    return await get_brightdata_market_context(product_query, tool_group="ecommerce")


async def get_brightdata_social_sentiment(topic: str) -> str:
    return await get_brightdata_market_context(topic, tool_group="social")
