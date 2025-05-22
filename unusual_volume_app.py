import streamlit as st
st.set_page_config(layout="wide", page_title="📈 Alpaca Advanced Stock Scanner")
st.title("📈 Alpaca Advanced Stock Scanner")
st.markdown("""
This scanner identifies stocks with unusual trading volume, price movements, and other technical signals.
**This is not financial advice. Do your own research.**
Scanning a very large number of tickers will take a significant amount of time.
""")

from strategy import run_strategies  # This uses strategy.py which calls all strategy functions
import alpaca_trade_api as tradeapi
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
tab1, tab2 = st.tabs(["📊 Unusual Volume Scanner", "🚀 Top Volume + Strategies"])
with tab1:
    st.caption("""
🎛️ **How to Use This Scanner**  
This app scans thousands of US stocks for potential trading setups. Here’s what the settings mean:

- **Avg Volume & Volume Multiplier**: Looks for stocks trading at unusually high volume compared to their recent average.
- **Price Range**: Filters stocks by current price.
- **% Change Today**: Minimum price movement required (up or down).
- **Advanced Filters**:
  - **Gap Scan**: Finds stocks that opened with a gap vs. yesterday's close.
  - **VWAP**: Compares price to intraday VWAP (approximate).
  - **Near Breakout**: Flags stocks near yesterday’s high.
  - **Consolidation Break**: Detects range breakouts based on historical highs/lows.
  - **Volatility Spike**: Price range is unusually large relative to recent ATR.
  - **Float Rotation**: Daily volume exceeds float proxy (shares outstanding).

📌 Use the **Preset Selector** on the left to try smart filters like “Momentum Hunt” or “Float Rotator”.

👉 Click **Run Scanner** to start, and scroll down for results.
""")

# Set up logging for debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Streamlit App Configuration ---


# --- API Key and Configuration Handling ---
# (This section remains the same as your provided code)
api = None
DATA_FEED = 'sip'
BASE_URL = "https://paper-api.alpaca.markets"

try:
    api_key_id_from_secrets = st.secrets["ALPACA_API_KEY"]
    api_secret_key_from_secrets = st.secrets["ALPACA_SECRET_KEY"]
    BASE_URL = st.secrets.get("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
    DATA_FEED = st.secrets.get("APCA_DATA_FEED", "sip")

    api = tradeapi.REST(
        key_id=api_key_id_from_secrets,
        secret_key=api_secret_key_from_secrets,
        base_url=BASE_URL,
        api_version='v2'
    )
    account = api.get_account()
    st.sidebar.success(f"✅ Connected to Alpaca! Account: {account.status}")
    if "paper" in BASE_URL.lower():
        st.sidebar.info("Mode: Paper Trading")
    else:
        st.sidebar.info("Mode: Live Trading")
    st.sidebar.info(f"Data Feed: {DATA_FEED.upper()}")
    if DATA_FEED.lower() == 'sip' and "paper" in BASE_URL.lower():
        st.sidebar.warning("Using SIP with paper trading. Ensure plan supports this or it might default.")

except KeyError as e:
    st.sidebar.error(f"Missing Alpaca API credential or configuration in st.secrets: {e}")
    # ... (rest of your error message for secrets)
    st.stop()
except Exception as e:
    st.sidebar.error(f"❌ Failed to connect to Alpaca: {e}")
    logger.error(f"Alpaca connection error: {e}")
    st.stop()

# --- Helper Functions ---
@st.cache_data(ttl=3600)
def get_all_tradable_assets_data(_api_ref):
    try:
        assets = _api_ref.list_assets(status='active', asset_class='us_equity')
        tradable_assets_data = []
        for asset in assets:
            if asset.tradable and asset.exchange != 'OTC' and asset.status == 'active':
                tradable_assets_data.append({
                    "symbol": asset.symbol, "name": asset.name, "exchange": asset.exchange,
                })
        logger.info(f"Found {len(tradable_assets_data)} tradable US equity assets (excluding OTC) for caching.")
        return tradable_assets_data
    except Exception as e:
        logger.error(f"Error fetching asset list: {e}")
        st.error(f"Failed to fetch tradable assets: {e}")
        return []

@st.cache_data(ttl=600)
def get_historical_data(_api_ref, symbols, lookback_days, data_feed_source, atr_period=14, consolidation_period=5):
    if not symbols: return {}
    try:
        today = datetime.now().date()
        end_date = today - timedelta(days=1)
        # Need enough data for lookback_days + ATR period + consolidation period
        start_date_buffer = max(lookback_days, atr_period, consolidation_period) + 45
        start_date = end_date - timedelta(days=start_date_buffer)

        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        logger.info(f"Fetching historical data for {len(symbols)} symbols from {start_date_str} to {end_date_str} using {data_feed_source} feed.")
        bars_df = _api_ref.get_bars(
            symbols, tradeapi.TimeFrame.Day, start=start_date_str, end=end_date_str,
            adjustment='raw', feed=data_feed_source
        ).df

        if bars_df.empty: return {}
        if 'symbol' not in bars_df.columns and isinstance(bars_df.index, pd.MultiIndex):
             bars_df = bars_df.reset_index(level=0)
        if not isinstance(bars_df.index, pd.DatetimeIndex):
             bars_df.index = pd.to_datetime(bars_df.index)
        if bars_df.index.tz is None:
             bars_df.index = bars_df.index.tz_localize('UTC')
        bars_df.index = bars_df.index.tz_convert('America/New_York').date

        result = {}
        for symbol_val in symbols:
            symbol_bars = bars_df[bars_df['symbol'].astype(str) == str(symbol_val)].copy()
            if not symbol_bars.empty:
                symbol_bars = symbol_bars.sort_index(ascending=True)

                # ATR Calculation
                if len(symbol_bars) >= atr_period:
                    high_low = symbol_bars['high'] - symbol_bars['low']
                    high_prev_close = abs(symbol_bars['high'] - symbol_bars['close'].shift(1))
                    low_prev_close = abs(symbol_bars['low'] - symbol_bars['close'].shift(1))
                    tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1, skipna=False)
                    symbol_bars[f'atr_{atr_period}'] = tr.rolling(atr_period).mean()

                # N-day High/Low for Consolidation Break
                if len(symbol_bars) >= consolidation_period:
                    symbol_bars[f'{consolidation_period}_day_high'] = symbol_bars['high'].rolling(consolidation_period).max()
                    symbol_bars[f'{consolidation_period}_day_low'] = symbol_bars['low'].rolling(consolidation_period).min()

                # Ensure we have enough data for avg volume lookback
                symbol_bars_df = symbol_bars.tail(lookback_days)
                if len(symbol_bars_df) >= lookback_days:
                    # We return the full symbol_bars which now includes ATR and N-day high/low history
                    # The avg volume will be calculated on the tail later.
                    result[symbol_val] = symbol_bars 
                else:
                    logger.warning(f"Insufficient data for {symbol_val} for avg vol: {len(symbol_bars_df)} bars, needed {lookback_days}")
            else:
                logger.warning(f"No data rows for {symbol_val} in historical batch.")
        return result
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbols[:5]}...: {e}")
        return {}

