import requests
import pandas as pd

API_KEY = "LQOCJ3SPdBrntavdH3mNZClLTiOqUwWc"  # עדכן לפי הצורך

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
        df["% שינוי יומי"] = df["changesPercentage"].apply(
            lambda x: float(str(x).replace('%', '').replace('+', '')) if pd.notnull(x) else 0.0
        )

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

    def get_color_style(pct):
        try:
            pct = float(pct)
            return 'background-color: #e6ffe6;' if pct >= 0 else 'background-color: #ffe6e6;'
        except:
            return ''

    def format_change_with_pct(row):
        try:
            pct = float(row.get("% שינוי יומי", 0))
            change_val = row.get("change $", "")
            symbol = "🔺" if pct >= 0 else "🔻"
            return f"{change_val} {symbol} ({abs(pct):.2f}%)"
        except:
            return row.get("change $", "")

    df_display = df.copy()

    if "% שינוי יומי" in df_display.columns:
        df_display["__row_color__"] = df_display["% שינוי יומי"].apply(get_color_style)
        df_display["change $"] = df_display.apply(format_change_with_pct, axis=1)
        df_display.drop(columns=["% שינוי יומי"], inplace=True)

    # בניית טבלת HTML עם עיצוב לשורות
    table_rows = []
    headers = ''.join([f'<th>{col}</th>' for col in df_display.columns if col != "__row_color__"])

    for _, row in df_display.iterrows():
        style = row.get("__row_color__", "")
        cells = ''.join([f'<td>{row[col]}</td>' for col in df_display.columns if col != "__row_color__"])
        table_rows.append(f'<tr style="{style}">{cells}</tr>')

    html_table = f"""
    <table border="1" style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;">
      <thead style="background-color: #f2f2f2;">{headers}</thead>
      <tbody>{''.join(table_rows)}</tbody>
    </table>
    """

    return f"### {title}\n{html_table}"
