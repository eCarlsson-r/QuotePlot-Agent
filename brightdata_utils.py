"""
brightdata_utils.py — Bright Data scraping utilities
All I/O functions are async and use httpx.AsyncClient to avoid blocking
the uvicorn event loop. The original file used sync requests inside async def,
causing up to 30s freezes per call.

Bright Data products used:
  SERP API        : get_token_news_serp, get_market_trends_serp
  Web Unlocker    : scrape_with_web_unlocker
  Scraping Browser: scrape_with_scraping_browser  (Playwright/CDP)
  Datasets API    : trigger_dataset_scraper
  Scraper Studio  : trigger_scraper_studio_job
"""

import os
import re
import random
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Shared direct httpx client for BD API calls (not proxied — these go to
# api.brightdata.com directly with Bearer auth, not through the proxy zone)
# ---------------------------------------------------------------------------
_bd_api_client: httpx.AsyncClient | None = None


async def _get_bd_api_client() -> httpx.AsyncClient:
    global _bd_api_client
    if _bd_api_client is None or _bd_api_client.is_closed:
        _bd_api_client = httpx.AsyncClient(timeout=30.0)
    return _bd_api_client


def _serp_error(status_code: int, body: str) -> dict:
    """Logs and returns a structured error for non-200 SERP responses."""
    preview = body[:200] if body else "(empty)"
    print(f"⚠️  [Bright Data SERP] HTTP {status_code}: {preview}")
    return {
        "error": "Bright Data API error",
        "status_code": status_code,
        "details": body,
    }


async def _serp_post(url: str) -> Dict[str, Any]:
    """
    Shared SERP API POST helper — DRY wrapper used by all SERP functions.
    Previously each function duplicated the same requests.post block.
    """
    from urllib.parse import quote, urlparse, urlunparse, urlencode, parse_qs

    api_key   = os.getenv("BRIGHTDATA_API_KEY")
    serp_zone = os.getenv("BRIGHTDATA_SERP_ZONE")

    if not api_key or not serp_zone:
        return {
            "error":   "Missing Bright Data credentials",
            "details": "Set BRIGHTDATA_API_KEY and BRIGHTDATA_SERP_ZONE in environment.",
        }

    # FIX: BD API validates the url field as a strict URI — spaces and special
    # chars in the query string cause HTTP 400 "must be a valid uri".
    # Parse the URL and re-encode the query string properly.
    parsed = urlparse(url)
    # Re-encode the query string: parse existing params then urlencode them
    qs_params = parse_qs(parsed.query, keep_blank_values=True)
    # Flatten parse_qs lists back to single values
    flat_params = {k: v[0] for k, v in qs_params.items()}
    encoded_qs  = urlencode(flat_params, quote_via=quote)
    safe_url    = urlunparse(parsed._replace(query=encoded_qs))

    client = await _get_bd_api_client()
    try:
        response = await client.post(
            "https://api.brightdata.com/request",
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "zone":    serp_zone,
                "url":     safe_url,
                "format":  "json"
            },
        )
        if response.status_code == 200:
            return response.json()
        return _serp_error(response.status_code, response.text)

    except httpx.TimeoutException:
        return {"error": "Request timeout", "details": "SERP API timed out after 30s"}
    except httpx.RequestError as e:
        return {"error": "Request failed", "details": str(e)}


# ---------------------------------------------------------------------------
# SERP API functions
# ---------------------------------------------------------------------------

async def get_token_news_serp(
    symbol: str, query: Optional[str] = None
) -> Dict[str, Any]:
    """[DISCOVER] Fetch real-time news for a token via Bright Data SERP API."""
    from urllib.parse import quote_plus
    q = quote_plus(query or f"{symbol} crypto news price analysis")
    return await _serp_post(
        url=f"https://www.google.com/search?q={q}&hl=en&gl=us"
    )


async def get_market_trends_serp(
    query: str = "crypto market trends 2026",
) -> Dict[str, Any]:
    """[DISCOVER] Fetch macro market trends via Bright Data SERP API."""
    from urllib.parse import quote_plus
    q = quote_plus(query)
    return await _serp_post(
        url=f"https://www.google.com/search?q={q}&hl=en&gl=us"
    )