# --- Main Application Logic ---
if api:
    st.sidebar.header("🔑 Alpaca API Status") # Moved from original position
    # ... (API status messages remain here)

    st.sidebar.header("⚙️ Scanner Settings")
    # Core Volume & Price Settings
    lookback_days_avg_vol = st.sidebar.slider("Lookback days for Avg. Volume:", 5, 60, 20, key="lookback_hist")
    volume_multiplier = st.sidebar.slider("Min Volume Multiplier (Current > Avg * X):", 0.0, 20.0, 3.0, 0.1, key="vol_multi")
    min_price = st.sidebar.number_input("Minimum Stock Price:", value=1.0, min_value=0.01, step=0.1, key="min_p")
    max_price = st.sidebar.number_input("Maximum Stock Price:", value=200.0, min_value=1.0, step=1.0, key="max_p")
    min_avg_volume = st.sidebar.number_input("Minimum Avg Daily Volume (hist):", value=50000, min_value=0, step=10000, key="min_avg_vol")
    min_change_perc_today = st.sidebar.slider("Minimum Abs % Change Today:", 0.0, 20.0, 2.0, 0.5, key="min_change_abs", help="Minimum absolute percentage change for today (up or down).")

    # Advanced Signal Settings
    st.sidebar.subheader("Advanced Signals (Optional Filters)")
    enable_gap_scan = st.sidebar.checkbox("Enable Gap Scan", value=False, key="en_gap")
    min_gap_up_perc = st.sidebar.slider("Min Gap Up %:", 0.0, 10.0, 2.0, 0.1, key="gap_up", disabled=not enable_gap_scan)
    min_gap_down_perc = st.sidebar.slider("Min Gap Down % (e.g., -2%):", -10.0, 0.0, -2.0, 0.1, key="gap_down", disabled=not enable_gap_scan)

    enable_vwap_scan = st.sidebar.checkbox("Enable VWAP Scan (vs Approx. Minute VWAP)", value=False, key="en_vwap")
    # No specific slider for VWAP, just a signal if above/below

    enable_near_breakout_scan = st.sidebar.checkbox("Enable Near Breakout Scan", value=False, key="en_near_bo")
    near_breakout_proximity_perc = st.sidebar.slider("Near Breakout Proximity (% from prev day high):", 0.1, 5.0, 1.0, 0.1, key="near_bo_prox", disabled=not enable_near_breakout_scan)

    enable_selloff_scan = st.sidebar.checkbox("Enable High Volume Sell-off Scan", value=False, key="en_selloff")
    # Uses main volume_multiplier

    consolidation_period_days = st.sidebar.slider("Consolidation Period (for Range Breakout):", 3, 20, 5, 1, key="consol_period")
    enable_consol_break_scan = st.sidebar.checkbox(f"Enable {consolidation_period_days}-Day Range Breakout Scan", value=False, key="en_consol_bo")


    atr_period_days = st.sidebar.slider("ATR Period (days):", 5, 30, 14, 1, key="atr_p")
    enable_volatility_spike_scan = st.sidebar.checkbox("Enable Volatility Spike Scan", value=False, key="en_vol_spike")
    volatility_spike_multiplier = st.sidebar.slider("Volatility Spike Multiplier (Range > ATR * X):", 1.0, 5.0, 1.5, 0.1, key="vol_spike_multi", disabled=not enable_volatility_spike_scan)
    
    enable_float_rotation_scan = st.sidebar.checkbox("Enable Float Rotation Scan (Proxy)", value=False, key="en_float_rot")
    min_float_rotation = st.sidebar.slider("Min Float Rotation (Current Vol / Shares Outstanding):", 0.1, 5.0, 0.5, 0.1, key="min_float_rot_val", disabled=not enable_float_rotation_scan, help="Uses 'shares_outstanding' as proxy for float. Data may be limited/inaccurate.")


    total_available_assets = len(get_all_tradable_assets_data(api))
    max_slider_val = min(total_available_assets, 11263)
    max_stocks_to_scan_live = st.sidebar.slider(
        "Max stocks to fetch data for (performance):", 100, max_slider_val, 500, 50,
        help=f"Limits symbols for data fetching. Max available: {total_available_assets}."
    )
    sort_by = st.sidebar.selectbox("Sort results by:", ["Volume Ratio", "Change %", "Current Price", "Float Rotation"], index=0, key="sort")
    st.sidebar.header("🧠 Strategy Scanner")
    available_strategies = list(run_strategies.__globals__["STRATEGY_MAP"].keys())
    selected_strategies = st.sidebar.multiselect(
        "Select strategies to run:",
        available_strategies,
        default=["Momentum Trading", "Breakout Trading"]  # or leave empty
    )


    if st.sidebar.button("🔄 Run Scanner"):
        st.session_state.run_scan = True
    # ... (rest of your run_scan session state logic)

    if st.session_state.get('run_scan', False):
        with st.spinner("Fetching tradable assets list..."):
            all_assets_data = get_all_tradable_assets_data(api)
        if not all_assets_data: # ... (stop if no assets)
            st.warning("No tradable assets found."); st.stop()

        asset_symbols_all = [asset_data['symbol'] for asset_data in all_assets_data]
        st.info(f"Total tradable symbols: {len(asset_symbols_all)}. Processing up to {max_stocks_to_scan_live}.")
        symbols_to_process_hist = asset_symbols_all[:max_stocks_to_scan_live]

        st.header("⏳ Fetching Historical Data...")
        historical_data_map = {}
        hist_progress_bar_container = st.empty() 
        
        HISTORICAL_BATCH_SIZE = 200
        total_batches_hist = (len(symbols_to_process_hist) + HISTORICAL_BATCH_SIZE - 1) // HISTORICAL_BATCH_SIZE
        
        status_text_hist = st.empty()

        for i in range(0, len(symbols_to_process_hist), HISTORICAL_BATCH_SIZE):
            # THIS IS THE CRITICAL LINE THAT WAS MISSING/MISPLACED IN THE PREVIOUS CONTEXT
            batch_symbols = symbols_to_process_hist[i:i + HISTORICAL_BATCH_SIZE] # Define batch_symbols for the current iteration

            current_batch_num = i // HISTORICAL_BATCH_SIZE + 1
            status_text_hist.text(f"Fetching historical data: Batch {current_batch_num}/{total_batches_hist} ({len(batch_symbols)} symbols)")
            hist_progress_bar_container.progress(current_batch_num / total_batches_hist)
            try:
                # Now batch_symbols is correctly defined before being used
                batch_data = get_historical_data(
                    api, 
                    batch_symbols, # Use the defined batch_symbols
                    lookback_days_avg_vol, 
                    DATA_FEED, 
                    atr_period_days, 
                    consolidation_period_days
                )
                if batch_data:
                    historical_data_map.update(batch_data)
            except Exception as e:
                logger.error(f"Error fetching historical batch {current_batch_num} for symbols {batch_symbols[:5]}...: {e}")
        status_text_hist.text("Historical data fetching complete.")
        hist_progress_bar_container.empty()

        if not historical_data_map: 
            st.warning("No historical data could be fetched. Check logs, API limits, or market open status.")
            st.stop()
        st.success(f"Fetched and processed historical data for {len(historical_data_map)} symbols.")


        candidate_stocks_info = []
        symbols_for_snapshots = []
        for symbol, hist_df_full in historical_data_map.items(): # hist_df_full now contains ATR etc.
            # Calculate avg_volume from the tail of hist_df_full
            hist_df_for_avg_vol = hist_df_full.tail(lookback_days_avg_vol)
            if len(hist_df_for_avg_vol) < lookback_days_avg_vol:
                logger.warning(f"Not enough data for avg vol for {symbol} after full hist fetch. Has {len(hist_df_for_avg_vol)}")
                continue

            avg_volume = hist_df_for_avg_vol['volume'].mean()
            last_close_price = hist_df_for_avg_vol['close'].iloc[-1] if not hist_df_for_avg_vol.empty else 0

            if avg_volume >= min_avg_volume and min_price <= last_close_price <= max_price:
                symbols_for_snapshots.append(symbol)
                candidate_stocks_info.append({
                    "symbol": symbol, "avg_volume": avg_volume, "last_hist_close": last_close_price,
                    "hist_df_full": hist_df_full # Pass the full historical data for ATR etc.
                })
        
        if not symbols_for_snapshots: # ... (stop if no candidates after pre-filter)
            st.info("No stocks met pre-filter criteria for live data."); st.stop()

        st.header("📡 Fetching Live Data (Snapshots)...")
        snapshots_data = {}
        live_progress_bar_container = st.empty()
        
        SNAPSHOT_BATCH_SIZE = 100
        total_batches_live = (len(symbols_for_snapshots) + SNAPSHOT_BATCH_SIZE -1) // SNAPSHOT_BATCH_SIZE
        status_text_live = st.empty()

        for i in range(0, len(symbols_for_snapshots), SNAPSHOT_BATCH_SIZE):
            # THIS IS THE CRITICAL LINE THAT WAS MISSING/MISPLACED
            batch_symbols_snap = symbols_for_snapshots[i:i + SNAPSHOT_BATCH_SIZE] # Define batch_symbols_snap

            current_batch_num_live = i // SNAPSHOT_BATCH_SIZE + 1
            status_text_live.text(f"Fetching live snapshots: Batch {current_batch_num_live}/{total_batches_live} ({len(batch_symbols_snap)} symbols)")
            live_progress_bar_container.progress(current_batch_num_live / total_batches_live)
            try:
                if batch_symbols_snap: # Check if the batch is not empty
                    # Now batch_symbols_snap is correctly defined
                    current_snapshots = api.get_snapshots(batch_symbols_snap) 
                    snapshots_data.update(current_snapshots)
            except Exception as e:
                logger.error(f"Error fetching snapshots for batch {current_batch_num_live} ({batch_symbols_snap[:5]}...): {e}")
                st.warning(f"Could not fetch live snapshots for some symbols in batch {current_batch_num_live}.")
        status_text_live.text("Live snapshot fetching complete.")
        live_progress_bar_container.empty()

        if not snapshots_data:
            st.warning("Could not fetch any live snapshot data after batching attempts.")
            st.stop()
        st.success(f"Fetched live snapshots for {len(snapshots_data)} symbols that met pre-filters.")
        if selected_strategies:
            st.subheader("📈 Strategy Signals")
            for stock_info in candidate_stocks_info:
                symbol = stock_info["symbol"]
                hist_df = stock_info["hist_df_full"]

                if symbol not in snapshots_data or hist_df.empty:
                    continue

                try:
                    if isinstance(hist_df, pd.DataFrame) and not hist_df.empty:
                        scan_results = run_strategies({symbol: hist_df.copy()}, selected_strategies)
                        for result in scan_results:
                            buy_signals = [col for col in result.get("entry_signals", []) if "Buy" in col]
                            sell_signals = [col for col in result.get("entry_signals", []) if "Sell" in col]
                            st.markdown(f"### {symbol}")
                            if buy_signals:
                                st.success(f"🟢 BUY Signals from: {result['strategy']}")
                            if sell_signals:
                                st.error(f"🔴 SELL Signals from: {result['strategy']}")
                except Exception as e:
                    st.warning(f"⚠️ Strategy error for {symbol}: {e}")



        
        st.header("📊 Analyzing Candidates...")
        results_list = []
        asset_details_cache = {} # Cache for api.get_asset() calls

        with st.spinner("Analyzing data and fetching asset details for results..."):
            for stock_info in candidate_stocks_info:
                symbol = stock_info["symbol"]
                avg_volume = stock_info["avg_volume"]
                hist_df_full = stock_info["hist_df_full"] # Full historical data for this stock

                if symbol not in snapshots_data or snapshots_data[symbol] is None: continue
                snapshot = snapshots_data[symbol]
                
                current_price = None
                if snapshot.latest_trade and snapshot.latest_trade.p: current_price = snapshot.latest_trade.p
                elif snapshot.minute_bar and snapshot.minute_bar.c: current_price = snapshot.minute_bar.c
                elif snapshot.daily_bar and snapshot.daily_bar.c: current_price = snapshot.daily_bar.c
                else: continue
                
                current_volume = snapshot.daily_bar.v if snapshot.daily_bar and snapshot.daily_bar.v is not None else 0

                # Core Filters
                if not (min_price <= current_price <= max_price): continue
                if pd.isna(avg_volume) or avg_volume == 0: continue
                
                todays_change_perc = 0.0
                previous_close = snapshot.prev_daily_bar.c if snapshot.prev_daily_bar and snapshot.prev_daily_bar.c is not None and snapshot.prev_daily_bar.c > 0 else None
                if previous_close and current_price:
                    todays_change_perc = ((current_price / previous_close) - 1) * 100
                
                if abs(todays_change_perc) < min_change_perc_today: continue # Filter by min abs change
                if current_volume <= (avg_volume * volume_multiplier): continue # Filter by volume multiplier

                # --- Start Advanced Signal Calculations & Filtering ---
                signals = []
                pass_advanced_filters = True # Assume true initially

                # 1. Gap Scan
                gap_pct = 0.0
                if snapshot.daily_bar and snapshot.daily_bar.o and previous_close:
                    gap_pct = ((snapshot.daily_bar.o / previous_close) - 1) * 100
                if enable_gap_scan:
                    if not ((gap_pct >= min_gap_up_perc) or (gap_pct <= min_gap_down_perc)): # OR condition
                        pass_advanced_filters = False
                if gap_pct >= min_gap_up_perc : signals.append(f"⬆️GapUp {gap_pct:.1f}%")
                elif gap_pct <= min_gap_down_perc : signals.append(f"⬇️GapDown {gap_pct:.1f}%")


                # Breakout (already in your code, just integrate into signals)
                is_breakout = False
                if previous_close and snapshot.prev_daily_bar and snapshot.prev_daily_bar.h:
                    if current_price > snapshot.prev_daily_bar.h:
                        is_breakout = True
                        signals.append("🚀Breakout")
                
                # 2. VWAP (Approximate)
                vwap_approx = None
                if snapshot.minute_bar and snapshot.minute_bar.h and snapshot.minute_bar.l and snapshot.minute_bar.c:
                    vwap_approx = (snapshot.minute_bar.h + snapshot.minute_bar.l + snapshot.minute_bar.c) / 3
                if vwap_approx:
                    if current_price > vwap_approx: signals.append("📈>VWAP")
                    else: signals.append("📉<VWAP")
                if enable_vwap_scan:
                    if vwap_approx is None:
                        pass_advanced_filters = False
                    elif current_price > vwap_approx:
                        pass_advanced_filters = False  # Fail if NOT < VWAP (we're scanning for breakdown)



                # 3. Near Breakout
                if snapshot.prev_daily_bar and snapshot.prev_daily_bar.h and not is_breakout: # only if not already a breakout
                    proximity_to_high = ((snapshot.prev_daily_bar.h - current_price) / snapshot.prev_daily_bar.h) * 100
                    if 0 <= proximity_to_high < near_breakout_proximity_perc: # current price is just below prev high
                        signals.append(f"🟡NearBO ({proximity_to_high:.1f}% below)")
                    if enable_near_breakout_scan and not (0 <= proximity_to_high < near_breakout_proximity_perc):
                         pass_advanced_filters = False


                # 4. High Volume Sell-off
                if todays_change_perc < 0 and current_volume > (avg_volume * volume_multiplier): # Using main vol_multiplier
                    signals.append("📉HV Selloff")
                if enable_selloff_scan and not (todays_change_perc < 0 and current_volume > (avg_volume * volume_multiplier)):
                    pass_advanced_filters = False


                # 5. Consolidation Break (N-day Range)
                # Use .iloc[-2] to get the high/low of the period *before* today's potential breakout
                prev_consol_high = hist_df_full[f'{consolidation_period_days}_day_high'].iloc[-2] if len(hist_df_full) > consolidation_period_days else None
                prev_consol_low = hist_df_full[f'{consolidation_period_days}_day_low'].iloc[-2] if len(hist_df_full) > consolidation_period_days else None
                
                is_consol_break_high = False
                is_consol_break_low = False
                if prev_consol_high and current_price > prev_consol_high:
                    signals.append(f"🟢{consolidation_period_days}D BreakH")
                    is_consol_break_high = True
                if prev_consol_low and current_price < prev_consol_low:
                    signals.append(f"🔴{consolidation_period_days}D BreakL")
                    is_consol_break_low = True
                if enable_consol_break_scan and not (is_consol_break_high or is_consol_break_low):
                    pass_advanced_filters = False


                # 6. Volatility Spike (ATR)
                # Use .iloc[-1] for ATR as it's calculated on historical data up to yesterday
                atr_val = hist_df_full[f'atr_{atr_period_days}'].iloc[-1] if f'atr_{atr_period_days}' in hist_df_full.columns and not hist_df_full[f'atr_{atr_period_days}'].empty else None
                daily_range = 0
                if snapshot.daily_bar and snapshot.daily_bar.h and snapshot.daily_bar.l:
                    daily_range = snapshot.daily_bar.h - snapshot.daily_bar.l
                
                is_vol_spike = False
                if atr_val and daily_range > (atr_val * volatility_spike_multiplier):
                    signals.append(f"⚡VolSpike (R:{daily_range:.2f} > ATR:{atr_val:.2f}x{volatility_spike_multiplier})")
                    is_vol_spike = True
                if enable_volatility_spike_scan and not is_vol_spike:
                    pass_advanced_filters = False
                

                # 7. Float Rotation (Proxy using shares_outstanding)
                shares_outstanding = None
                asset_details = None
                if symbol not in asset_details_cache: # Fetch only if not cached for this run
                    try: asset_details_cache[symbol] = api.get_asset(symbol)
                    except Exception: asset_details_cache[symbol] = None
                asset_details = asset_details_cache[symbol]

                if asset_details and hasattr(asset_details, 'shares_outstanding') and asset_details.shares_outstanding:
                    shares_outstanding = asset_details.shares_outstanding
                
                float_rotation = 0.0
                if shares_outstanding and shares_outstanding > 0:
                    float_rotation = current_volume / shares_outstanding
                
                is_high_float_rot = False
                if float_rotation >= min_float_rotation:
                    signals.append(f"💎FloatRot {float_rotation:.2f}x")
                    is_high_float_rot = True
                if enable_float_rotation_scan and not is_high_float_rot:
                    pass_advanced_filters = False

                # (Placeholder for Earnings Scan)
                # if symbol in earnings_today_list: signals.append("🗓️Earnings")
                # if enable_earnings_scan and not (symbol in earnings_today_list): pass_advanced_filters = False

                if not pass_advanced_filters: # If any enabled advanced filter was not met
                    continue

                # --- End Advanced Signal Calculations ---

                volume_ratio = current_volume / avg_volume if avg_volume > 0 else float('inf')
                market_cap_display = "N/A"
                if asset_details and hasattr(asset_details, 'market_cap') and asset_details.market_cap:
                    raw_market_cap = asset_details.market_cap
                    if isinstance(raw_market_cap, (int, float)):
                        if raw_market_cap >= 1_000_000_000: market_cap_display = f"${raw_market_cap / 1_000_000_000:.2f}B"
                        elif raw_market_cap >= 1_000_000: market_cap_display = f"${raw_market_cap / 1_000_000:.2f}M"
                        elif raw_market_cap > 0: market_cap_display = f"${raw_market_cap / 1000:.2f}K"

                results_list.append({
                    "Symbol": symbol,
                    "Signals": ", ".join(signals) if signals else " - ",
                    "Current Price Num": current_price, "Current Volume Num": current_volume,
                    "Avg Vol Num": avg_volume, "Volume Ratio Num": volume_ratio,
                    "Change % Num": todays_change_perc, "Market Cap Str": market_cap_display,
                    "Float Rotation Num": float_rotation # For sorting
                })
        
        if results_list:
            results_df_numeric = pd.DataFrame(results_list)
            sort_column_map = {
                "Volume Ratio": "Volume Ratio Num", "Change %": "Change % Num",
                "Current Price": "Current Price Num", "Float Rotation": "Float Rotation Num"
            }
            sort_column_numeric = sort_column_map.get(sort_by, "Volume Ratio Num")
            results_df_sorted = results_df_numeric.sort_values(by=sort_column_numeric, ascending=False)

            results_df_display = results_df_sorted.copy()
            results_df_display['Price'] = results_df_display['Current Price Num'].map('${:,.2f}'.format)
            results_df_display['Volume'] = results_df_display['Current Volume Num'].map('{:,.0f}'.format)
            results_df_display[f"AvgVol({lookback_days_avg_vol}d)"] = results_df_display["Avg Vol Num"].map('{:,.0f}'.format)
            results_df_display['VolRatio'] = results_df_display['Volume Ratio Num'].map('{:.2f}x'.format)
            results_df_display['Change%'] = results_df_display['Change % Num'].map('{:.2f}%'.format)
            results_df_display['MarketCap'] = results_df_display["Market Cap Str"]
            results_df_display['FloatRot'] = results_df_display["Float Rotation Num"].map('{:.2f}x'.format)


            st.dataframe(
                results_df_display[[
                    "Symbol", "Signals", "Price", "Volume", f"AvgVol({lookback_days_avg_vol}d)",
                    "VolRatio", "Change%", "MarketCap", "FloatRot"
                ]], 
                use_container_width=True, hide_index=True,
                column_config={ # Optional: define widths or specific configs
                    "Symbol": st.column_config.TextColumn(width="small"),
                    "Signals": st.column_config.TextColumn(width="large"),
                    "Price": st.column_config.TextColumn(width="small"),
                }
            )
            st.caption(f"Displaying {len(results_df_display)} stocks meeting all criteria.")
            st.caption("Signal Emojis: 🚀Breakout, ⬆️GapUp, ⬇️GapDown, 📈>VWAP, 📉<VWAP, 🟡NearBO, 📉HV Selloff, 🟢ND BreakH, 🔴ND BreakL, ⚡VolSpike, 💎FloatRot")
        else:
            st.info("No stocks currently meet all your selected criteria after live data check.")
        
        st.session_state.run_scan = False
    else:
        st.info("Adjust scanner settings in the sidebar and click 'Run Scanner'.")
