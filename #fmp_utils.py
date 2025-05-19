import requests

def get_top_fmp_tickers(api_key: str, limit: int = 10) -> list:
    url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={api_key}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        tickers = [item["symbol"] for item in data]
        return tickers[:limit]
    except Exception as e:
        print(f"❌ Error fetching FMP tickers: {e}")
        return []
