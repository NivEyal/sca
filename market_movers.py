import requests
import pandas as pd

API_KEY = "LQOCJ3SPdBrntavdH3mNZClLTiOqUwWc"  # עדכן כאן אם יש מפתח אחר

def fetch_market_movers(endpoint: str, limit: int = 10) -> pd.DataFrame:
    url = f"https://financialmodelingprep.com/api/v3/{endpoint}?apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ API failed: {response.status_code} - {response.text}")
        return pd.DataFrame()

    data = response.json()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    required = ["symbol", "companyName", "price", "changesPercentage", "changes", "volume"]
    present = [col for col in required if col in df.columns]
    df = df[present].copy()

    if "changesPercentage" in df.columns:
        df["% שינוי יומי"] = df["changesPercentage"].apply(lambda x: float(str(x).replace('%', '')) if pd.notnull(x) else 0.0)

    rename_map = {
        "symbol": "symbol",
        "companyName": "companyName",
        "price": "price",
        "changes": "change $",
        "volume": "volume"
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    return df.head(limit)

def format_market_movers_section(title, df):
    if df.empty:
        return f"### {title}\nלא נמצאו נתונים."

    def color_pct(x):
        try:
            x = float(x)
            return f"<span style='color:{'green' if x >= 0 else 'red'}'>{x:.2f}%</span>"
        except:
            return x

    df_display = df.copy()
    if "% שינוי יומי" in df_display.columns:
        df_display["% שינוי יומי"] = df_display["% שינוי יומי"].apply(color_pct)

    return f"### {title}\n" + df_display.to_html(escape=False, index=False)
