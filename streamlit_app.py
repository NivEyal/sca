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
    page_title="🚀 Premium Trading Strategy Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS for Premium Look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    /* Root Variables */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --glass-bg: rgba(255, 255, 255, 0.15);
        --glass-border: rgba(255, 255, 255, 0.2);
    }
    
    /* Global Styles */
    .main .block-container {
        padding-top: 2rem;
        max-width: 1400px;
    }
    
    /* Custom Font */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Background */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .main-header {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid var(--glass-border);
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
    }
    
    .main-header h1 {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
        font-weight: 500;
    }
    
    .metric-card {
        background: var(--glass-bg);
        backdrop-filter: blur(15px);
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        border: 1px solid var(--glass-border);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--primary-gradient);
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(31, 38, 135, 0.5);
    }
    
    .strategy-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        border: 1px solid var(--glass-border);
        box-shadow: 0 4px 15px rgba(31, 38, 135, 0.2);
        transition: all 0.3s ease;
    }
    
    .strategy-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(31, 38, 135, 0.3);
    }
    
    .signal-buy {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        padding: 0.25rem 0.5rem;
        border-radius: 8px;
        font-weight: bold;
        border: 2px solid rgba(16, 185, 129, 0.3);
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
    }
    
    .signal-sell {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        padding: 0.25rem 0.5rem;
        border-radius: 8px;
        font-weight: bold;
        border: 2px solid rgba(239, 68, 68, 0.3);
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.2);
    }
    
    .signal-none {
        background: rgba(156, 163, 175, 0.15);
        color: #9ca3af;
        padding: 0.25rem 0.5rem;
        border-radius: 8px;
        border: 2px solid rgba(156, 163, 175, 0.3);
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid var(--glass-border);
    }
    
    /* Button Styling */
    .stButton > button {
        background: var(--primary-gradient);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 700;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
    }
    
    /* Select Box Styling */
    .stSelectbox > div > div {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid var(--glass-border);
        color: white;
    }
    
    /* Multiselect Styling */
    .stMultiSelect > div > div {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid var(--glass-border);
    }
    
    /* Checkbox Styling */
    .stCheckbox > label {
        color: white;
        font-weight: 500;
    }
    
    /* Slider Styling */
    .stSlider > div > div > div {
        background: var(--primary-gradient);
    }
    
    /* Text Input Styling */
    .stTextArea > div > div > textarea {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        color: white;
    }
    
    /* Success/Error Messages */
    .stSuccess {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    .stWarning {
        background: rgba(245, 158, 11, 0.15);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    /* Loading Spinner */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid var(--glass-border);
        color: white;
        font-weight: 600;
    }
    
    /* Dataframe Styling */
    .stDataFrame {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid var(--glass-border);
    }
    
    /* Plotly Chart Container */
    .js-plotly-plot {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid var(--glass-border);
        padding: 1rem;
    }
    
    /* Custom animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .metric-card, .strategy-card {
        animation: fadeInUp 0.6s ease forwards;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        
        .main-header p {
            font-size: 1rem;
        }
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
    <h1>🚀 Premium Trading Strategy Scanner</h1>
    <p>Advanced AI-powered market analysis with 50+ professional trading strategies</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown("### ⚙️ Premium Configuration")
    
    # Connection Status
    st.markdown("#### 📡 Connection Status")
    if st.session_state.alpaca_connector and st.session_state.alpaca_connector.is_operational:
        st.success("✨ Alpaca Markets Connected")
    else:
        st.error("❌ Connection Failed")
        if st.button("🔄 Reconnect to Markets"):
            with st.spinner("Connecting to Alpaca..."):
                try:
                    st.session_state.alpaca_connector = AlpacaConnector(
                        paper=False,  # Using live account with your credentials
                        feed=DataFeed.IEX
                    )
                    if st.session_state.alpaca_connector.is_operational:
                        st.success("✨ Connected successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Connection failed: {e}")
    
    st.divider()
    
    # Ticker Selection
    st.markdown("#### 📊 Smart Ticker Selection")
    
    ticker_source = st.radio(
        "🎯 Data Source:",
        ["🔥 Top Volume Stocks", "✏️ Custom Tickers"],
        help="Choose between AI-curated top volume stocks or enter your own symbols"
    )
    
    if ticker_source == "🔥 Top Volume Stocks":
        num_tickers = st.slider("📈 Number of stocks:", 5, 20, 10, help="Select how many top volume stocks to analyze")
        if st.button("🚀 Load Premium Stocks"):
            with st.spinner("Loading top volume stocks..."):
                tickers = get_top_volume_tickers(limit=num_tickers)
                st.session_state.selected_tickers = tickers if tickers else DEFAULT_TICKERS[:num_tickers]
                st.success(f"✨ Loaded {len(tickers)} premium stocks")
    else:
        custom_input = st.text_area(
            "📝 Enter tickers (one per line or comma-separated):",
            placeholder="AAPL\nTSLA\nNVDA\nMSFT",
            height=120,
            help="Enter stock symbols you want to analyze"
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
        st.info(f"🎯 **Selected:** {', '.join(st.session_state.selected_tickers[:5])}" + 
                (f" **+{len(st.session_state.selected_tickers)-5} more**" if len(st.session_state.selected_tickers) > 5 else ""))
    
    st.divider()
    
    # Strategy Selection
    st.markdown("#### 🧠 AI Strategy Selection")
    
    selected_strategies = []
    
    # Quick select buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Select All Strategies"):
            selected_strategies = [strategy for strategies in STRATEGY_CATEGORIES.values() for strategy in strategies]
    with col2:
        if st.button("🗑️ Clear Selection"):
            selected_strategies = []
    
    # Category selection
    for category, strategies in STRATEGY_CATEGORIES.items():
        with st.expander(f"🎯 {category}", expanded=False):
            for strategy in strategies:
                if st.checkbox(f"📊 {strategy}", key=f"strat_{strategy}"):
                    if strategy not in selected_strategies:
                        selected_strategies.append(strategy)
                elif strategy in selected_strategies:
                    selected_strategies.remove(strategy)
    
    st.divider()
    
    # Scan Settings
    st.markdown("#### ⚡ Advanced Scan Settings")
    
    timeframe_display = st.selectbox(
        "⏰ Analysis Timeframe:",
        list(TIMEFRAMES.keys()),
        index=1,
        help="Select the timeframe for market data analysis"
    )
    
    timeframe = TIMEFRAMES[timeframe_display]
    default_limit = DATA_LIMITS.get(timeframe, 200)
    data_limit = st.slider("📊 Data Points:", 50, 500, default_limit, help="Number of data points to analyze")
    
    auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=st.session_state.auto_refresh, help="Automatically refresh results every 30 seconds")
    st.session_state.auto_refresh = auto_refresh
    
    # Scan button
    scan_button = st.button("🚀 Start Premium Analysis", type="primary", use_container_width=True)

# Main content area
if not st.session_state.selected_tickers:
    st.info("🎯 **Please select tickers from the sidebar to begin your premium analysis**")
    st.stop()

if not selected_strategies:
    st.info("🧠 **Please select at least one AI strategy from the sidebar**")
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
    progress_container = st.container()
    with progress_container:
        st.markdown("### 🔄 Analyzing Market Data...")
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    try:
        # Fetch market data
        status_text.markdown("**📊 Fetching real-time market data...**")
        progress_bar.progress(20)
        
        market_data = st.session_state.alpaca_connector.get_historical_data(
            tickers=st.session_state.selected_tickers,
            timeframe_str=timeframe,
            limit=data_limit
        )
        
        progress_bar.progress(50)
        status_text.markdown("**🧠 Running AI strategy analysis...**")
        
        # Run strategies
        strategy_results = run_strategies(market_data, selected_strategies)
        
        progress_bar.progress(80)
        status_text.markdown("**📈 Generating premium insights...**")
        
        # Store results
        st.session_state.market_data = market_data
        st.session_state.strategy_results = strategy_results
        st.session_state.last_scan_time = time.time()
        
        progress_bar.progress(100)
        status_text.markdown("**✅ Analysis completed successfully!**")
        
        time.sleep(1)  # Brief pause to show completion
        progress_container.empty()
        
    except Exception as e:
        st.error(f"❌ Scan failed: {e}")
        logger.error(f"Scan error: {e}")

# Display results
if st.session_state.strategy_results:
    st.markdown("## 📊 Premium Analysis Results")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_signals = len(st.session_state.strategy_results)
    buy_signals = len([r for r in st.session_state.strategy_results if any("BUY" in str(signal) for signal in r.get("entry_signals", []))])
    sell_signals = len([r for r in st.session_state.strategy_results if any("SELL" in str(signal) for signal in r.get("entry_signals", []))])
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🎯 Total Signals</h3>
            <h1>{}</h1>
        </div>
        """.format(total_signals), unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>📈 Buy Signals</h3>
            <h1 style="color: #10b981;">{}</h1>
        </div>
        """.format(buy_signals), unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>📉 Sell Signals</h3>
            <h1 style="color: #ef4444;">{}</h1>
        </div>
        """.format(sell_signals), unsafe_allow_html=True)
    with col4:
        scan_time = datetime.fromtimestamp(st.session_state.last_scan_time).strftime("%H:%M:%S")
        st.markdown("""
        <div class="metric-card">
            <h3>⏰ Last Analysis</h3>
            <h1>{}</h1>
        </div>
        """.format(scan_time), unsafe_allow_html=True)
    
    st.divider()
    
    # Results by symbol
    for result in st.session_state.strategy_results:
        symbol = result["symbol"]
        strategy = result["strategy"]
        entry_signals = result.get("entry_signals", [])
        
        if not entry_signals:
            continue
            
        with st.expander(f"🎯 **{symbol}** - {strategy}", expanded=True):
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
                            title=f"📊 {symbol} - {timeframe} Analysis",
                            yaxis_title="Price",
                            yaxis2=dict(title="Volume", overlaying="y", side="right"),
                            height=400,
                            showlegend=False,
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white')
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Signal details
                st.markdown("#### 🎯 AI Signals")
                for signal in entry_signals:
                    if "Buy" in signal:
                        st.markdown('<div class="signal-buy">🚀 BUY SIGNAL</div>', unsafe_allow_html=True)
                    elif "Sell" in signal:
                        st.markdown('<div class="signal-sell">📉 SELL SIGNAL</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="signal-none">⚪ NEUTRAL SIGNAL</div>', unsafe_allow_html=True)
                
                # Latest data
                if symbol in st.session_state.market_data:
                    df = st.session_state.market_data[symbol]
                    if not df.empty:
                        latest = df.iloc[-1]
                        
                        price_change = ((latest['close'] - df.iloc[0]['open']) / df.iloc[0]['open']) * 100
                        
                        st.markdown("#### 📊 Market Data")
                        st.metric("💰 Latest Price", f"${latest['close']:.2f}", f"{price_change:+.2f}%")
                        st.metric("📊 Volume", f"{latest['volume']:,}")
                        st.metric("📈 High", f"${latest['high']:.2f}")
                        st.metric("📉 Low", f"${latest['low']:.2f}")

# Auto-refresh countdown
if auto_refresh and st.session_state.last_scan_time:
    time_since_scan = time.time() - st.session_state.last_scan_time
    time_remaining = max(0, 30 - time_since_scan)
    
    if time_remaining > 0:
        st.sidebar.info(f"🔄 **Next premium refresh in {int(time_remaining)}s**")
        time.sleep(1)
        st.rerun()
    else:
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p style='color: white; font-size: 1.2rem; font-weight: 600;'>🚀 Premium Trading Strategy Scanner | Powered by Advanced AI</p>
    <p style='color: rgba(255,255,255,0.8); font-size: 1rem;'>⚠️ This is for educational and research purposes only. Not financial advice.</p>
    <p style='color: rgba(255,255,255,0.6); font-size: 0.9rem;'>Built with ❤️ using Streamlit, Alpaca Markets, and cutting-edge AI technology</p>
</div>
""", unsafe_allow_html=True)