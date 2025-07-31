#!/usr/bin/env python3
"""
Minimal Trading Strategy Scanner Server
Works without asyncio/select modules - uses only basic Python HTTP server
"""

import sys
import json
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socketserver
import random

class TradingHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_index()
        elif self.path.startswith('/api/status'):
            self.serve_status()
        elif self.path.startswith('/api/strategies'):
            self.serve_strategies()
        elif self.path.startswith('/api/config'):
            self.serve_config()
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/scan'):
            self.handle_scan()
        elif self.path.startswith('/api/top-volume'):
            self.handle_top_volume()
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def serve_index(self):
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "index.html not found")
    
    def serve_status(self):
        response = {
            'connected': True,
            'message': 'Minimal server running - Demo mode active',
            'timestamp': datetime.now().isoformat(),
            'demo_mode': True
        }
        self.send_json_response(response)
    
    def serve_strategies(self):
        strategies = {
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
                "Ichimoku Basic Combo"
            ],
            "🔄 Mean Reversion": [
                "Mean Reversion (RSI)",
                "Scalping (Bollinger Bands)",
                "MACD RSI Oversold",
                "CCI Reversion",
                "Keltner RSI Oversold"
            ],
            "💥 Breakout & Patterns": [
                "Breakout Trading",
                "Opening Range Breakout",
                "Gap and Go",
                "Fractal Breakout RSI",
                "Pivot Point (Intraday S/R)"
            ],
            "📊 Volume & Volatility": [
                "VWAP RSI",
                "News Trading (Volatility Spike)",
                "TEMA Cross Volume",
                "VWAP Aroon",
                "Bollinger Upper Break Volume"
            ]
        }
        response = {
            'categories': strategies,
            'total_strategies': sum(len(s) for s in strategies.values())
        }
        self.send_json_response(response)
    
    def serve_config(self):
        config = {
            'timeframes': {
                "1 Minute": "1Min",
                "5 Minutes": "5Min", 
                "15 Minutes": "15Min",
                "30 Minutes": "30Min",
                "1 Hour": "1Hour",
                "1 Day": "1Day"
            },
            'data_limits': {
                "1Min": 200,
                "5Min": 300,
                "15Min": 400,
                "30Min": 500,
                "1Hour": 500,
                "1Day": 200
            },
            'default_tickers': ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        }
        self.send_json_response(config)
    
    def handle_scan(self):
        # Read request data
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            tickers = data.get('tickers', ['AAPL'])
            strategies = data.get('strategies', ['Momentum Trading'])
            timeframe = data.get('timeframe', '5Min')
            
            print(f"📊 Processing scan: {len(tickers)} tickers, {len(strategies)} strategies")
            
            # Simulate processing time
            time.sleep(1)
            
            # Generate demo results
            market_data = self.generate_demo_data(tickers, timeframe)
            strategy_results = self.generate_demo_signals(tickers, strategies)
            
            results = {
                'success': True,
                'scan_time': datetime.now().isoformat(),
                'tickers_scanned': len(tickers),
                'strategies_used': len(strategies),
                'timeframe': timeframe,
                'market_data': market_data,
                'strategy_results': strategy_results,
                'summary': {
                    'total_signals': len(strategy_results),
                    'buy_signals': len([r for r in strategy_results if any('Buy' in str(s) for s in r.get('entry_signals', []))]),
                    'sell_signals': len([r for r in strategy_results if any('Sell' in str(s) for s in r.get('entry_signals', []))]),
                    'symbols_with_signals': len(set(r['symbol'] for r in strategy_results if r.get('entry_signals')))
                }
            }
            
            print(f"✅ Scan completed: {results['summary']}")
            self.send_json_response(results)
            
        except Exception as e:
            print(f"❌ Scan error: {e}")
            self.send_json_response({'success': False, 'error': str(e)}, 500)
    
    def handle_top_volume(self):
        data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8'))
        limit = data.get('limit', 10)
        
        # Demo top volume tickers with realistic names
        all_tickers = [
            'AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX',
            'AMD', 'INTC', 'BABA', 'UBER', 'SNAP', 'ZOOM', 'ROKU', 'SQ',
            'PYPL', 'SHOP', 'TWTR', 'PINS', 'COIN', 'PLTR', 'SOFI', 'RIVN'
        ]
        
        # Shuffle and take requested amount
        selected_tickers = random.sample(all_tickers, min(limit, len(all_tickers)))
        
        response = {
            'success': True,
            'tickers': selected_tickers,
            'count': len(selected_tickers)
        }
        self.send_json_response(response)
    
    def generate_demo_data(self, tickers, timeframe):
        market_data = {}
        
        # Determine number of data points based on timeframe
        data_points_count = {
            '1Min': 60, '5Min': 48, '15Min': 32, 
            '30Min': 24, '1Hour': 24, '1Day': 30
        }.get(timeframe, 30)
        
        for ticker in tickers:
            data_points = []
            # Different base prices for different tickers
            base_prices = {
                'AAPL': 175, 'TSLA': 250, 'NVDA': 450, 'MSFT': 350,
                'GOOGL': 140, 'AMZN': 145, 'META': 320, 'NFLX': 400
            }
            base_price = base_prices.get(ticker, 150.0 + random.uniform(-50, 100))
            
            for i in range(data_points_count):
                # Create realistic price movement
                volatility = random.uniform(0.5, 3.0)
                price_change = random.uniform(-volatility, volatility)
                base_price = max(1.0, base_price + price_change)  # Ensure price stays positive
                
                # Create OHLC data
                open_price = base_price
                high_price = open_price + random.uniform(0, volatility)
                low_price = open_price - random.uniform(0, volatility)
                close_price = random.uniform(low_price, high_price)
                
                data_points.append({
                    'timestamp': datetime.now().isoformat(),
                    'open': round(open_price, 2),
                    'high': round(high_price, 2),
                    'low': round(low_price, 2),
                    'close': round(close_price, 2),
                    'volume': random.randint(100000, 5000000)
                })
                
                base_price = close_price  # Use close as next open
            
            market_data[ticker] = data_points
        
        return market_data
    
    def generate_demo_signals(self, tickers, strategies):
        signals = []
        
        for ticker in tickers:
            for strategy in strategies:
                # 60% chance of generating a signal
                if random.random() > 0.4:
                    signal_types = ['Buy', 'Sell']
                    signal_type = random.choice(signal_types)
                    
                    # Create realistic entry signal name
                    entry_signal = f"{strategy.replace(' ', '').replace('(', '').replace(')', '').replace('/', '')}_Entry_{signal_type}"
                    
                    signals.append({
                        'symbol': ticker,
                        'strategy': strategy,
                        'entry_signals': [entry_signal],
                        'latest_row': {
                            'timestamp': datetime.now().isoformat(),
                            'signal_strength': random.uniform(0.6, 0.95)
                        }
                    })
        
        return signals
    
    def send_json_response(self, data, status=200):
        response = json.dumps(data, indent=2)
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    allow_reuse_address = True

def main():
    print("🚀 Minimal Trading Strategy Scanner Server")
    print("=" * 60)
    print("✨ This version works without asyncio/select modules")
    print("🎯 Demo mode with simulated market data")
    print("=" * 60)
    
    port = 5000
    try:
        server = ThreadedHTTPServer(('0.0.0.0', port), TradingHandler)
        
        print(f"✅ Server running on http://localhost:{port}")
        print("🌐 Open your browser and navigate to the URL above")
        print("🎨 Enjoy your beautiful trading strategy scanner!")
        print("=" * 60)
        print("Press Ctrl+C to stop the server")
        
        server.serve_forever()
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print("Try stopping other servers or use a different port")
        else:
            print(f"❌ Server error: {e}")
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        if 'server' in locals():
            server.shutdown()

if __name__ == '__main__':
    main()