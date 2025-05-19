import streamlit as st
st.set_page_config(page_title="🚀 Alpaca Strategy Scanner", layout="wide")

from tradingview_data import get_tradingview_data

# app.py
# ...
# ...from strategy import run_strategies # Assuming this is your custom function
import asyncio
import threading
import requests
import atexit
import time
import logging # Import logging for Streamlit script to
from typing import List, Dict, Optional, Any
# No need to import DataFeed here if passing feed as string
from enum import Enum
import pandas as pd
import plotly.graph_objects as go
import requests
from enum import Enum
from alpaca_connector import AlpacaConnector, DataFeed
from top_volume import get_top_volume_tickers
from market_movers import fetch_market_movers
from strategy import run_strategies
from alpaca_connector import get_latest_price_and_change
# Load Alpaca secrets
ALPACA_API_KEY = st.secrets.get("ALPACA_API_KEY")
ALPACA_SECRET_KEY = st.secrets.get("ALPACA_SECRET_KEY")
ALPACA_FEED_STR = st.secrets.get("APCA_DATA_FEED", "sip").lower()     # should become "sip"
ALPACA_PAPER = st.secrets.get("APCA_PAPER", False)                    # should be False
ALPACA_BASE_URL = st.secrets.get("APCA_API_BASE_URL", "https://api.alpaca.markets")
alpaca = AlpacaConnector(
api_key=ALPACA_API_KEY,
secret_key=ALPACA_SECRET_KEY,)
FMP_API_KEY = st.secrets.get("FMP_API_KEY") # Load the FMP API Key

def clean_tickers_for_tradingview(tickers):
    return [t for t in tickers if t.isalpha() and len(t) <= 9]
# ✅ Define function to clean tickers
def clean_tickers_for_tradingview(tickers):
    return [t for t in tickers if t.isalpha() and len(t) <= 9]


# --- Title ---
st.title("🔥 Top Volume Stocks with TradingView + Alpaca Prices")

# --- Style Injection for Zebra + Bold Headers ---
st.markdown("""
<style>
thead tr th {
    background-color: #0e1117;
    color: white;
    font-weight: bold;
}
tbody tr:nth-child(even) {
    background-color: #f2f2f2;
}
td {
    padding: 6px;
}
</style>
""", unsafe_allow_html=True)

# --- Fetch tickers ---
tickers = get_top_volume_tickers(limit=10)

if not tickers:
    st.error("❌ Failed to fetch top tickers from FMP.")
else:
    st.success(f"Top 10 Tickers: {', '.join(tickers)}")

    tickers_clean = clean_tickers_for_tradingview(tickers)
    st.caption(f"📡 Cleaned for TradingView: {', '.join(tickers_clean)}")

    df_tv = get_tradingview_data(tickers_clean)

    if df_tv.empty:
        st.warning("⚠️ No data returned from TradingView.")
    else:
        # ✅ Format % Change with color and "%"
        def format_change(val):
            if pd.isna(val):
                return "-"
            color = "green" if val > 0 else "red"
            return f"<span style='color:{color}'>{val:.2f}%</span>"

        # Apply formatting
        
    # 🕓 הוספת נתוני AFTER-HOURS מהסריקה בגוגל
    price_change_data = {}
    with st.spinner("📡 Fetching real-time prices from Alpaca..."):
        for t in df_tv["Symbol"]:
            price_data = get_latest_price_and_change(alpaca, t)
            price_change_data[t] = price_data

    df_tv["Last Close"] = df_tv["Symbol"].apply(lambda t: price_change_data.get(t, {}).get("last_close", "N/A"))
    df_tv["Prev Close"] = df_tv["Symbol"].apply(lambda t: price_change_data.get(t, {}).get("prev_close", "N/A"))
    df_tv["% Change"] = df_tv["Symbol"].apply(lambda t: price_change_data.get(t, {}).get("pct_change", "N/A"))
    df_tv["% Change"] = df_tv["% Change"].apply(
        lambda x: f"🔻 {x:.2f}%" if isinstance(x, float) and x < 0 else f"🟢 {x:.2f}%" if isinstance(x, float) else x
    )

    # ✅ הצגת טבלה בעיצוב HTML עם עמודות After-Hours
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(df_tv.to_html(escape=False, index=False), unsafe_allow_html=True)


col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🔼 Top Gainers")
    gainers = fetch_market_movers("stock_market/gainers")
    if not gainers.empty:
        html = format_market_movers_section("🔺 Top Gainers", gainers_df)
        st.markdown(html, unsafe_allow_html=True)

    else:
        st.warning("No data for gainers.")

