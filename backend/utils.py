import httpx
import re

async def get_tokens():
    # Use 'async with' to ensure the connection is closed automatically
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency": "usd", "category": "web3"}
        )
        return response.json()

def extract_symbol(text: str):
    """
    Scans text for crypto symbols. 
    Priority: 1. Uppercase symbols (BTC) 2. Known lowercase keywords.
    """
    # Look for 3-5 consecutive uppercase letters (e.g., "Tell me about SOL")
    found = re.findall(r'\b[A-Z]{3,5}\b', text)
    if found:
        return found[0]

    # Fallback: check for common lowercase mentions
    text_lower = text.lower()
    common_map = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "doge": "DOGE"}
    for name, sym in common_map.items():
        if name in text_lower:
            return sym
            
    return "BTC"  # Default to BTC if nothing is found