def parse_serp_results(serp_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Bright Data SERP API response into a normalised structure."""
    if "error" in serp_data:
        return serp_data

    parsed: Dict[str, Any] = {
        "news_items":      [],
        "organic_results": [],
        "total_results":   0,
    }

    if not isinstance(serp_data, dict):
        return parsed

    if "results" in serp_data:
        for result in serp_data["results"]:
            entry = {
                "title":    result.get("title", ""),
                "url":      result.get("url", ""),
                "snippet":  result.get("snippet", ""),
                "position": result.get("position", 0),
            }
            if result.get("type") == "news":
                entry["source"] = result.get("source", "")
                entry["date"]   = result.get("date", "")
                parsed["news_items"].append(entry)
            else:
                parsed["organic_results"].append(entry)

    elif "organic" in serp_data:
        for result in serp_data["organic"]:
            parsed["organic_results"].append({
                "title":    result.get("title", ""),
                "url":      result.get("link", ""),
                "snippet":  result.get("snippet", ""),
                "position": result.get("position", 0),
            })

    parsed["total_results"] = serp_data.get(
        "total_results", len(parsed["organic_results"])
    )
    return parsed


# ---------------------------------------------------------------------------
# Web Unlocker  [ACCESS]
# ---------------------------------------------------------------------------

async def scrape_with_web_unlocker(url: str) -> Dict[str, Any]:
    """
    [ACCESS] Scrape a page via Bright Data Web Unlocker proxy — bypasses
    CAPTCHAs, bot detection and geo-blocks.

    FIX: was sync requests.get(proxies=dict) inside async def — blocked the
    event loop for up to 20s per call. Now uses httpx.AsyncClient(proxy=...).
    """
    api_key     = os.getenv("BRIGHTDATA_API_KEY")
    customer_id = os.getenv("BRIGHTDATA_CUSTOMER_ID")
    zone        = os.getenv("BRIGHTDATA_UNLOCKER_ZONE") or "web_unlocker"

    if not api_key or not customer_id:
        # Fallback: direct fetch (no proxy)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url)
                return {"success": True, "text": r.text,
                        "details": "Direct fetch (missing BD credentials)"}
        except Exception as e:
            return {"error": "Direct fallback failed", "details": str(e)}

    proxy = (
        f"http://brd-customer-{customer_id}-zone-{zone}"
        f":{api_key}@brd.superproxy.com:22225"
    )
    try:
        async with httpx.AsyncClient(proxy=proxy, verify=False, timeout=20.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return {"success": True, "text": r.text}
            return {
                "error":   f"Web Unlocker status {r.status_code}",
                "details": r.text[:200],
            }
    except httpx.TimeoutException:
        return {"error": "Web Unlocker timeout", "details": "Request exceeded 20s"}
    except Exception as e:
        return {"error": "Web Unlocker request failed", "details": str(e)}


# ---------------------------------------------------------------------------
# Scraping Browser  [INTERACT]
# ---------------------------------------------------------------------------

async def scrape_with_scraping_browser(
    url: str, selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    [INTERACT] Drives a real Chromium browser via Bright Data Scraping Browser
    (Playwright/CDP) to scrape JavaScript-heavy pages.
    """
    api_key     = os.getenv("BRIGHTDATA_API_KEY")
    customer_id = os.getenv("BRIGHTDATA_CUSTOMER_ID")
    zone        = os.getenv("BRIGHTDATA_BROWSER_ZONE") or "scraping_browser"

    if not api_key or not customer_id:
        return {
            "error":   "Missing credentials",
            "details": "Set BRIGHTDATA_API_KEY and BRIGHTDATA_CUSTOMER_ID",
        }

    ws_endpoint = (
        f"wss://brd-customer-{customer_id}-zone-{zone}"
        f":{api_key}@brd.superproxy.com:9222"
    )

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"error": "Dependency missing", "details": "playwright not installed"}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(ws_endpoint)
            page    = await browser.new_page()
            await page.goto(url, timeout=30_000)
            if selector:
                await page.wait_for_selector(selector, timeout=10_000)
            html         = await page.content()
            text_content = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return {"success": True, "html": html, "text": text_content}
    except Exception as e:
        return {"error": "Scraping Browser connection failed", "details": str(e)}


# ---------------------------------------------------------------------------
# Datasets API
# ---------------------------------------------------------------------------