else:
    st.error("API not initialized.")
# --- Smart Presets Function ---
def load_presets(preset):
    if preset == "🔍 Momentum Hunt":
        return {
            "volume_multiplier": 2.0,
            "min_price": 1.0,
            "max_price": 30.0,
            "min_avg_volume": 100_000,
            "min_change_perc_today": 2.0,
            "enable_gap_scan": False,
            "enable_vwap_scan": True,
            "enable_near_breakout_scan": True,
            "enable_consol_break_scan": False,
            "enable_volatility_spike_scan": False,
            "enable_float_rotation_scan": True,
        }
    elif preset == "🚀 Pre-Breakout":
        return {
            "volume_multiplier": 1.8,
            "min_price": 1.0,
            "max_price": 50.0,
            "min_avg_volume": 80_000,
            "min_change_perc_today": 1.5,
            "enable_gap_scan": True,
            "enable_vwap_scan": True,
            "enable_near_breakout_scan": True,
            "enable_consol_break_scan": True,
            "enable_volatility_spike_scan": False,
            "enable_float_rotation_scan": False,
        }
    elif preset == "⚡ Vol Spike Only":
        return {
            "volume_multiplier": 2.0,
            "min_price": 1.0,
            "max_price": 100.0,
            "min_avg_volume": 100_000,
            "min_change_perc_today": 1.0,
            "enable_gap_scan": False,
            "enable_vwap_scan": False,
            "enable_near_breakout_scan": False,
            "enable_consol_break_scan": False,
            "enable_volatility_spike_scan": True,
            "enable_float_rotation_scan": False,
        }
    elif preset == "💎 Float Rotator":
        return {
            "volume_multiplier": 2.5,
            "min_price": 1.0,
            "max_price": 20.0,
            "min_avg_volume": 50_000,
            "min_change_perc_today": 2.0,
            "enable_gap_scan": False,
            "enable_vwap_scan": False,
            "enable_near_breakout_scan": False,
            "enable_consol_break_scan": False,
            "enable_volatility_spike_scan": False,
            "enable_float_rotation_scan": True,
        }
    elif preset == "🧪 All-In Strict":
        return {
            "volume_multiplier": 3.0,
            "min_price": 1.0,
            "max_price": 50.0,
            "min_avg_volume": 150_000,
            "min_change_perc_today": 3.0,
            "enable_gap_scan": True,
            "enable_vwap_scan": True,
            "enable_near_breakout_scan": True,
            "enable_consol_break_scan": True,
            "enable_volatility_spike_scan": True,
            "enable_float_rotation_scan": True,
        }
    return {}

