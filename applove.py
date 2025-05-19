import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import requests
import yfinance as yf
import atexit
import threading
from alpaca_data import AlpacaData
from strategy import run_strategies

# --- Page Config ---
st.set_page_config(page_title="🚀 Alpaca Strategy Scanner", layout="wide")
st.title("📊 Alpaca Strategy Scanner Dashboard")

# --- Globals & Setup ---
if "websocket_thread" not in st.session_state:
    st.session_state.websocket_thread = None
if "alpaca_data" not in st.session_state:
    st.session_state.alpaca_data = AlpacaData()

# --- Sidebar ---
st.sidebar.header("🔍 Strategy Configuration")
strategy_categories = {
    "Momentum": ["Momentum Trading", "MACD Bullish ADX", "ADX Rising MFI Surge"],
    "Trend Following": ["Trend Following (EMA/ADX)", "Golden Cross RSI"],
    "Mean Reversion": ["Mean Reversion (RSI)", "Scalping (Bollinger Bands)", "MACD RSI Oversold"],
    "Volume-Based": ["VWAP RSI", "News Trading (Volatility Spike)", "TEMA Cross Volume"],
    "Breakouts": ["Breakout Trading", "Pivot Point (Intraday S/R)"]
}

selected_categories = st.sidebar.multiselect("Select Strategy Categories", list(strategy_categories.keys()), default=list(strategy_categories.keys()))
selected_strategies = []
for cat in selected_categories:
    selected_strategies.extend(strategy_categories[cat])

if st.sidebar.button("Clear Selection"):
    selected_strategies = []

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Ticker Input")

# --- Get Top Volume Stocks via FMP ---
def get_top_10_volume_fmp():
    try:
        url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={st.secrets['FMP_API_KEY']}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return [item['symbol'] for item in data[:10]]
        else:
            return []
    except:
        return []

load_top = st.sidebar.checkbox("📡 Auto-load top 10 active stocks", value=True)
manual_input = st.sidebar.text_input("...or enter comma-separated tickers:", "")

if manual_input:
    user_tickers = [ticker.strip().upper() for ticker in manual_input.split(",") if ticker.strip()]
elif load_top:
    user_tickers = get_top_10_volume_fmp() or ["AAPL", "TSLA", "NVDA", "MSFT"]
else:
    user_tickers = []

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Page & Clear Cache"):
    st.session_state.clear()
    st.rerun()

# --- WebSocket Start ---
def start_websocket():
    if st.session_state.websocket_thread is None:
        thread = threading.Thread(target=st.session_state.alpaca_data.start_websocket_stream, args=(user_tickers,), daemon=True)
        thread.start()
        st.session_state.websocket_thread = thread

start_websocket()

# --- Exit Cleanup ---
def cleanup():
    if st.session_state.websocket_thread:
        st.session_state.alpaca_data.stop_websocket_stream()
atexit.register(cleanup)

# --- Market Overview ---
st.subheader("📈 Market Overview")

def fetch_price_data(ticker):
    try:
        df = st.session_state.alpaca_data.get_historical_data(ticker, timeframe="5Min", limit=30)
        price = df['close'].iloc[-1]
        open_price = df['open'].iloc[0]
        change = ((price - open_price) / open_price) * 100
        return price, change
    except:
        try:
            data = yf.Ticker(ticker).history(period="1d", interval="5m")
            price = data["Close"].iloc[-1]
            open_price = data["Open"].iloc[0]
            change = ((price - open_price) / open_price) * 100
            return price, change
        except:
            return 0, 0

market_data = []
for ticker in user_tickers:
    price, change = fetch_price_data(ticker)
    market_data.append({"Ticker": ticker, "Price": round(price, 2), "% Change": round(change, 2)})

st.dataframe(pd.DataFrame(market_data).sort_values("% Change", ascending=False), use_container_width=True)

# --- Strategy Scanner ---
st.subheader("🧠 Strategy Scanner Results")

for ticker in user_tickers:
    st.markdown(f"### {ticker}")
    try:
        df = st.session_state.alpaca_data.get_historical_data(ticker, timeframe="5Min", limit=100)
    except:
        df = yf.Ticker(ticker).history(period="1d", interval="5m")
    if df.empty:
        st.warning(f"No data for {ticker}")
        continue

    signals = run_strategies(df, selected_strategies)
    for strat, signal in signals.items():
        st.markdown(f"- **{strat}**: `{signal}`")

    fig = go.Figure(data=[
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"]
        )
    ])
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

# --- Donation Button ---
st.markdown("---")
st.markdown("☕ If you enjoy this app, consider [buying me a coffee](https://buymeacoffee.com/) to support development!")
