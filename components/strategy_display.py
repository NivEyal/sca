import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Any
import numpy as np

def create_strategy_summary_chart(strategy_results: List[Dict]) -> go.Figure:
    """Create a summary chart of strategy performance"""
    if not strategy_results:
        return go.Figure()
    
    # Count signals by strategy
    strategy_counts = {}
    for result in strategy_results:
        strategy = result['strategy']
        entry_signals = result.get('entry_signals', [])
        
        if strategy not in strategy_counts:
            strategy_counts[strategy] = {'buy': 0, 'sell': 0, 'total': 0}
        
        for signal in entry_signals:
            strategy_counts[strategy]['total'] += 1
            if 'Buy' in signal:
                strategy_counts[strategy]['buy'] += 1
            elif 'Sell' in signal:
                strategy_counts[strategy]['sell'] += 1
    
    if not strategy_counts:
        return go.Figure()
    
    strategies = list(strategy_counts.keys())
    buy_counts = [strategy_counts[s]['buy'] for s in strategies]
    sell_counts = [strategy_counts[s]['sell'] for s in strategies]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Buy Signals',
        x=strategies,
        y=buy_counts,
        marker_color='green',
        opacity=0.8
    ))
    
    fig.add_trace(go.Bar(
        name='Sell Signals',
        x=strategies,
        y=sell_counts,
        marker_color='red',
        opacity=0.8
    ))
    
    fig.update_layout(
        title='Strategy Signal Summary',
        xaxis_title='Strategy',
        yaxis_title='Number of Signals',
        barmode='group',
        height=400,
        xaxis_tickangle=-45
    )
    
    return fig

def create_signal_timeline(strategy_results: List[Dict], market_data: Dict[str, pd.DataFrame]) -> go.Figure:
    """Create a timeline of signals across all symbols"""
    fig = go.Figure()
    
    colors = {'buy': 'green', 'sell': 'red', 'neutral': 'gray'}
    
    for i, result in enumerate(strategy_results):
        symbol = result['symbol']
        strategy = result['strategy']
        entry_signals = result.get('entry_signals', [])
        
        if symbol not in market_data or market_data[symbol].empty:
            continue
        
        df = market_data[symbol]
        latest_time = df.index[-1]
        latest_price = df['close'].iloc[-1]
        
        for signal in entry_signals:
            color = 'green' if 'Buy' in signal else 'red' if 'Sell' in signal else 'gray'
            
            fig.add_trace(go.Scatter(
                x=[latest_time],
                y=[latest_price],
                mode='markers',
                marker=dict(
                    size=15,
                    color=color,
                    symbol='triangle-up' if 'Buy' in signal else 'triangle-down' if 'Sell' in signal else 'circle',
                    line=dict(width=2, color='white')
                ),
                name=f"{symbol} - {strategy}",
                hovertemplate=f'<b>{symbol}</b><br>' +
                             f'Strategy: {strategy}<br>' +
                             f'Signal: {signal}<br>' +
                             f'Price: ${latest_price:.2f}<br>' +
                             f'Time: {latest_time}<br>' +
                             '<extra></extra>'
            ))
    
    fig.update_layout(
        title='Signal Timeline',
        xaxis_title='Time',
        yaxis_title='Price',
        height=500,
        showlegend=True
    )
    
    return fig