# --- Preset Selector UI ---
preset = st.sidebar.selectbox("📌 Load Preset:", ["None", "🔍 Momentum Hunt", "🚀 Pre-Breakout", "⚡ Vol Spike Only", "💎 Float Rotator", "🧪 All-In Strict"])

if preset != "None":
    settings = load_presets(preset)
    for key, val in settings.items():
        st.session_state[key] = val
    st.sidebar.success(f"Preset '{preset}' loaded.")
st.sidebar.markdown("---")
st.sidebar.markdown("Data by Alpaca. Not financial advice.")
st.markdown("---")
st.markdown(
    """<div style="text-align: center; margin-top: 20px; margin-bottom: 20px;">
        <p style="font-size:18px; font-weight: bold;">Enjoying this tool? Consider supporting its development!</p>
        <a href="https://paypal.me/niveyal" target="_blank" style="background-color: #FFC439; color: #000000; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
           ☕ Buy me a coffee</a></div>""", unsafe_allow_html=True)
    # Paste all the code from your "Unusual Volume Scanner"
    # starting from st.title("📈 Alpaca Advanced Stock Scanner") ...

with tab2:
    import streamlit as st
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
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import finnhub
finnhub_client = finnhub.Client(api_key=st.secrets["FINNHUB_API_KEY"])

