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
    max_slider_val = min(total_available_assets, 7000)
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