with col2:
    st.markdown("### 🔽 Top Losers")
    losers = fetch_market_movers("stock_market/losers")
    if not losers.empty:
        st.dataframe(losers, use_container_width=True)
    else:
        st.warning("No data for losers.")

# Setup Streamlit page

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Streamlit app started.")

# --- API Keys ---
FMP_API_KEY = st.secrets.get("FMP_API_KEY", "demo")

# --- Get Top Tickers ---




# --- Settings

 


class DataFeed(str, Enum):
    SIP = "sip"
    IEX = "iex"
# --- Setup logging for the Streamlit script ---
# Configure logging for the main thread (Streamlit) if it hasn't been configured globally by alpaca_data
# This ensures logs from the main thread are visible
if not logging.getLogger().handlers: # Check if root logger has handlers
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
streamlit_logger = logging.getLogger(__name__) # Get a logger specific to this script
streamlit_logger.info("Streamlit app started.")


# --- Set Page Config (MUST BE FIRST STREAMLIT COMMAND) ---

# --- Load API Keys from Streamlit Secrets ---



# Load FMP API Key

# 🔁 Create AlpacaConnector instance (this must succeed if keys are correct)
alpaca_client = AlpacaConnector(
    api_key="AKNBUFB8HJFN2XTQWXSK",
    secret_key="hSQOdDX7A1Ujj65N9nzE3qikNNUyNceKWGaolbmK",
    paper=False,
    feed=DataFeed.IEX  # ✅ this is an Enum, not a string
)

if not alpaca_client.is_operational:
    st.error("❌ Alpaca client still not operational (even with forced config). Check logs.")
else:
    st.success("✅ Alpaca Live Client Initialized!")

# --- Config ---
STRATEGY_CATEGORIES = {
    "Pattern Recognition": [
        "Fractal Breakout RSI", "Ross Hook Momentum",
        "Hammer Volume", "RSI Bullish Divergence Candlestick"
    ],
    "Momentum": [
        "Momentum Trading", "MACD Bullish ADX", "ADX Rising MFI Surge", "TRIX OBV", "Vortex ADX"
    ],
    "Mean Reversion": [
        "Mean Reversion (RSI)", "Scalping (Bollinger Bands)", "MACD RSI Oversold", "CCI Reversion",
        "Bollinger Bounce Volume", "MFI Bollinger"
    ],
    "Trend Following": [
        "Trend Following (EMA/ADX)", "Golden Cross RSI", "ADX Heikin Ashi", "SuperTrend RSI Pullback",
        "Ichimoku Basic Combo", "Ichimoku Multi-Line", "EMA SAR"
    ],
    "Breakout": [
        "Breakout Trading", "Pivot Point (Intraday S/R)"
    ],
    "Volatility": [
        "Bollinger Upper Break Volume", "EMA Ribbon Expansion CMF"
    ],
    "Volume-Based": [
        "News Trading (Volatility Spike)", "TEMA Cross Volume", "Bollinger Bounce Volume",
        "Hammer Volume", "ADX Rising MFI Surge", "MFI Bollinger", "TRIX OBV", "VWAP RSI",
        "VWAP Aroon", "EMA Ribbon Expansion CMF"
    ],
    "Oscillator-Based": [
        "PSAR RSI", "RSI EMA Crossover", "CCI Bollinger", "Awesome Oscillator Divergence MACD",
        "Heikin Ashi CMO", "MFI Bollinger"
    ],
    "News/Event-Driven": [
        "News Trading (Volatility Spike)"
    ],
    "Hybrid/Other": [
        "Reversal (RSI/MACD)", "Pullback Trading (EMA)", "End-of-Day (Intraday Consolidation)",
        "VWAP RSI", "Chandelier Exit MACD", "Heikin Ashi CMO", "Double MA Pullback",
        "RSI Range Breakout BB", "VWAP Aroon", "EMA Ribbon Expansion CMF", "MACD Bullish ADX",
        "ADX Rising MFI Surge", "Fractal Breakout RSI", "Bollinger Upper Break Volume",
        "RSI EMA Crossover", "Vortex ADX", "Ross Hook Momentum", "RSI Bullish Divergence Candlestick",
        "Ichimoku Basic Combo", "Ichimoku Multi-Line", "EMA SAR", "MFI Bollinger", "Hammer Volume"
    ]
}
# Ensure ALL strategies listed in categories are present, handle potential duplicates
ALL_UNIQUE_STRATEGY_NAMES = sorted(list(set(s_name for cat_strats in STRATEGY_CATEGORIES.values() for s_name in cat_strats)))

# --- Helper Functions ---




