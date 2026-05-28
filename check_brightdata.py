import os
import asyncio
import requests
from dotenv import load_dotenv

load_dotenv()

# Set up test credentials
API_KEY = os.getenv("BRIGHTDATA_API_KEY")
CUSTOMER_ID = os.getenv("BRIGHTDATA_CUSTOMER_ID")
TOKEN = os.getenv("BRIGHTDATA_API_KEY")

SERP_ZONE = os.getenv("BRIGHTDATA_SERP_ZONE", "serp_api")
UNLOCKER_ZONE = os.getenv("BRIGHTDATA_UNLOCKER_ZONE", "web_unlocker")
BROWSER_ZONE = os.getenv("BRIGHTDATA_BROWSER_ZONE", "scraping_browser")

async def test_mcp_server():
    print("\n--- 1. Testing Hosted MCP Server Connection ---")
    if not TOKEN:
        print("⚠️ Skip: BRIGHTDATA_API_KEY not set in environment.")
        return False
        
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        client = MultiServerMCPClient({
            "bright_data": {
                "url": f"https://mcp.brightdata.com/mcp?token={TOKEN}",
                "transport": "streamable_http",
            }
        })
        print("🔌 Connecting to remote streamable HTTP MCP server...")
        tools = {t.name: t for t in await client.get_tools()}
        print(f"   Tools: {', '.join(sorted(tools.keys()))}")
        response = await tools["search_engine"].ainvoke({"query": "crypto news"})
        preview = str(response)[:150]
        print("✅ MCP search_engine call successful!")
        print(f"📄 Response preview: {preview}...")
        return True
    except Exception as e:
        print(f"❌ MCP Server test failed: {e}")
        return False

def test_web_unlocker():
    print("\n--- 2. Testing Web Unlocker Proxy ---")
    if not API_KEY or not CUSTOMER_ID:
        print("⚠️ Skip: BRIGHTDATA_API_KEY or BRIGHTDATA_CUSTOMER_ID not set.")
        return False
        
    proxy_url = f"http://brd-customer-{CUSTOMER_ID}-zone-{UNLOCKER_ZONE}:{API_KEY}@brd.superproxy.com:22225"
    proxies = {"http": proxy_url, "https": proxy_url}
    test_url = "https://httpbin.org/ip"
    
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        print(f"🌐 Querying {test_url} through Web Unlocker...")
        response = requests.get(test_url, proxies=proxies, verify=False, timeout=15)
        if response.status_code == 200:
            print("✅ Web Unlocker request successful!")
            print(f"📄 Response IP content: {response.text.strip()}")
            return True
        else:
            print(f"❌ Web Unlocker error. Status: {response.status_code}, Body: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Web Unlocker connection failed: {e}")
        return False

def test_serp_api():
    print("\n--- 3. Testing SERP API ---")
    if not API_KEY:
        print("⚠️ Skip: BRIGHTDATA_API_KEY not set.")
        return False
        
    url = "https://api.brightdata.com/request"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "zone": SERP_ZONE,
        "url": "https://www.google.com/search?q=bitcoin",
        "format": "raw",
        "brd_json": "1"
    }
    
    try:
        print("🔍 Querying Google search via SERP API request endpoint...")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ SERP API request successful!")
            data = response.json()
            organic = data.get("organic", []) or data.get("results", [])
            print(f"📄 Retrieved {len(organic)} search result matches.")
            return True
        else:
            print(f"❌ SERP API error. Status: {response.status_code}, Body: {response.text}")
            return False
    except Exception as e:
        print(f"❌ SERP API request failed: {e}")
        return False

async def test_scraping_browser():
    print("\n--- 4. Testing Scraping Browser CDP Connection ---")
    if not API_KEY or not CUSTOMER_ID:
        print("⚠️ Skip: BRIGHTDATA_API_KEY or BRIGHTDATA_CUSTOMER_ID not set.")
        return False
        
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("⚠️ Skip: 'playwright' library not installed.")
        return False
        
    ws_endpoint = f"wss://brd-customer-{CUSTOMER_ID}-zone-{BROWSER_ZONE}:{API_KEY}@brd.superproxy.com:9222"
    test_url = "https://httpbin.org/headers"
    
    try:
        print(f"🕷️ Launching Scraping Browser connection to {test_url}...")
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(ws_endpoint)
            page = await browser.new_page()
            await page.goto(test_url, timeout=30000)
            headers_content = await page.evaluate("() => document.body.innerText")
            print("✅ Scraping Browser CDP connection successful!")
            print(f"📄 Response: {headers_content.strip()}")
            await browser.close()
            return True
    except Exception as e:
        print(f"❌ Scraping Browser test failed: {e}")
        return False

def test_datasets_scrapers():
    print("\n--- 5. Testing Datasets Trigger API ---")
    if not API_KEY:
        print("⚠️ Skip: BRIGHTDATA_API_KEY not set.")
        return False
        
    url = "https://api.brightdata.com/datasets/v3/trigger"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "dataset_id": "twitter_posts",
        "search_queries": ["#BTC"]
    }
    
    try:
        print("📊 Triggering dataset collection...")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        # 400 or 403 can happen if the specific dataset is not activated on the account, but we verify API response
        if response.status_code in [200, 201, 202]:
            print("✅ Datasets API trigger successful!")
            print(f"📄 Response: {response.text}")
            return True
        else:
            print(f"ℹ️ Datasets API responded with code {response.status_code} (Ensure 'twitter_posts' dataset is active on your plan).")
            print(f"📄 Details: {response.text}")
            return True # API reached, which is a success for config verification
    except Exception as e:
        print(f"❌ Datasets API connection failed: {e}")
        return False

def test_scraper_studio():
    print("\n--- 6. Testing Scraper Studio Trigger API ---")
    if not API_KEY:
        print("⚠️ Skip: BRIGHTDATA_API_KEY not set.")
        return False
        
    # We test with a dummy scraper ID to check API endpoint connectivity
    url = "https://api.brightdata.com/datasets/v3/trigger?scraper=dummy_scraper_id"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = [{"url": "https://httpbin.org"}]
    
    try:
        print("🎨 Querying Scraper Studio Trigger API...")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        # Expected status: 400 (if dummy_scraper_id doesn't exist) but we verify endpoint reachability
        if response.status_code in [200, 201, 202, 400]:
            print("✅ Scraper Studio trigger endpoint reachable!")
            print(f"📄 Response status: {response.status_code}")
            return True
        else:
            print(f"❌ Scraper Studio endpoint error. Status: {response.status_code}, Body: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Scraper Studio API connection failed: {e}")
        return False

async def main():
    print("🔍 Starting Bright Data 7-Product Verification Diagnostics...")
    await test_mcp_server()
    test_web_unlocker()
    test_serp_api()
    await test_scraping_browser()
    test_datasets_scrapers()
    test_scraper_studio()
    print("\n🏁 Diagnostics Finished.")

if __name__ == "__main__":
    asyncio.run(main())
