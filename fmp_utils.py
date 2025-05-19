import requests

def get_top_fmp_tickers(api_key: str, limit: int = 10) -> list:
    url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={anc5nLqF1PuZUQGhxDHpgXuU0Yp9Cj0V}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return [x['symbol'] for x in res.json()][:limit]
    except Exception as e:
        print(f"FMP Error: {e}")
        return []