def start_websocket_thread_loop(loop: asyncio.AbstractEventLoop, alpaca_client: AlpacaConnector, ws_tickers_list: List[str]):
    asyncio.set_event_loop(loop)
    if not ws_tickers_list:
        streamlit_logger.warning(f"WebSocket Thread ({threading.get_ident()}): No tickers provided for streaming. Exiting thread.")
        if loop.is_running(): loop.call_soon_threadsafe(loop.stop)
        if not loop.is_closed(): loop.call_soon_threadsafe(loop.close)
        asyncio.set_event_loop(None)
        return

    streamlit_logger.info(f"WebSocket Thread ({threading.get_ident()}): Starting Alpaca WebSocket for {len(ws_tickers_list)} tickers.")
    try:
        # ✅ ADD this line, replacing the entire if/else block above
        # The main thread decided to start this thread, so we assume the stream should start here.
        # AlpacaConnector.start_stream handles its own internal state if called redundantly.
        if hasattr(alpaca_client, '_websocket_running') and alpaca_client._websocket_running:
            loop.run_until_complete(alpaca_client.stop_stream())

        loop.run_until_complete(alpaca_client.start_stream(
            symbols=ws_tickers_list,
            on_bar=None,
            on_trade=None,
            on_quote=None,
            subscribe_bars=True,
            subscribe_trades=True,
            subscribe_quotes=False
        ))
        # ✅ END ADD
        streamlit_logger.info(f"WebSocket Thread ({threading.get_ident()}): run_until_complete finished. WebSocket stream stopped.")
    except asyncio.CancelledError:
        streamlit_logger.info(f"WebSocket Thread ({threading.get_ident()}): asyncio.CancelledError caught. Stream task was cancelled.")
    except Exception as e:
        streamlit_logger.error(f"WebSocket Thread ({threading.get_ident()}) error during loop execution: {e}", exc_info=True)
    finally:
        streamlit_logger.info(f"WebSocket Thread ({threading.get_ident()}): Finally block. Loop running: {loop.is_running()}, Loop closed: {loop.is_closed()}.")
        if loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if not loop.is_closed():
            loop.call_soon_threadsafe(loop.close)
            streamlit_logger.info(f"WebSocket Thread ({threading.get_ident()}): Loop close requested.")
        asyncio.set_event_loop(None)
        streamlit_logger.debug(f"WebSocket Thread ({threading.get_ident()}): Event loop finalized and unset.")


@st.cache_resource
def initialize_alpaca_client(api_key, secret_key, paper, feed_str, base_url):
    streamlit_logger.info("Attempting to initialize Alpaca client (via cache_resource)...")
    try:
        alpaca_client_instance = AlpacaConnector(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper,
            feed=feed_str,
            base_url=base_url
        )
        if alpaca_client_instance.is_operational:
            streamlit_logger.info("Alpaca client initialized and reported as operational.")
            return alpaca_client_instance
        else:
            streamlit_logger.warning("AlpacaConnector instance created, but reported as not fully operational. Returning None.")
            return None
    except Exception as e:
        st.error(f"A critical error prevented Alpaca client initialization: {e}")
        streamlit_logger.critical(f"Critical error during AlpacaConnector instantiation: {e}", exc_info=True)
        return None

alpaca: Optional[AlpacaConnector] = initialize_alpaca_client(
    ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER, ALPACA_FEED_STR, ALPACA_BASE_URL
)

