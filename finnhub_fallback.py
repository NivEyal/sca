# finnhub_fallback.py

import pandas as pd
import finnhub
from datetime import datetime
from streamlit import secrets
from alpaca_connector import AlpacaConnector, DataFeed
from alpaca_data import AlpacaConnector, DataFeed

alpaca_client = AlpacaConnector(
    api_key="AKNBUFB8HJFN2XTQWXSK",
    secret_key="hSQOdDX7A1Ujj65N9nzE3qikNNUyNceKWGaolbmK",
    paper=False,
    feed=DataFeed.IEX  # ✅ correct usage — this is the Enum
)

def get_finnhub_bars(symbol: str, resolution: str = "1", limit: int = 300) -> pd.DataFrame:
    try:
        api_key = secrets["FINNHUB_API_KEY"]
        client = finnhub.Client(api_key=api_key)

        now = int(datetime.utcnow().timestamp())
        start = now - limit * 60  # 1-minute resolution

        res = client.stock_candles(symbol, resolution, start, now)
        if res.get("s") != "ok":
            return pd.DataFrame()

        df = pd.DataFrame(res)
        df["timestamp"] = pd.to_datetime(df["t"], unit="s")
        df.set_index("timestamp", inplace=True)
        df.rename(columns={
            "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"
        }, inplace=True)
        return df[["open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"Finnhub fallback error for {symbol}: {e}")
        return pd.DataFrame()