def get_finnhub_price_data(symbol: str) -> Dict[str, float]:
    try:
        quote = finnhub_client.quote(symbol)
        last_price = quote.get("c")  # current
        prev_close = quote.get("pc")  # previous close

        if last_price is None or prev_close is None:
            return {"last_price": None, "prev_close": None, "pct_change": None}

        pct_change = ((last_price - prev_close) / prev_close) * 100 if prev_close != 0 else None
        return {
            "last_price": round(last_price, 2),
            "prev_close": round(prev_close, 2),
            "pct_change": round(pct_change, 2) if pct_change is not None else None
        }
    except Exception as e:
        logging.warning(f"Finnhub fallback failed for {symbol}: {e}")
        return {"last_price": None, "prev_close": None, "pct_change": None}

components.html("""
<script>
document.addEventListener("DOMContentLoaded", function() {
  const textarea = parent.document.querySelector('textarea[data-testid="stTextArea"]');
  const scanButton = parent.document.querySelector('button[aria-label="🚀 Scan Selected Strategies"]');

  if (textarea && scanButton) {
    textarea.addEventListener("keydown", function(e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();  // כדי שלא ירד שורה
        scanButton.click();
      }
    });
  }
});
</script>
""", height=0)

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
    # ✅ Only run once on load using session state