def cleanup():
    streamlit_logger.info("ATELEXIT: Cleanup function called.")
    alpaca_client_to_clean: Optional[AlpacaConnector] = None
    try:
        # Try to get from cache_resource first (might not be reliable in atexit)
        alpaca_client_to_clean = initialize_alpaca_client(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER, ALPACA_FEED_STR, ALPACA_BASE_URL)
        if alpaca_client_to_clean: streamlit_logger.info("ATELEXIT: Successfully re-obtained cached Alpaca client.")
        else:
            streamlit_logger.warning("ATELEXIT: Could not re-obtain cached Alpaca client. Trying session_state backup.")
            alpaca_client_to_clean = st.session_state.get("alpaca_client_for_atexit") # Use specific key
            if alpaca_client_to_clean: streamlit_logger.info("ATELEXIT: Obtained Alpaca client from session_state.")
            else: streamlit_logger.warning("ATELEXIT: Could not obtain Alpaca client from session_state either.")
    except Exception as e:
        streamlit_logger.error(f"ATELEXIT: Error attempting to get Alpaca client for cleanup: {e}", exc_info=True)
        if not alpaca_client_to_clean: # If still not obtained
            alpaca_client_to_clean = st.session_state.get("alpaca_client_for_atexit")

    ws_thread: Optional[threading.Thread] = st.session_state.get("ws_thread")
    ws_loop: Optional[asyncio.AbstractEventLoop] = st.session_state.get("ws_loop")

    streamlit_logger.info(f"ATELEXIT: Resources - client: {alpaca_client_to_clean is not None}, thread: {ws_thread is not None}, loop: {ws_loop is not None}")

    if alpaca_client_to_clean and hasattr(alpaca_client_to_clean, 'stop_stream') and \
       hasattr(alpaca_client_to_clean, '_websocket_running') and alpaca_client_to_clean._websocket_running:
        streamlit_logger.info("ATELEXIT: Signalling Alpaca client's WebSocket stream to stop gracefully...")
        if ws_loop and not ws_loop.is_closed(): # Check if loop object exists and is not closed
             # Important: Check if the loop is still running or can run tasks
             # Sometimes in atexit, the loop might be technically open but shutting down.
             # We use call_soon_threadsafe or try run_until_complete if possible
             try:
                  # This needs to be run *in* the event loop thread.
                  # call_soon_threadsafe schedules the coroutine to run in the loop.
                  # We then wait for it to complete.
                  # This is the trickiest part in atexit. Running a new async event loop just for this might be safer.
                  # Option A: Use run_coroutine_threadsafe if the loop is still running
                  if ws_loop.is_running():
                      streamlit_logger.info("ATELEXIT: Loop is running, attempting run_coroutine_threadsafe.")
                      future = asyncio.run_coroutine_threadsafe(alpaca_client_to_clean.stop_stream(), ws_loop)
                      future.result(timeout=3) # Wait for the stop coroutine to finish
                      streamlit_logger.info("ATELEXIT: Alpaca client WebSocket stop signal processed by loop.")
                  else:
                       # Option B: If the loop isn't running, it might be safe to just call stop_stream directly
                       # This is less ideal as stop_stream is async. Running a *new* minimal loop might be necessary.
                       streamlit_logger.warning("ATELEXIT: WS loop not running. Trying direct stop_stream call (less reliable).")
                       # This won't await properly, but might trigger cancellation.
                       # A better approach here would be to run stop_stream in a *new*, temporary loop if needed.
                       try:
                           new_cleanup_loop = asyncio.new_event_loop()
                           new_cleanup_loop.run_until_complete(alpaca_client_to_clean.stop_stream())
                           new_cleanup_loop.close()
                           streamlit_logger.info("ATELEXIT: stop_stream run in new temporary loop.")
                       except Exception as e_new_loop:
                            streamlit_logger.error(f"ATELEXIT: Error running stop_stream in new temp loop: {e_new_loop}", exc_info=True)
                       
                       # As a final fallback, just mark the flag false
                       if hasattr(alpaca_client_to_clean, '_websocket_running'):
                            alpaca_client_to_clean._websocket_running = False
                            streamlit_logger.info("ATELEXIT: Fallback: Explicitly set _websocket_running = False.")


             except Exception as e_stop_stream:
                 streamlit_logger.error(f"ATELEXIT: Error during graceful stop_stream attempt: {e_stop_stream}", exc_info=True)
        else:
             streamlit_logger.warning("ATELEXIT: WS loop object not available, closed, or not running. Cannot attempt graceful stop.")
             # Ensure the flag is false as a fallback
             if alpaca_client_to_clean and hasattr(alpaca_client_to_clean, '_websocket_running'):
                  alpaca_client_to_clean._websocket_running = False
                  streamlit_logger.info("ATELEXIT: Fallback: Explicitly set _websocket_running = False.")
    
    if ws_loop and not ws_loop.is_closed():
        streamlit_logger.info(f"ATELEXIT: Requesting WebSocket event loop (ID: {id(ws_loop)}) to stop.")
        if ws_loop.is_running():
            ws_loop.call_soon_threadsafe(ws_loop.stop)
            time.sleep(0.1) # Give a moment for stop to process
        # The loop should be closed by its thread's finally block.
        # Don't close from here directly as it can cause issues if the thread isn't done.
        # loop.call_soon_threadsafe(ws_loop.close) # This could be risky if thread still using it.
        # Rely on thread's finally block to close.

    if ws_thread and ws_thread.is_alive():
        streamlit_logger.info(f"ATELEXIT: Waiting for WebSocket thread (ID: {ws_thread.ident}) to join...")
        ws_thread.join(timeout=5)
        if ws_thread.is_alive(): streamlit_logger.warning("ATELEXIT: WebSocket thread did not join in time.")
        else: streamlit_logger.info("ATELEXIT: WebSocket thread joined successfully.")
    
    streamlit_logger.info("ATELEXIT: Cleanup finished.")
    print("ATELEXIT: Cleanup finished (stdout).") # Keep for critical debugging