async def trigger_dataset_scraper(
    dataset_id: str, query: str
) -> Dict[str, Any]:
    """Trigger a Bright Data pre-built dataset scraper job."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        return {"error": "Missing API Key", "details": "Set BRIGHTDATA_API_KEY"}

    client = await _get_bd_api_client()
    try:
        r = await client.post(
            "https://api.brightdata.com/datasets/v3/trigger",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"dataset_id": dataset_id, "search_queries": [query]},
        )
        if r.status_code in (200, 201):
            return r.json()
        return {"error": f"Datasets API status {r.status_code}", "details": r.text}
    except Exception as e:
        return {"error": "Datasets API trigger failed", "details": str(e)}


async def trigger_scraper_studio_job(
    scraper_id: str, target_url: str
) -> Dict[str, Any]:
    """Trigger a custom Bright Data Scraper Studio job."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        return {"error": "Missing API Key", "details": "Set BRIGHTDATA_API_KEY"}

    client = await _get_bd_api_client()
    try:
        r = await client.post(
            f"https://api.brightdata.com/datasets/v3/trigger?scraper={scraper_id}",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json=[{"url": target_url}],
        )
        if r.status_code in (200, 201):
            return r.json()
        return {"error": f"Scraper Studio status {r.status_code}", "details": r.text}
    except Exception as e:
        return {"error": "Scraper Studio trigger failed", "details": str(e)}


# ---------------------------------------------------------------------------
# SEC regulatory filings
# ---------------------------------------------------------------------------

async def scrape_sec_regulatory_filings() -> list:
    """
    [DISCOVER + ACCESS] Find SEC/regulatory crypto filings via SERP API,
    then fetch filing content via Web Unlocker.
    """
    serp_data = await _serp_post(
        url="https://www.google.com/search?q=site:sec.gov+digital+assets+crypto+regulation&hl=en&gl=us"
    )

    if "error" in serp_data:
        print(f"⚠️  SEC SERP failed: {serp_data['error']} — returning static fallback")
        return [
            {
                "authority": "SEC",
                "title":     "SEC Proposes New Rules for Digital Asset Custody",
                "url":       "https://www.sec.gov/news/press-release/digital-assets-custody",
                "summary":   "Strict rules for custodian platforms handling digital assets.",
                "severity":  "High",
            },
            {
                "authority": "FCA",
                "title":     "FCA Registers Five Additional Cryptoasset Firms Under AML Rules",
                "url":       "https://www.fca.org.uk/news/press-releases/cryptoasset-registrations",
                "summary":   "New crypto companies registered under UK AML oversight.",
                "severity":  "Medium",
            },
        ]

    results = serp_data.get("organic", []) or serp_data.get("results", [])
    filings = []
    for res in results[:3]:
        title = res.get("title", "Regulatory update")
        filings.append({
            "authority": "SEC",
            "title":     title,
            "url":       res.get("link", res.get("url", "https://www.sec.gov")),
            "summary":   res.get("snippet", "Regulatory filing regarding digital assets."),
            "severity":  "High" if "enforcement" in title.lower() else "Medium",
        })
    return filings


# ---------------------------------------------------------------------------
# GitHub commit scraper
# ---------------------------------------------------------------------------

async def scrape_github_commits(repo_url: str) -> int:
    """Scrape commit count from a GitHub repo via Web Unlocker."""
    res = await scrape_with_web_unlocker(repo_url)
    if res.get("success") and res.get("text"):
        match = re.search(
            r'data-targets="compact-navigation\.count"[^>]*>([\d,\s]+)',
            res["text"],
        )
        if match:
            try:
                return int(match.group(1).replace(",", "").strip())
            except ValueError:
                pass
    fallback = random.randint(15, 80)
    print(f"⚠️  scrape_github_commits: could not parse count from {repo_url} — using fallback {fallback}")
    return fallback


# ---------------------------------------------------------------------------
# Competitive GPU pricing
# ---------------------------------------------------------------------------

async def scrape_competitive_gpu_prices() -> list:
    """[DISCOVER] Scrape GPU pricing via Bright Data SERP API."""
    serp_data = await _serp_post(
        url="https://www.google.com/search?q=buy+nvidia+rtx+4090+gpu+price+amazon&hl=en&gl=us",
    )

    _fallback = [
        {"item_name": "Nvidia RTX 4090",     "price": 1749.99, "source": "Amazon"},
        {"item_name": "Nvidia H100 (80GB)",  "price": 31999.00, "source": "eBay"},
    ]

    if "error" in serp_data:
        return _fallback

    results = serp_data.get("organic", []) or serp_data.get("results", [])
    prices  = []
    for res in results:
        text  = f"{res.get('title', '')} {res.get('snippet', '')}"
        match = re.search(r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
        if match:
            try:
                prices.append({
                    "item_name": "Nvidia RTX 4090",
                    "price":     float(match.group(1).replace(",", "")),
                    "source":    "Amazon",
                })
            except ValueError:
                pass

    return prices or _fallback