if "run_top_volume_fetch" not in st.session_state:
    st.session_state.run_top_volume_fetch = True

# 🕓 Fetch once on app start
if "run_top_volume_fetch" not in st.session_state:
    st.session_state.run_top_volume_fetch = True

if st.session_state.run_top_volume_fetch:
    price_change_data = {}
    with st.spinner("📡 Fetching real-time prices from Alpaca (fallback: Finnhub)..."):
        for t in df_tv["Symbol"]:
            price_data = get_latest_price_and_change(alpaca, t)
            if price_data.get("last_price") is None or price_data.get("prev_close") is None:
                price_data.update(get_finnhub_price_data(t))
            price_change_data[t] = price_data

    df_tv["Last Price"] = df_tv["Symbol"].apply(lambda t: price_change_data.get(t, {}).get("last_price", "N/A"))
    df_tv["Prev Close"] = df_tv["Symbol"].apply(lambda t: price_change_data.get(t, {}).get("prev_close", "N/A"))

    def calculate_change(row):
        try:
            last = float(row["Last Price"])
            prev = float(row["Prev Close"])
            if prev == 0:
                return "-"
            change_pct = ((last - prev) / prev) * 100
            return f"🔻 {change_pct:.2f}%" if change_pct < 0 else f"🟢 {change_pct:.2f}%"
        except:
            return "-"
    df_tv["% Change"] = df_tv.apply(calculate_change, axis=1)

    # ✅ Prevent re-fetch
    st.session_state.run_top_volume_fetch = False