if 'cleanup_registered' not in st.session_state:
    streamlit_logger.info("Registering atexit cleanup function.")
    st.session_state.alpaca_client_for_atexit = alpaca # Store specific key for atexit
    atexit.register(cleanup)
    st.session_state.cleanup_registered = True
else:
    st.session_state.alpaca_client_for_atexit = alpaca # Ensure it's updated

if 'ws_thread' not in st.session_state: st.session_state.ws_thread = None
if 'ws_loop' not in st.session_state: st.session_state.ws_loop = None
if 'ws_tickers_streaming' not in st.session_state: st.session_state.ws_tickers_streaming = []


st.title("🚀 Alpaca Strategy Scanner")
st.sidebar.header("⚙️ Scanner Settings")

if alpaca and alpaca.is_operational:
    st.sidebar.success(f"✅ Alpaca Client Operational ({alpaca.data_feed.upper()} Feed)")
    st.sidebar.caption(f"Paper Trading: {alpaca.paper_trading}, Base URL: {alpaca.base_url}")
else:
    st.sidebar.error("❌ Alpaca Client Not Operational")
    if ALPACA_API_KEY is None or ALPACA_SECRET_KEY is None or ALPACA_API_KEY == "placeholder_api_key" or ALPACA_SECRET_KEY == "placeholder_secret_key":
        st.sidebar.info("Hint: Add ALPACA_API_KEY and ALPACA_SECRET_KEY to `.streamlit/secrets.toml`.")
    elif alpaca and not alpaca.feed: # alpaca object exists but feed is invalid
        st.sidebar.warning(f"Hint: Configured feed '{ALPACA_FEED_STR}' might be invalid or unsupported by your account. Check Alpaca dashboard and logs.")
    elif alpaca is None: # Alpaca client failed to initialize at all
        st.sidebar.warning("Hint: Alpaca client could not be initialized. Check logs for critical errors.")
    else: # Alpaca client initialized but not operational (e.g. bad keys but not placeholders)
        st.sidebar.warning("Hint: Alpaca keys might be invalid or account issues. Check logs.")
    st.sidebar.caption("Using yFinance fallback for historical data.")

st.sidebar.markdown("---")
st.sidebar.markdown("#### 1. Select Strategies")

if 'individual_strategy_selections' not in st.session_state:
    default_selected = STRATEGY_CATEGORIES.get("Momentum", [])
    st.session_state.individual_strategy_selections = {
        s_name: (s_name in default_selected) for s_name in ALL_UNIQUE_STRATEGY_NAMES
    }
else:
    current_selections = st.session_state.individual_strategy_selections
    st.session_state.individual_strategy_selections = {
        s_name: current_selections.get(s_name, False) for s_name in ALL_UNIQUE_STRATEGY_NAMES
    }

col_main_all, col_main_none = st.sidebar.columns(2)
if col_main_all.button("✅ Select ALL Strategies", key="select_all_strategies_overall_btn", use_container_width=True):
    for s_name in st.session_state.individual_strategy_selections: st.session_state.individual_strategy_selections[s_name] = True
    st.rerun()
if col_main_none.button("❌ Clear ALL Selections", key="clear_all_strategies_overall_btn", use_container_width=True):
    for s_name in st.session_state.individual_strategy_selections: st.session_state.individual_strategy_selections[s_name] = False
    st.rerun()

st.sidebar.markdown("---")
for category_name, strategies_in_category in STRATEGY_CATEGORIES.items():
    valid_strategies_in_category = [s for s in strategies_in_category if s in ALL_UNIQUE_STRATEGY_NAMES]
    if not valid_strategies_in_category: continue
    num_selected_in_cat = sum(1 for s_name in valid_strategies_in_category if st.session_state.individual_strategy_selections.get(s_name, False))
    is_expanded = category_name == "Momentum" or num_selected_in_cat > 0
    with st.sidebar.expander(f"{category_name} ({num_selected_in_cat}/{len(valid_strategies_in_category)} selected)", expanded=is_expanded):
        col_cat_all, col_cat_none = st.columns(2)
        cat_key_prefix = category_name.replace(' ', '_').replace('&', '').replace('-', '_')
        if col_cat_all.button(f"All in {category_name}", key=f"select_all_cat_{cat_key_prefix}", use_container_width=True):
            for strat_name in valid_strategies_in_category: st.session_state.individual_strategy_selections[strat_name] = True
            st.rerun()
        if col_cat_none.button(f"None in {category_name}", key=f"deselect_all_cat_{cat_key_prefix}", use_container_width=True):
            for strat_name in valid_strategies_in_category: st.session_state.individual_strategy_selections[strat_name] = False
            st.rerun()
        st.markdown("<div style='margin-top: 5px; margin-bottom: 5px;'></div>", unsafe_allow_html=True)
        for strategy_name in valid_strategies_in_category:
            checkbox_key = f"checkbox_{cat_key_prefix}_{strategy_name.replace(' ', '_').replace('/', '_').replace('-', '_').replace('(', '').replace(')', '')}"
            current_state = st.session_state.individual_strategy_selections[strategy_name]
            new_state = st.checkbox(strategy_name, value=current_state, key=checkbox_key)
            if new_state != current_state:
                st.session_state.individual_strategy_selections[strategy_name] = new_state
                st.rerun()

