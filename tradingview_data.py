import requests
import pandas as pd

def get_tradingview_data(tickers, market="america"):
    def resolve_market_prefix(symbol):
        # Assign most to NASDAQ for safety
        if symbol.upper() in {"UNH", "JPM", "MCD", "V"}:
            return f"NYSE:{symbol}"
        return f"NASDAQ:{symbol}"  # Default

    tv_tickers = [resolve_market_prefix(t) for t in tickers]

    url = f"https://scanner.tradingview.com/{market}/scan"
    payload = {
        "symbols": {"tickers": tv_tickers, "query": {"types": []}},
        "columns": [
            "name", "description", "close", "change", "change_abs", "volume",
            "Value.Traded", "Recommend.All", "exchange", "market_cap_basic"
        ]
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Referer": f"https://www.tradingview.com/markets/stocks-{market}/market-movers-active/"
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        result = res.json()

        rows = []
        for item in result.get("data", []):
            d = item.get("d", [])
            if d[2] and d[2] >= 1.0:  # Filter out penny stocks
                rows.append({
                    "Symbol": d[0].split(":")[-1],
                    "Name": d[1],
                    "Price": round(d[2], 2),
                    "% Change": round(d[3], 2),
                    "Volume": int(d[5]) if d[5] else None,
                    "Recommendation": d[7]
                })

        return pd.DataFrame(rows)

    except Exception as e:
        print("❌ TradingView fetch error:", e)
        return pd.DataFrame()
