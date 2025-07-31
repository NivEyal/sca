import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import asyncio
import time
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your existing modules
try:
    from alpaca_connector import AlpacaConnector, DataFeed
    from strategy import run_strategies, STRATEGY_MAP
    from top_volume import get_top_volume_tickers
    from config import STRATEGY_CATEGORIES, TIMEFRAMES, DATA_LIMITS, DEFAULT_TICKERS
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="🚀 Trading Strategy Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for smoother interface
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .strategy-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #28a745;
    }
    
    .signal-buy {
        background-color: #d4edda;
        color: #155724;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    
    .signal-sell {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    
    .signal-none {
        background-color: #e2e3e5;
        color: #383d41;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .sidebar .stSelectbox > div > div {
        background-color: #f8f9fa;
        border-radius: 8px;
    }
    
    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    if 'alpaca_connector' not in st.session_state:
        # Initialize connector with your API keys
        try:
            st.session_state.alpaca_connector = AlpacaConnector(
                paper=False,  # Using live account
                feed=DataFeed.IEX
            )
        except Exception as e:
            st.session_state.alpaca_connector = None
            logger.error(f"Failed to initialize Alpaca connector: {e}")
    if 'market_data' not in st.session_state:
        st.session_state.market_data = {}
    if 'strategy_results' not in st.session_state:
        st.session_state.strategy_results = {}
    if 'last_scan_time' not in st.session_state:
        st.session_state.last_scan_time = None
    if 'selected_tickers' not in st.session_state:
        st.session_state.selected_tickers = DEFAULT_TICKERS[:5]  # Start with 5 default tickers
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False

init_session_state()

# Header
st.markdown("""
<div class="main-header">
    <h1>🚀 Advanced Trading Strategy Scanner</h1>
    <p>Real-time market analysis with professional trading strategies</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Connection Status
    st.subheader("📡 Connection Status")
    if st.session_state.alpaca_connector and st.session_state.alpaca_connector.is_operational:
        st.success("✅ Alpaca Connected")
    else:
        st.error("❌ Not Connected")
        if st.button("🔄 Reconnect"):
            with st.spinner("Connecting to Alpaca..."):
                try:
                    st.session_state.alpaca_connector = AlpacaConnector(
                        paper=False,  # Using live account with your credentials
                        feed=DataFeed.IEX
                    )
                    if st.session_state.alpaca_connector.is_operational:
                        st.success("Connected successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Connection failed: {e}")
    
    st.divider()
    
    # Ticker Selection
    st.subheader("📊 Ticker Selection")
    
    ticker_source = st.radio(
        "Data Source:",
        ["Top Volume Stocks", "Custom Tickers"],
        help="Choose between auto-loaded top volume stocks or enter your own"
    )
    
    if ticker_source == "Top Volume Stocks":
        num_tickers = st.slider("Number of stocks:", 5, 20, 10)
        if st.button("🔄 Load Top Volume"):
            with st.spinner("Loading top volume stocks..."):
                tickers = get_top_volume_tickers(limit=num_tickers)
                st.session_state.selected_tickers = tickers if tickers else DEFAULT_TICKERS[:num_tickers]
                st.success(f"Loaded {len(tickers)} tickers")
    else:
        custom_input = st.text_area(
            "Enter tickers (one per line or comma-separated):",
            placeholder="AAPL\nTSLA\nNVDA\nMSFT",
            height=100
        )
        if custom_input:
            # Parse input - handle both newlines and commas
            tickers = []
            for line in custom_input.replace(',', '\n').split('\n'):
                ticker = line.strip().upper()
                if ticker:
                    tickers.append(ticker)
            st.session_state.selected_tickers = tickers
    
    # Display selected tickers
    if st.session_state.selected_tickers:
        st.info(f"Selected: {', '.join(st.session_state.selected_tickers[:5])}" + 
                (f" +{len(st.session_state.selected_tickers)-5} more" if len(st.session_state.selected_tickers) > 5 else ""))
    
    st.divider()
    
    # Strategy Selection
    st.subheader("🧠 Strategy Selection")
    
    selected_strategies = []
    
    # Quick select buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Select All"):
            selected_strategies = [strategy for strategies in STRATEGY_CATEGORIES.values() for strategy in strategies]
    with col2:
        if st.button("❌ Clear All"):
            selected_strategies = []
    
    # Category selection
    for category, strategies in STRATEGY_CATEGORIES.items():
        with st.expander(category, expanded=False):
            for strategy in strategies:
                if st.checkbox(strategy, key=f"strat_{strategy}"):
                    if strategy not in selected_strategies:
                        selected_strategies.append(strategy)
                elif strategy in selected_strategies:
                    selected_strategies.remove(strategy)
    
    st.divider()
    
    # Scan Settings
    st.subheader("⚡ Scan Settings")
    
    timeframe_display = st.selectbox(
        "Timeframe:",
        list(TIMEFRAMES.keys()),
        index=1
    )
    
    timeframe = TIMEFRAMES[timeframe_display]
    default_limit = DATA_LIMITS.get(timeframe, 200)
    data_limit = st.slider("Data points:", 50, 500, default_limit)
    
    auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=st.session_state.auto_refresh)
    st.session_state.auto_refresh = auto_refresh
    
    # Scan button
    scan_button = st.button("🚀 Start Scan", type="primary", use_container_width=True)

# Main content area
if not st.session_state.selected_tickers:
    st.info("👆 Please select tickers from the sidebar to begin scanning")
    st.stop()

if not selected_strategies:
    st.info("👆 Please select at least one strategy from the sidebar")
    st.stop()

# Auto-refresh logic
if auto_refresh and st.session_state.last_scan_time:
    time_since_scan = time.time() - st.session_state.last_scan_time
    if time_since_scan >= 30:  # 30 seconds
        scan_button = True

# Main scanning logic
if scan_button:
    if not st.session_state.alpaca_connector or not st.session_state.alpaca_connector.is_operational:
        st.error("❌ Please connect to Alpaca first (check sidebar)")
        st.stop()
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Fetch market data
        status_text.text("📊 Fetching market data...")
        progress_bar.progress(20)
        
        market_data = st.session_state.alpaca_connector.get_historical_data(
            tickers=st.session_state.selected_tickers,
            timeframe_str=timeframe,
            limit=data_limit
        )
        
        progress_bar.progress(50)
        status_text.text("🧠 Running strategy analysis...")
        
        # Run strategies
        strategy_results = run_strategies(market_data, selected_strategies)
        
        progress_bar.progress(80)
        status_text.text("📈 Generating results...")
        
        # Store results
        st.session_state.market_data = market_data
        st.session_state.strategy_results = strategy_results
        st.session_state.last_scan_time = time.time()
        
        progress_bar.progress(100)
        status_text.text("✅ Scan completed!")
        
        time.sleep(1)  # Brief pause to show completion
        progress_bar.empty()
        status_text.empty()
        
    except Exception as e:
        st.error(f"❌ Scan failed: {e}")
        logger.error(f"Scan error: {e}")

# Display results
if st.session_state.strategy_results:
    st.header("📊 Scan Results")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_signals = len(st.session_state.strategy_results)
    buy_signals = len([r for r in st.session_state.strategy_results if any("BUY" in str(signal) for signal in r.get("entry_signals", []))])
    sell_signals = len([r for r in st.session_state.strategy_results if any("SELL" in str(signal) for signal in r.get("entry_signals", []))])
    
    with col1:
        st.metric("Total Signals", total_signals)
    with col2:
        st.metric("Buy Signals", buy_signals, delta=buy_signals)
    with col3:
        st.metric("Sell Signals", sell_signals, delta=-sell_signals if sell_signals > 0 else 0)
    with col4:
        scan_time = datetime.fromtimestamp(st.session_state.last_scan_time).strftime("%H:%M:%S")
        st.metric("Last Scan", scan_time)
    
    st.divider()
    
    # Results by symbol
    for result in st.session_state.strategy_results:
        symbol = result["symbol"]
        strategy = result["strategy"]
        entry_signals = result.get("entry_signals", [])
        
        if not entry_signals:
            continue
            
        with st.expander(f"📈 {symbol} - {strategy}", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Price chart
                if symbol in st.session_state.market_data:
                    df = st.session_state.market_data[symbol]
                    if not df.empty:
                        fig = go.Figure()
                        
                        # Candlestick chart
                        fig.add_trace(go.Candlestick(
                            x=df.index,
                            open=df['open'],
                            high=df['high'],
                            low=df['low'],
                            close=df['close'],
                            name=symbol
                        ))
                        
                        # Volume
                        fig.add_trace(go.Bar(
                            x=df.index,
                            y=df['volume'],
                            name='Volume',
                            yaxis='y2',
                            opacity=0.3
                        ))
                        
                        fig.update_layout(
                            title=f"{symbol} - {timeframe} Chart",
                            yaxis_title="Price",
                            yaxis2=dict(title="Volume", overlaying="y", side="right"),
                            height=400,
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Signal details
                st.subheader("🎯 Signals")
                for signal in entry_signals:
                    if "Buy" in signal:
                        st.markdown('<div class="signal-buy">🟢 BUY SIGNAL</div>', unsafe_allow_html=True)
                    elif "Sell" in signal:
                        st.markdown('<div class="signal-sell">🔴 SELL SIGNAL</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="signal-none">⚪ NEUTRAL</div>', unsafe_allow_html=True)
                
                # Latest data
                if symbol in st.session_state.market_data:
                    df = st.session_state.market_data[symbol]
                    if not df.empty:
                        latest = df.iloc[-1]
                        st.metric("Latest Price", f"${latest['close']:.2f}")
                        st.metric("Volume", f"{latest['volume']:,}")

# Auto-refresh countdown
if auto_refresh and st.session_state.last_scan_time:
    time_since_scan = time.time() - st.session_state.last_scan_time
    time_remaining = max(0, 30 - time_since_scan)
    
    if time_remaining > 0:
        st.sidebar.info(f"🔄 Next refresh in {int(time_remaining)}s")
        time.sleep(1)
        st.rerun()
    else:
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>🚀 Advanced Trading Strategy Scanner | Built with Streamlit</p>
    <p>⚠️ This is for educational purposes only. Not financial advice.</p>
</div>
""", unsafe_allow_html=True)