selected_strategies = sorted([s_name for s_name, is_sel in st.session_state.individual_strategy_selections.items() if is_sel])
st.sidebar.markdown("---")
st.sidebar.subheader(f"📋 Strategies Selected: {len(selected_strategies)}")
st.sidebar.caption(", ".join([f"_{s}_" for s in selected_strategies]) if selected_strategies else "No strategies selected yet.")

st.sidebar.markdown("---")
st.sidebar.markdown("#### 2. Select Tickers")

if 'fmp_tickers' not in st.session_state: st.session_state.fmp_tickers = []
if 'fmp_last_refresh' not in st.session_state: st.session_state.fmp_last_refresh = None






# --- קלט טיקרים ידני משופר ---
manual_tickers_input = st.sidebar.text_area(
    "📥 OR Enter tickers (any format, comma/space/newline separated):",
    placeholder="AAPL, MSFT GOOG\nTSLA\n nvda",
    height=100,
    key="manual_tickers_input",
    
)


    # 👇 החלק שמשפר קלט חופשי של טיקרים
raw_manual_input = manual_tickers_input.replace(",", "\n").replace(" ", "\n").split("\n")
current_tickers_to_scan = [
    t.strip().upper()
    for t in raw_manual_input
    if t.strip() and t.strip().isalnum() and len(t.strip()) <= 5 and '.' not in t.strip()
]
if current_tickers_to_scan:
    st.sidebar.caption(f"Manual: {', '.join(current_tickers_to_scan)}")

# --- אזהרה אם לא נבחרו טיקרים ---
if not current_tickers_to_scan:
    st.sidebar.warning("⚠️ No valid tickers selected for scanning.")


st.sidebar.markdown("---")
scan_button = st.sidebar.button(
    "🚀 Scan Selected Strategies",
    disabled=not current_tickers_to_scan or not selected_strategies,
    key="scan_button_main", use_container_width=True
)

