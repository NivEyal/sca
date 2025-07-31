import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional
import numpy as np

def create_market_heatmap(market_data: Dict[str, pd.DataFrame]) -> go.Figure:
    """Create a market heatmap showing price changes"""
    symbols = []
    changes = []
    volumes = []
    prices = []
    
    for symbol, df in market_data.items():
        if df.empty:
            continue
            
        latest = df.iloc[-1]
        first = df.iloc[0]
        
        price_change = ((latest['close'] - first['open']) / first['open']) * 100
        
        symbols.append(symbol)
        changes.append(price_change)
        volumes.append(latest['volume'])
        prices.append(latest['close'])
    
    if not symbols:
        return go.Figure()
    
    # Create heatmap data
    fig = go.Figure(data=go.Scatter(
        x=volumes,
        y=changes,
        mode='markers+text',
        text=symbols,
        textposition="middle center",
        marker=dict(
            size=[np.log10(v) * 5 for v in volumes],  # Size based on volume
            color=changes,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Price Change %"),
            line=dict(width=1, color='white')
        ),
        hovertemplate='<b>%{text}</b><br>' +
                      'Price Change: %{y:.2f}%<br>' +
                      'Volume: %{x:,}<br>' +
                      '<extra></extra>'
    ))
    
    fig.update_layout(
        title="Market Overview - Price Change vs Volume",
        xaxis_title="Volume",
        yaxis_title="Price Change (%)",
        xaxis_type="log",
        height=500,
        showlegend=False
    )
    
    return fig

def create_volume_chart(market_data: Dict[str, pd.DataFrame]) -> go.Figure:
    """Create volume comparison chart"""
    fig = go.Figure()
    
    for symbol, df in market_data.items():
        if df.empty:
            continue
            
        # Calculate volume moving average
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        fig.add_trace(go.Bar(
            x=df.index,
            y=df['volume'],
            name=f"{symbol} Volume",
            opacity=0.7
        ))
    
    fig.update_layout(
        title="Volume Comparison",
        xaxis_title="Time",
        yaxis_title="Volume",
        height=400,
        barmode='group'
    )
    
    return fig

def create_price_performance_chart(market_data: Dict[str, pd.DataFrame]) -> go.Figure:
    """Create normalized price performance chart"""
    fig = go.Figure()
    
    for symbol, df in market_data.items():
        if df.empty:
            continue
            
        # Normalize prices to percentage change from start
        normalized_prices = ((df['close'] / df['close'].iloc[0]) - 1) * 100
        
        fig.add_trace(go.Scatter(
            x=df.index,
            y=normalized_prices,
            mode='lines',
            name=symbol,
            line=dict(width=2)
        ))
    
    fig.update_layout(
        title="Normalized Price Performance (%)",
        xaxis_title="Time",
        yaxis_title="Price Change (%)",
        height=400,
        hovermode='x unified'
    )
    
    return fig

def display_market_metrics(market_data: Dict[str, pd.DataFrame]):
    """Display key market metrics"""
    if not market_data:
        st.warning("No market data available")
        return
    
    metrics = []
    
    for symbol, df in market_data.items():
        if df.empty:
            continue
            
        latest = df.iloc[-1]
        first = df.iloc[0]
        
        price_change = ((latest['close'] - first['open']) / first['open']) * 100
        volume_avg = df['volume'].mean()
        volatility = df['close'].pct_change().std() * 100
        
        metrics.append({
            'Symbol': symbol,
            'Price': f"${latest['close']:.2f}",
            'Change %': f"{price_change:.2f}%",
            'Volume': f"{latest['volume']:,}",
            'Avg Volume': f"{volume_avg:,.0f}",
            'Volatility': f"{volatility:.2f}%"
        })
    
    if metrics:
        df_metrics = pd.DataFrame(metrics)
        
        # Style the dataframe
        def color_change(val):
            if '%' in str(val):
                num = float(val.replace('%', ''))
                if num > 0:
                    return 'background-color: #d4edda; color: #155724'
                elif num < 0:
                    return 'background-color: #f8d7da; color: #721c24'
            return ''
        
        styled_df = df_metrics.style.applymap(color_change, subset=['Change %'])
        st.dataframe(styled_df, use_container_width=True)

def create_correlation_heatmap(market_data: Dict[str, pd.DataFrame]) -> go.Figure:
    """Create correlation heatmap between symbols"""
    if len(market_data) < 2:
        return go.Figure()
    
    # Create price change matrix
    price_changes = {}
    
    for symbol, df in market_data.items():
        if not df.empty:
            price_changes[symbol] = df['close'].pct_change().dropna()
    
    if len(price_changes) < 2:
        return go.Figure()
    
    # Align all series to same index
    df_changes = pd.DataFrame(price_changes)
    correlation_matrix = df_changes.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.index,
        colorscale='RdBu',
        zmid=0,
        text=correlation_matrix.round(2).values,
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False
    ))
    
    fig.update_layout(
        title="Price Correlation Matrix",
        height=400
    )
    
    return fig