import requests
def get_top_volume_tickers(limit=10):
    url = "https://financialmodelingprep.com/api/v3/stock_market/actives"
    params = {"apikey": "anc5nLqF1PuZUQGhxDHpgXuU0Yp9Cj0V"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        print("✅ Raw FMP data received:", data[:3] if data else "No data")

        # Filter out penny stocks and bad tickers
        filtered = [
            item["symbol"]
            for item in data
            if item.get("price", 0) >= 1.0 and "." not in item.get("symbol", "")
        ]

        print(f"✅ Filtered tickers: {filtered[:10]}")  # Debug log
        return filtered[:limit]
    except Exception as e:
        print("❌ Error fetching top tickers from FMP:", e)