# --- WebSocket Management ---
if alpaca and alpaca.is_operational:
    tickers_for_ws = list(set(current_tickers_to_scan))
    ws_thread_active = st.session_state.ws_thread is not None and st.session_state.ws_thread.is_alive()
    current_streaming_tickers = st.session_state.ws_tickers_streaming
    should_restart_ws = False

    def stop_current_ws():
        streamlit_logger.info("WS Management: Attempting to stop current WebSocket.")
        # Attempt to stop the stream gracefully via asyncio if the loop is running
        if hasattr(alpaca, '_websocket_running') and alpaca._websocket_running and \
           st.session_state.ws_loop and not st.session_state.ws_loop.is_closed() and \
           st.session_state.ws_loop.is_running():
            try:
                # Correcting the method name to stop_stream
                future = asyncio.run_coroutine_threadsafe(alpaca.stop_stream(), st.session_state.ws_loop)
                future.result(timeout=3)
                streamlit_logger.info("WS Management: Existing WebSocket stop signal sent and processed.")
            except asyncio.TimeoutError: streamlit_logger.warning("WS Management: Timeout waiting for existing WebSocket stop.")
            except Exception as e_stop_ws:
                streamlit_logger.error(f"WS Management: Error sending stop signal: {e_stop_ws}", exc_info=True)
        else:
             streamlit_logger.info("WS Management: Existing stream not running via loop or loop is closed/not running.")

        # Force stop the loop from the main thread as a fallback/cleanup step
        if st.session_state.ws_loop and not st.session_state.ws_loop.is_closed() and st.session_state.ws_loop.is_running():
             streamlit_logger.info("WS Management: Signalling existing Event loop to stop.")
             st.session_state.ws_loop.call_soon_threadsafe(st.session_state.ws_loop.stop)

        # Wait for the thread to finish
        if st.session_state.ws_thread and st.session_state.ws_thread.is_alive():
            streamlit_logger.info("WS Management: Waiting for old WS thread to join...")
            st.session_state.ws_thread.join(timeout=5) # Increased timeout slightly
            if st.session_state.ws_thread.is_alive():
                streamlit_logger.warning("WS Management: Old WS thread did not join in time.")
            else:
                streamlit_logger.info("WS Management: Old WS thread joined successfully.")
        
        # ✅ ADD THIS LINE: Explicitly reset the flag on the AlpacaConnector instance
        if alpaca and hasattr(alpaca, '_websocket_running'):
             streamlit_logger.info("WS Management: Explicitly resetting alpaca_client._websocket_running flag.")
             alpaca._websocket_running = False


        st.session_state.ws_thread = None
        st.session_state.ws_loop = None # Loop should be closed by thread's finally block now
        st.session_state.ws_tickers_streaming = []


    if not tickers_for_ws:
        if ws_thread_active:
            streamlit_logger.info("WS Management: No tickers selected, stopping active WebSocket.")
            stop_current_ws()
            time.sleep(0.5)    
            st.sidebar.caption("WebSocket stopped (no tickers).")
        # else: st.sidebar.caption("WebSocket inactive (no tickers).") # This can be noisy
    else:
        if not ws_thread_active:
            streamlit_logger.info("WS Management: Thread not active. Starting WebSocket.")
            should_restart_ws = True
        elif set(current_streaming_tickers) != set(tickers_for_ws):
            streamlit_logger.info(f"WS Management: Ticker list changed. Old: {current_streaming_tickers}, New: {tickers_for_ws}. Restarting WebSocket.")
            stop_current_ws()
            should_restart_ws = True
        else:
            st.sidebar.caption(f"WebSocket streaming: {', '.join(current_streaming_tickers)}")

        if should_restart_ws:
            streamlit_logger.info("WS Management: Starting/Restarting WebSocket thread.")
            new_loop = asyncio.new_event_loop()
            st.session_state.ws_loop = new_loop
            st.session_state.ws_thread = threading.Thread(
                target=start_websocket_thread_loop,
                args=(new_loop, alpaca, tickers_for_ws),
                daemon=True
            )
            st.session_state.ws_thread.start()
            st.session_state.ws_tickers_streaming = tickers_for_ws
            st.sidebar.caption(f"WebSocket initiated for: {', '.join(tickers_for_ws)}")
            streamlit_logger.info(f"WS Management: New WebSocket thread started for {len(tickers_for_ws)} tickers.")
else:
    st.sidebar.caption("WebSocket disabled (Alpaca client not operational or not initialized).")


# --- Main Area Display (Dashboard) ---


