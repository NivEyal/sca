"""
Simplified strategy functions for the trading scanner
"""
import pandas as pd
import numpy as np

def strategy_momentum(df, rsi_period=14, volume_multiplier=2.0, rsi_level=70):
    """Simple momentum strategy"""
    try:
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume condition
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        volume_condition = df['volume'] > (df['volume_ma'] * volume_multiplier)
        
        # Entry signal
        df['Momentum_Trading_Entry'] = (df['rsi'] > rsi_level) & volume_condition
        
        return df
    except Exception as e:
        print(f"Error in momentum strategy: {e}")
        df['Momentum_Trading_Entry'] = False
        return df

def strategy_mean_reversion(df, rsi_period=14, rsi_upper=70, rsi_lower=30):
    """Simple mean reversion strategy"""
    try:
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Entry signals
        df['Mean_Reversion_RSI_Entry_Buy'] = df['rsi'] < rsi_lower
        df['Mean_Reversion_RSI_Entry_Sell'] = df['rsi'] > rsi_upper
        
        return df
    except Exception as e:
        print(f"Error in mean reversion strategy: {e}")
        df['Mean_Reversion_RSI_Entry_Buy'] = False
        df['Mean_Reversion_RSI_Entry_Sell'] = False
        return df

def strategy_breakout(df, ema_period=20, volume_multiplier=1.5):
    """Simple breakout strategy"""
    try:
        # Calculate EMA
        df['ema'] = df['close'].ewm(span=ema_period).mean()
        
        # Volume condition
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        volume_condition = df['volume'] > (df['volume_ma'] * volume_multiplier)
        
        # Breakout condition
        breakout_condition = df['close'] > df['ema']
        
        # Entry signal
        df['Breakout_Trading_Entry'] = breakout_condition & volume_condition
        
        return df
    except Exception as e:
        print(f"Error in breakout strategy: {e}")
        df['Breakout_Trading_Entry'] = False
        return df

def strategy_scalping(df, bb_period=20, bb_std=2.0):
    """Simple Bollinger Bands scalping strategy"""
    try:
        # Calculate Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
        bb_std_dev = df['close'].rolling(window=bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std_dev * bb_std)
        df['bb_lower'] = df['bb_middle'] - (bb_std_dev * bb_std)
        
        # Entry signals
        df['Scalping_Bollinger_Bands_Entry_Buy'] = df['close'] < df['bb_lower']
        df['Scalping_Bollinger_Bands_Entry_Sell'] = df['close'] > df['bb_upper']
        
        return df
    except Exception as e:
        print(f"Error in scalping strategy: {e}")
        df['Scalping_Bollinger_Bands_Entry_Buy'] = False
        df['Scalping_Bollinger_Bands_Entry_Sell'] = False
        return df

def strategy_trend_following(df, ema_short=9, ema_long=21, adx_period=14, adx_threshold=25):
    """Simple trend following strategy"""
    try:
        # Calculate EMAs
        df['ema_short'] = df['close'].ewm(span=ema_short).mean()
        df['ema_long'] = df['close'].ewm(span=ema_long).mean()
        
        # Simple ADX approximation
        df['high_low'] = df['high'] - df['low']
        df['adx_approx'] = df['high_low'].rolling(window=adx_period).mean()
        
        # Trend conditions
        uptrend = df['ema_short'] > df['ema_long']
        strong_trend = df['adx_approx'] > df['adx_approx'].rolling(window=adx_period).mean()
        
        # Entry signal
        df['Trend_Following_EMA_ADX_Entry'] = uptrend & strong_trend
        
        return df
    except Exception as e:
        print(f"Error in trend following strategy: {e}")
        df['Trend_Following_EMA_ADX_Entry'] = False
        return df

# Add more simplified strategies as needed
def strategy_news(df, volume_multiplier=2.5, price_change_threshold=0.02):
    """Simple volatility spike strategy"""
    try:
        # Price change
        df['price_change'] = df['close'].pct_change().abs()
        
        # Volume condition
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        volume_spike = df['volume'] > (df['volume_ma'] * volume_multiplier)
        
        # Volatility condition
        volatility_spike = df['price_change'] > price_change_threshold
        
        # Entry signal
        df['News_Trading_Volatility_Spike_Entry'] = volume_spike & volatility_spike
        
        return df
    except Exception as e:
        print(f"Error in news trading strategy: {e}")
        df['News_Trading_Volatility_Spike_Entry'] = False
        return df