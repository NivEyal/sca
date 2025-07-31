"""
Configuration file for the Trading Strategy Scanner
"""

# Default tickers for quick start
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", 
    "NVDA", "META", "NFLX", "AMD", "INTC"
]

# Strategy categories for organized selection
STRATEGY_CATEGORIES = {
    "🎯 Momentum": [
        "Momentum Trading",
        "MACD Bullish ADX", 
        "ADX Rising MFI Surge",
        "TRIX OBV",
        "Vortex ADX"
    ],
    "📈 Trend Following": [
        "Trend Following (EMA/ADX)",
        "Golden Cross RSI",
        "SuperTrend RSI Pullback",
        "ADX Heikin Ashi",
        "Ichimoku Basic Combo",
        "Ichimoku Multi-Line",
        "EMA SAR"
    ],
    "🔄 Mean Reversion": [
        "Mean Reversion (RSI)",
        "Scalping (Bollinger Bands)",
        "MACD RSI Oversold",
        "CCI Reversion",
        "Keltner RSI Oversold",
        "Keltner MFI Oversold",
        "Bollinger Bounce Volume",
        "MFI Bollinger"
    ],
    "💥 Breakout & Patterns": [
        "Breakout Trading",
        "Opening Range Breakout",
        "Gap and Go",
        "Fractal Breakout RSI",
        "Pivot Point (Intraday S/R)",
        "Liquidity Sweep Reversal"
    ],
    "📊 Volume & Volatility": [
        "VWAP RSI",
        "News Trading (Volatility Spike)",
        "TEMA Cross Volume",
        "VWAP Aroon",
        "VWAP Breakdown Volume",
        "Bollinger Upper Break Volume"
    ],
    "🔧 Advanced Oscillators": [
        "PSAR RSI",
        "RSI EMA Crossover",
        "CCI Bollinger",
        "TSI Resistance Break",
        "Awesome Oscillator Divergence MACD",
        "Heikin Ashi CMO"
    ],
    "🎪 Pattern Recognition": [
        "Hammer on Keltner Volume",
        "Hammer Volume",
        "RSI Bullish Divergence Candlestick",
        "Ross Hook Momentum",
        "Bearish RSI Divergence",
        "SuperTrend Flip"
    ],
    "🔀 Hybrid Strategies": [
        "Reversal (RSI/MACD)",
        "Pullback Trading (EMA)",
        "End-of-Day (Intraday Consolidation)",
        "EMA Ribbon MACD",
        "Chandelier Exit MACD",
        "Double MA Pullback",
        "RSI Range Breakout BB",
        "Keltner Middle RSI Divergence",
        "EMA Ribbon Expansion CMF",
        "MACD Bearish Cross"
    ]
}

# Timeframe options
TIMEFRAMES = {
    "1 Minute": "1Min",
    "5 Minutes": "5Min", 
    "15 Minutes": "15Min",
    "30 Minutes": "30Min",
    "1 Hour": "1Hour",
    "4 Hours": "4Hour",
    "1 Day": "1Day"
}

# Data limits for different timeframes
DATA_LIMITS = {
    "1Min": 200,
    "5Min": 300,
    "15Min": 400,
    "30Min": 500,
    "1Hour": 500,
    "4Hour": 300,
    "1Day": 200
}

# Color scheme
COLORS = {
    "primary": "#667eea",
    "secondary": "#764ba2", 
    "success": "#28a745",
    "danger": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8",
    "light": "#f8f9fa",
    "dark": "#343a40"
}

# Chart settings
CHART_CONFIG = {
    "height": 400,
    "show_volume": True,
    "show_signals": True,
    "candlestick_colors": {
        "increasing": "#26a69a",
        "decreasing": "#ef5350"
    }
}