# --- Strategy Scanning Logic ---
if scan_button:
    if not selected_strategies: st.warning("No strategies selected for scanning.")
    elif not current_tickers_to_scan: st.warning("No tickers selected for scanning.")
    else:
        st.markdown("---")
        st.subheader(f"📡 Strategy Scan Results for {len(current_tickers_to_scan)} Tickers")
        st.caption(f"Scanning {len(selected_strategies)} strategies: {', '.join(selected_strategies)}")

        scan_timeframe = "5Min"
        scan_limit = 300
        progress_bar_scan = st.progress(0.0, text=f"Starting scan for {len(current_tickers_to_scan)} tickers...")
        
        all_historical_data: Dict[str, pd.DataFrame] = {}
        data_source_msg = "yFinance fallback (Alpaca client not available/operational)"
        if alpaca and alpaca.is_operational:
            data_source_msg = f"Alpaca ({alpaca.data_feed } feed)"
        elif alpaca: # Client exists but not fully operational
             data_source_msg = "yFinance fallback (Alpaca client not fully operational)"


        st.info(f"Attempting data fetch using {data_source_msg}...")
        try:
            with st.spinner(f"Downloading historical data ({scan_timeframe}, {scan_limit} bars) using {data_source_msg}..."):
                if alpaca: # Alpaca client object exists
                    all_historical_data = alpaca.get_historical_data(
                        current_tickers_to_scan, timeframe_str=scan_timeframe, limit=scan_limit
                    )

                else: # Alpaca client is None (failed initialization)
                    dummy_client = AlpacaConnector(api_key="AKNBUFB8HJFN2XTQWXSK", secret_key="hSQOdDX7A1Ujj65N9nzE3qikNNUyNceKWGaolbmK", paper=False)
                    all_historical_data = dummy_client.get_historical_data(
                        current_tickers_to_scan, timeframe_str=scan_timeframe, limit_per_symbol=scan_limit
                    )
            st.success("Historical data download attempt complete.")
        except Exception as e:
            st.error(f"Failed to download historical data for scan: {e}")
            streamlit_logger.error(f"Failed to download historical data for scan: {e}", exc_info=True)
            all_historical_data = {} # Ensure it's empty on error

        results_container = st.container()
        num_tickers_processed_successfully = 0
        total_tickers_attempted = len(current_tickers_to_scan)

        if all_historical_data and any(not df.empty for df in all_historical_data.values()):
            for i, ticker in enumerate(current_tickers_to_scan):
                progress_bar_scan.progress((i + 1) / total_tickers_attempted, text=f"Scanning {ticker} ({i+1}/{total_tickers_attempted})")
                df_ticker = all_historical_data.get(ticker)
                if df_ticker is None or df_ticker.empty:
                    with results_container: st.warning(f"No historical data for {ticker}. Skipping.")
                    continue
                if len(df_ticker) < 50: # Basic data length check
                    with results_container: st.warning(f"Insufficient data ({len(df_ticker)} bars) for {ticker}. Min 50 needed. Skipping.")
                    continue
                try:
                    signals: Dict[str, str] = run_strategies(df_ticker.copy(), selected_strategies)
                    latest_bar = df_ticker.iloc[-1]
                    signal_texts_buy = [s_name for s_name, s_val in signals.items() if s_val == "BUY"]
                    signal_texts_sell = [s_name for s_name, s_val in signals.items() if s_val == "SELL"]
                    with results_container:
                        st.markdown(f"--- \n ### {ticker.upper()}")
                        col_info, col_chart = st.columns([1, 2])
                        with col_info:
                            st.metric("Last Close", f"${latest_bar['close']:.2f}", help=f"Timestamp: {latest_bar.name.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                            daily_volume = int(df_ticker['volume'].sum())  # סך הנפח מ־OHLCV intraday
                            st.metric("Total Volume (Intraday)", f"{daily_volume:,}")
                            if signal_texts_buy: st.success(f"🟢 BUY Signals: {', '.join(signal_texts_buy)}")
                            if signal_texts_sell: st.error(f"🔴 SELL Signals: {', '.join(signal_texts_sell)}")
                            if not signal_texts_buy and not signal_texts_sell: st.info("No BUY/SELL signals.")
                        with col_chart:
                            fig = go.Figure(data=[go.Candlestick(
                                x=df_ticker.index, open=df_ticker['open'], high=df_ticker['high'],
                                low=df_ticker['low'], close=df_ticker['close']
                            )])
                            fig.update_layout(height=250, margin=dict(l=10, r=10, t=5, b=5), xaxis_rangeslider_visible=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                            st.plotly_chart(fig, use_container_width=True)
                    num_tickers_processed_successfully += 1
                except Exception as e_strat:
                    with results_container: st.error(f"Error running strategies for {ticker}: {e_strat}")
                    streamlit_logger.error(f"Error running strategies for {ticker}: {e_strat}", exc_info=True)
        else:
            with results_container: st.warning("No historical data fetched for any ticker. Cannot run strategies.")
        
        progress_bar_scan.empty()
        if total_tickers_attempted > 0:
            if num_tickers_processed_successfully == total_tickers_attempted:
                st.success(f"Scan complete! Successfully processed all {total_tickers_attempted} tickers.")
            elif num_tickers_processed_successfully > 0:
                st.warning(f"Scan complete. Processed {num_tickers_processed_successfully}/{total_tickers_attempted} tickers. Some skipped.")
            else:
                st.error(f"Scan complete, but no tickers processed. Check data fetching logs.")
        # else: No tickers were selected, scan_button would be disabled.

# --- Donation Link ---
st.markdown("---")
st.markdown(
    """<div style="text-align: center; margin-top: 20px; margin-bottom: 20px;">
        <p style="font-size:18px; font-weight: bold;">Enjoying this tool? Consider supporting its development!</p>
        <a href="https://paypal.me/niveyal" target="_blank" style="background-color: #FFC439; color: #000000; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
           ☕ Buy me a coffee</a></div>""", unsafe_allow_html=True)

# --- Page Refresh/Reset Button ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Page & Clear State", key="refresh_page_clear_cache_button", use_container_width=True):
    streamlit_logger.info("Clearing caches and session state for full refresh.")
    st.cache_data.clear()
    st.cache_resource.clear()
    # Selectively clear parts of session_state if needed, or full clear
    # Be cautious if cleanup relies on specific session_state items that might be needed before full clear.
    # For a full reset, clearing all is usually intended.
    keys_to_keep = ['cleanup_registered', 'alpaca_client_for_atexit'] # Keep atexit related flags
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    st.rerun()
