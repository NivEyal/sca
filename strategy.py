# strategy.py
import pandas as pd
import numpy as np
try:
    import strategy_functions as sf # Try to import full strategy functions
except ImportError:
    import simple_strategy_functions as sf # Fallback to simplified functions
    print("Using simplified strategy functions")
from typing import Dict, List

# This STRATEGY_MAP is crucial.
# Keys: User-friendly display names (MUST MATCH app.py's STRATEGY_CATEGORIES items)
# Values: Actual function objects from strategy_functions.py (sf.actual_function_name)
STRATEGY_MAP = {
    # Momentum
    "Momentum Trading": sf.strategy_momentum,
    # Mean Reversion
    "Mean Reversion (RSI)": sf.strategy_mean_reversion,
    "Scalping (Bollinger Bands)": sf.strategy_scalping,
    # Trend Following
    "Trend Following (EMA/ADX)": sf.strategy_trend_following,
    # Breakout
    "Breakout Trading": sf.strategy_breakout,
    # Volume-Based
    "News Trading (Volatility Spike)": sf.strategy_news,
}

# This dictionary should contain default parameters for strategies that need them.
# Keys are the *display names*. Values are dicts of params for the corresponding strategy function.
# (Copied from your original strategy.py)
STRATEGY_DEFAULT_PARAMS = {
    "Bearish RSI Divergence": {"rsi_period": 14, "div_lookback": 14},
    "MACD Bearish Cross": {"fast": 12, "slow": 26, "signal": 9, "volume_multiplier": 1.2},
    "VWAP Breakdown Volume": {"rsi_period": 14, "volume_multiplier": 1.5},
    "SuperTrend Flip": {"atr_length": 10, "factor": 3.0},
    "Opening Range Breakout": {"range_minutes": 15, "volume_multiplier": 1.5},
    "Gap and Go": {"gap_threshold": 0.02, "rsi_period": 14, "volume_multiplier": 1.5},
    "Liquidity Sweep Reversal": {"lookback": 20, "rsi_period": 14},
    "Momentum Trading": {"rsi_period": 14, "volume_multiplier": 2.0, "rsi_level": 70},
    "Scalping (Bollinger Bands)": {"bb_period": 20, "bb_std": 2.0},
    "Breakout Trading": {"ema_period": 20, "volume_multiplier": 1.5},
    "Mean Reversion (RSI)": {"rsi_period": 14, "rsi_upper": 70, "rsi_lower": 30},
    "News Trading (Volatility Spike)": {"volume_multiplier": 2.5, "price_change_threshold": 0.02},
    "Trend Following (EMA/ADX)": {"ema_short": 9, "ema_long": 21, "adx_period": 14, "adx_threshold": 25},
    "Pivot Point (Intraday S/R)": {"pivot_lookback": 20, "exit_ema_period": 20}, # Adjusted to match your version
    "Reversal (RSI/MACD)": {"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
    "Pullback Trading (EMA)": {"ema_short": 9, "ema_long": 21},
    "End-of-Day (Intraday Consolidation)": {"ema_period": 20, "volume_multiplier": 1.5, "price_stability_pct": 0.002},
    "Golden Cross RSI": {"short_ema": 50, "long_ema": 200, "rsi_period": 14, "rsi_level": 50},
    "MACD Bullish ADX": {"fast": 12, "slow": 26, "signal": 9, "adx_period": 14, "adx_level": 25},
    "MACD RSI Oversold": {"fast": 12, "slow": 26, "signal": 9, "rsi_period": 14, "rsi_oversold": 30},
    "ADX Heikin Ashi": {"adx_period": 14, "adx_level": 25},
    "PSAR RSI": {"initial_af": 0.02, "max_af": 0.2, "rsi_period": 14, "rsi_level": 50},
    "VWAP RSI": {"rsi_period": 14, "rsi_level": 50},
    "EMA Ribbon MACD": {"ema_lengths": [8, 13, 21, 34, 55], "macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
    "TRIX OBV": {"trix_period": 15, "trix_signal": 9},
    "VWAP Aroon": {"aroon_period": 14, "aroon_level": 70},}
    for symbol, df in data_dict.items():
        # Validate essential columns exist
        if not all(col in df.columns for col in required_cols):
            print(f"Skipping {symbol}: missing required columns.")
            continue
        df[required_cols] = df[required_cols].apply(pd.to_numeric, errors='coerce')
        if df[required_cols].isnull().any().any():
            print(f"Skipping {symbol}: NaN values found in required columns after conversion.")
            continue
    "Vortex ADX": {"vortex_period": 14, "adx_period": 14, "adx_trend_level": 25},
        for strategy_name in strategy_names:
            func = STRATEGY_MAP.get(strategy_name)
            params = STRATEGY_DEFAULT_PARAMS.get(strategy_name, {})
            if func:
                try:
                    df_with_signals = func(df.copy(), **params)
                    entry_cols = [
                        col for col in df_with_signals.columns
                        if "_Entry" in col and df_with_signals[col].any()
                    ]
                    if entry_cols:
                        results.append({
                            "symbol": symbol,
                            "strategy": strategy_name,
                            "entry_signals": entry_cols,
                            "latest_row": df_with_signals.iloc[-1].to_dict()
                        })
                except Exception as e:
                    print(f"Error running strategy '{strategy_name}' on {symbol}: {e}")
            else:
                print(f"Strategy '{strategy_name}' not found in STRATEGY_MAP.")
    return results



