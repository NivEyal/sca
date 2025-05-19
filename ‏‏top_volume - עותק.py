# top_volume.py
import requests

def get_top_volume_tickers(limit=10):
    url = "https://financialmodelingprep.com/api/v3/stock_market/actives"
    params = {"apikey": "anc5nLqF1PuZUQGhxDHpgXuU0Yp9Cj0V"}  # replace if needed

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return [item["symbol"] for item in data[:limit]]
    except Exception as e:
        print("Error fetching top tickers from FMP:", e)
        return []
