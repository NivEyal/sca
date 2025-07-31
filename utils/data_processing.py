import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def validate_market_data(market_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Validate and clean market data"""
    cleaned_data = {}
    
    for symbol, df in market_data.items():
        if df.empty:
            logger.warning(f"Empty dataframe for {symbol}")
            continue
        
        # Check required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            logger.warning(f"Missing columns for {symbol}: {missing_cols}")
            continue
        
        # Convert to numeric and handle NaN values
        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove rows with NaN values
        df_clean = df.dropna(subset=required_cols)
        
        if df_clean.empty:
            logger.warning(f"No valid data after cleaning for {symbol}")
            continue
        
        # Ensure proper datetime index
        if not isinstance(df_clean.index, pd.DatetimeIndex):
            try:
                df_clean.index = pd.to_datetime(df_clean.index)
            except Exception as e:
                logger.error(f"Failed to convert index to datetime for {symbol}: {e}")
                continue
        
        # Sort by index
        df_clean = df_clean.sort_index()
        
        cleaned_data[symbol] = df_clean
    
    return cleaned_data

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add common technical indicators to dataframe"""
    if df.empty:
        return df
    
    df = df.copy()
    
    try:
        # Simple Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # Exponential Moving Averages
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price change
        df['price_change'] = df['close'].pct_change()
        df['price_change_abs'] = df['close'].diff()
        
    except Exception as e:
        logger.error(f"Error calculating technical indicators: {e}")
    
    return df

def detect_patterns(df: pd.DataFrame) -> Dict[str, bool]:
    """Detect common chart patterns"""
    if df.empty or len(df) < 20:
        return {}
    
    patterns = {}
    
    try:
        # Golden Cross
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            patterns['golden_cross'] = (
                df['sma_20'].iloc[-1] > df['sma_50'].iloc[-1] and
                df['sma_20'].iloc[-2] <= df['sma_50'].iloc[-2]
            )
        
        # Death Cross
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            patterns['death_cross'] = (
                df['sma_20'].iloc[-1] < df['sma_50'].iloc[-1] and
                df['sma_20'].iloc[-2] >= df['sma_50'].iloc[-2]
            )
        
        # Breakout above Bollinger Upper Band
        if 'bb_upper' in df.columns:
            patterns['bb_breakout_up'] = df['close'].iloc[-1] > df['bb_upper'].iloc[-1]
        
        # Breakdown below Bollinger Lower Band
        if 'bb_lower' in df.columns:
            patterns['bb_breakdown'] = df['close'].iloc[-1] < df['bb_lower'].iloc[-1]
        
        # High Volume
        if 'volume_ratio' in df.columns:
            patterns['high_volume'] = df['volume_ratio'].iloc[-1] > 2.0
        
        # RSI Overbought/Oversold
        if 'rsi' in df.columns:
            patterns['rsi_overbought'] = df['rsi'].iloc[-1] > 70
            patterns['rsi_oversold'] = df['rsi'].iloc[-1] < 30
        
        # MACD Bullish/Bearish
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            patterns['macd_bullish'] = (
                df['macd'].iloc[-1] > df['macd_signal'].iloc[-1] and
                df['macd'].iloc[-2] <= df['macd_signal'].iloc[-2]
            )
            patterns['macd_bearish'] = (
                df['macd'].iloc[-1] < df['macd_signal'].iloc[-1] and
                df['macd'].iloc[-2] >= df['macd_signal'].iloc[-2]
            )
    
    except Exception as e:
        logger.error(f"Error detecting patterns: {e}")
    
    return patterns

def calculate_volatility(df: pd.DataFrame, window: int = 20) -> float:
    """Calculate price volatility"""
    if df.empty or len(df) < window:
        return 0.0
    
    try:
        returns = df['close'].pct_change().dropna()
        volatility = returns.rolling(window=window).std().iloc[-1] * np.sqrt(252)  # Annualized
        return volatility if not np.isnan(volatility) else 0.0
    except Exception as e:
        logger.error(f"Error calculating volatility: {e}")
        return 0.0

def get_support_resistance_levels(df: pd.DataFrame, window: int = 20) -> Tuple[float, float]:
    """Calculate support and resistance levels"""
    if df.empty or len(df) < window:
        return 0.0, 0.0
    
    try:
        recent_data = df.tail(window)
        support = recent_data['low'].min()
        resistance = recent_data['high'].max()
        return support, resistance
    except Exception as e:
        logger.error(f"Error calculating support/resistance: {e}")
        return 0.0, 0.0

def filter_signals_by_confidence(strategy_results: List[Dict], min_confidence: float = 0.7) -> List[Dict]:
    """Filter strategy results by confidence level"""
    # This is a placeholder - you would implement actual confidence scoring
    # based on multiple factors like volume, volatility, pattern strength, etc.
    
    filtered_results = []
    
    for result in strategy_results:
        # Simple confidence scoring based on number of entry signals
        entry_signals = result.get('entry_signals', [])
        confidence = min(len(entry_signals) / 3.0, 1.0)  # Max confidence at 3+ signals
        
        if confidence >= min_confidence:
            result['confidence'] = confidence
            filtered_results.append(result)
    
    return filtered_results

def aggregate_signals_by_symbol(strategy_results: List[Dict]) -> Dict[str, Dict]:
    """Aggregate all signals for each symbol"""
    symbol_aggregates = {}
    
    for result in strategy_results:
        symbol = result['symbol']
        strategy = result['strategy']
        entry_signals = result.get('entry_signals', [])
        
        if symbol not in symbol_aggregates:
            symbol_aggregates[symbol] = {
                'strategies': [],
                'buy_signals': 0,
                'sell_signals': 0,
                'total_signals': 0,
                'signal_strength': 0
            }
        
        symbol_aggregates[symbol]['strategies'].append(strategy)
        symbol_aggregates[symbol]['total_signals'] += len(entry_signals)
        
        for signal in entry_signals:
            if 'Buy' in signal:
                symbol_aggregates[symbol]['buy_signals'] += 1
            elif 'Sell' in signal:
                symbol_aggregates[symbol]['sell_signals'] += 1
        
        # Calculate signal strength (more buy signals = higher strength)
        buy_ratio = symbol_aggregates[symbol]['buy_signals'] / max(symbol_aggregates[symbol]['total_signals'], 1)
        symbol_aggregates[symbol]['signal_strength'] = buy_ratio
    
    return symbol_aggregates