def display_strategy_cards(strategy_results: List[Dict], market_data: Dict[str, pd.DataFrame]):
    """Display strategy results as cards"""
    if not strategy_results:
        st.info("No strategy signals found")
        return
    
    # Group results by symbol
    symbol_results = {}
    for result in strategy_results:
        symbol = result['symbol']
        if symbol not in symbol_results:
            symbol_results[symbol] = []
        symbol_results[symbol].append(result)
    
    # Display cards
    for symbol, results in symbol_results.items():
        with st.expander(f"📊 {symbol} Analysis", expanded=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Price chart with signals
                if symbol in market_data and not market_data[symbol].empty:
                    df = market_data[symbol]
                    
                    fig = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.1,
                        subplot_titles=('Price', 'Volume'),
                        row_width=[0.7, 0.3]
                    )
                    
                    # Candlestick chart
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df['open'],
                            high=df['high'],
                            low=df['low'],
                            close=df['close'],
                            name='Price'
                        ),
                        row=1, col=1
                    )
                    
                    # Volume bars
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df['volume'],
                            name='Volume',
                            marker_color='lightblue',
                            opacity=0.7
                        ),
                        row=2, col=1
                    )
                    
                    # Add signal markers
                    for result in results:
                        entry_signals = result.get('entry_signals', [])
                        strategy = result['strategy']
                        
                        for signal in entry_signals:
                            color = 'green' if 'Buy' in signal else 'red'
                            symbol_shape = 'triangle-up' if 'Buy' in signal else 'triangle-down'
                            
                            fig.add_trace(
                                go.Scatter(
                                    x=[df.index[-1]],
                                    y=[df['close'].iloc[-1]],
                                    mode='markers',
                                    marker=dict(
                                        size=20,
                                        color=color,
                                        symbol=symbol_shape,
                                        line=dict(width=2, color='white')
                                    ),
                                    name=f"{strategy} Signal",
                                    hovertemplate=f'<b>{strategy}</b><br>' +
                                                 f'Signal: {signal}<br>' +
                                                 '<extra></extra>'
                                ),
                                row=1, col=1
                            )
                    
                    fig.update_layout(
                        height=500,
                        showlegend=False,
                        title=f"{symbol} - Technical Analysis"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Signal summary
                st.subheader("🎯 Active Signals")
                
                for result in results:
                    strategy = result['strategy']
                    entry_signals = result.get('entry_signals', [])
                    
                    st.markdown(f"**{strategy}**")
                    
                    for signal in entry_signals:
                        if 'Buy' in signal:
                            st.success(f"🟢 BUY")
                        elif 'Sell' in signal:
                            st.error(f"🔴 SELL")
                        else:
                            st.info(f"⚪ {signal}")
                
                # Market data summary
                if symbol in market_data and not market_data[symbol].empty:
                    df = market_data[symbol]
                    latest = df.iloc[-1]
                    first = df.iloc[0]
                    
                    price_change = ((latest['close'] - first['open']) / first['open']) * 100
                    
                    st.subheader("📈 Market Data")
                    st.metric("Current Price", f"${latest['close']:.2f}", f"{price_change:.2f}%")
                    st.metric("Volume", f"{latest['volume']:,}")
                    st.metric("High", f"${latest['high']:.2f}")
                    st.metric("Low", f"${latest['low']:.2f}")

def create_performance_metrics(strategy_results: List[Dict]) -> Dict[str, Any]:
    """Calculate performance metrics for strategies"""
    if not strategy_results:
        return {}
    
    metrics = {
        'total_signals': len(strategy_results),
        'unique_symbols': len(set(r['symbol'] for r in strategy_results)),
        'unique_strategies': len(set(r['strategy'] for r in strategy_results)),
        'buy_signals': 0,
        'sell_signals': 0,
        'strategy_breakdown': {}
    }
    
    for result in strategy_results:
        strategy = result['strategy']
        entry_signals = result.get('entry_signals', [])
        
        if strategy not in metrics['strategy_breakdown']:
            metrics['strategy_breakdown'][strategy] = {'count': 0, 'symbols': set()}
        
        metrics['strategy_breakdown'][strategy]['count'] += len(entry_signals)
        metrics['strategy_breakdown'][strategy]['symbols'].add(result['symbol'])
        
        for signal in entry_signals:
            if 'Buy' in signal:
                metrics['buy_signals'] += 1
            elif 'Sell' in signal:
                metrics['sell_signals'] += 1
    
    return metrics