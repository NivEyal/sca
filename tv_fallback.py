from tradingview_ta import TA_Handler, Interval, Exchange
import logging

def get_top_volume_tickers_from_fmp(api_key: str, limit: int = 10) -> List[str]:
    try:
        url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={anc5nLqF1PuZUQGhxDHpgXuU0Yp9Cj0V}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return [stock["symbol"] for stock in data[:limit]]
    except Exception as e:
        print(f"[FMP ERROR] Failed to fetch tickers: {e}")
        return []