# ✅ Always display the table after fetch
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(df_tv.to_html(escape=False, index=False), unsafe_allow_html=True)


    # ⛔ Prevent it from re-fetching on every rerun

st.subheader("🔼 Top Gainers / 🔽 Top Losers")

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🔼 Top Gainers")
    gainers = fetch_market_movers("stock_market/gainers")
    if not gainers.empty:
        st.dataframe(gainers, use_container_width=True)
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
        "Momentum Trading", "MACD Bullish ADX", "ADX Rising MFI Surge", "TRIX OBV", "Vortex ADX",
        "MACD Bearish Cross", "Gap and Go"  # Added
    ],
    "Mean Reversion": [
        "Mean Reversion (RSI)", "Scalping (Bollinger Bands)", "MACD RSI Oversold", "CCI Reversion",
        "Bollinger Bounce Volume", "MFI Bollinger",
        "VWAP Breakdown Volume", "Liquidity Sweep Reversal"  # Added
    ],
    "Trend Following": [
        "Trend Following (EMA/ADX)", "Golden Cross RSI", "ADX Heikin Ashi", "SuperTrend RSI Pullback",
        "Ichimoku Basic Combo", "Ichimoku Multi-Line", "EMA SAR",
        "SuperTrend Flip"  # Added
    ],
    "Breakout": [
        "Breakout Trading", "Pivot Point (Intraday S/R)",
        "Opening Range Breakout"  # Added
    ],
    "Volatility": [
        "Bollinger Upper Break Volume", "EMA Ribbon Expansion CMF"
    ],
    "Volume-Based": [
        "News Trading (Volatility Spike)", "TEMA Cross Volume", "Bollinger Bounce Volume",
        "Hammer Volume", "ADX Rising MFI Surge", "MFI Bollinger", "TRIX OBV", "VWAP RSI",
        "VWAP Aroon", "EMA Ribbon Expansion CMF",
        "VWAP Breakdown Volume"  # Added
    ],
    "Oscillator-Based": [
        "PSAR RSI", "RSI EMA Crossover", "CCI Bollinger", "Awesome Oscillator Divergence MACD",
        "Heikin Ashi CMO", "MFI Bollinger",
        "Bearish RSI Divergence", "MACD Bearish Cross"  # Added
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
        "Ichimoku Basic Combo", "Ichimoku Multi-Line", "EMA SAR", "MFI Bollinger", "Hammer Volume",
        "Bearish RSI Divergence", "Liquidity Sweep Reversal"  # Added
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
st.sidebar.markdown("---")
st.sidebar.markdown("#### 3. Backtest Strategies")



if 'fmp_tickers' not in st.session_state: st.session_state.fmp_tickers = []
if 'fmp_last_refresh' not in st.session_state: st.session_state.fmp_last_refresh = None


scan_button_html = """
<script>
document.addEventListener("DOMContentLoaded", function() {
  const textarea = parent.document.querySelector('textarea[data-testid="stTextArea"]');
  if (textarea) {
    textarea.addEventListener("keydown", function(e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();  // לא יורד שורה
        const btn = parent.document.querySelector('button[aria-label="🚀 Scan Selected Strategies"]');
        if (btn) btn.click();
      }
    });
  }
});
</script>
"""
st.components.v1.html(scan_button_html, height=0)




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
    key="scan_button_main",
    use_container_width=True
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
