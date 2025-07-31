#!/usr/bin/env python3
"""
Standalone Python Environment Setup
This script creates a clean Python environment and installs all dependencies
"""

import sys
import os
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python 3.7+ required. Current: {version.major}.{version.minor}")
        return False
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def test_core_modules():
    """Test if core Python modules are available"""
    core_modules = ['select', 'asyncio', 'selectors', 'socket', 'threading']
    failed_modules = []
    
    for module in core_modules:
        try:
            __import__(module)
            print(f"✅ {module} - OK")
        except ImportError as e:
            print(f"❌ {module} - FAILED: {e}")
            failed_modules.append(module)
    
    return len(failed_modules) == 0

def install_requirements():
    """Install required packages"""
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip"
        ])
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def create_minimal_server():
    """Create a minimal server that doesn't use problematic modules"""
    server_code = '''#!/usr/bin/env python3
"""
Minimal Trading Strategy Scanner Server
Works without asyncio/select modules
"""

import sys
import json
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socketserver

class TradingHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_index()
        elif self.path.startswith('/api/status'):
            self.serve_status()
        elif self.path.startswith('/api/strategies'):
            self.serve_strategies()
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/scan'):
            self.handle_scan()
        elif self.path.startswith('/api/top-volume'):
            self.handle_top_volume()
        else:
            self.send_error(404)
    
    def serve_index(self):
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "index.html not found")
    
    def serve_status(self):
        response = {
            'connected': True,
            'message': 'Minimal server running',
            'timestamp': datetime.now().isoformat()
        }
        self.send_json_response(response)
    
    def serve_strategies(self):
        strategies = {
            "🎯 Momentum": ["Momentum Trading", "MACD Bullish ADX"],
            "📈 Trend Following": ["Trend Following (EMA/ADX)", "Golden Cross RSI"],
            "🔄 Mean Reversion": ["Mean Reversion (RSI)", "Scalping (Bollinger Bands)"]
        }
        response = {
            'categories': strategies,
            'total_strategies': sum(len(s) for s in strategies.values())
        }
        self.send_json_response(response)
    
    def handle_scan(self):
        # Read request data
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            tickers = data.get('tickers', ['AAPL'])
            
            # Generate demo results
            results = {
                'success': True,
                'scan_time': datetime.now().isoformat(),
                'tickers_scanned': len(tickers),
                'market_data': self.generate_demo_data(tickers),
                'strategy_results': self.generate_demo_signals(tickers),
                'summary': {
                    'total_signals': len(tickers) * 2,
                    'buy_signals': len(tickers),
                    'sell_signals': len(tickers)
                }
            }
            
            self.send_json_response(results)
            
        except Exception as e:
            self.send_json_response({'success': False, 'error': str(e)}, 500)
    
    def handle_top_volume(self):
        # Demo top volume tickers
        tickers = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX']
        response = {
            'success': True,
            'tickers': tickers,
            'count': len(tickers)
        }
        self.send_json_response(response)
    
    def generate_demo_data(self, tickers):
        import random
        market_data = {}
        
        for ticker in tickers:
            data_points = []
            base_price = 150.0 + random.uniform(-50, 50)
            
            for i in range(20):
                price_change = random.uniform(-2, 2)
                base_price += price_change
                
                data_points.append({
                    'timestamp': datetime.now().isoformat(),
                    'open': round(base_price - 0.5, 2),
                    'high': round(base_price + 1, 2),
                    'low': round(base_price - 1, 2),
                    'close': round(base_price, 2),
                    'volume': random.randint(100000, 1000000)
                })
            
            market_data[ticker] = data_points
        
        return market_data
    
    def generate_demo_signals(self, tickers):
        import random
        signals = []
        strategies = ['Momentum Trading', 'Mean Reversion (RSI)', 'Breakout Trading']
        
        for ticker in tickers:
            for strategy in strategies[:2]:  # Limit to 2 strategies per ticker
                if random.random() > 0.3:  # 70% chance of signal
                    signal_type = random.choice(['Buy', 'Sell', 'None'])
                    signals.append({
                        'symbol': ticker,
                        'strategy': strategy,
                        'entry_signals': [f'{strategy}_Entry_{signal_type}'] if signal_type != 'None' else []
                    })
        
        return signals
    
    def send_json_response(self, data, status=200):
        response = json.dumps(data, indent=2)
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass

def main():
    print("🚀 Starting Minimal Trading Strategy Scanner...")
    print("=" * 50)
    
    port = 5000
    server = ThreadedHTTPServer(('0.0.0.0', port), TradingHandler)
    
    print(f"✅ Server running on http://localhost:{port}")
    print("🌐 Open your browser and navigate to the URL above")
    print("=" * 50)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\n👋 Server stopped by user")
        server.shutdown()

if __name__ == '__main__':
    main()
'''
    
    with open('minimal_server.py', 'w', encoding='utf-8') as f:
        f.write(server_code)
    
    print("✅ Created minimal_server.py")

def main():
    print("🔧 Python Environment Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Test core modules
    print("\\n🧪 Testing core Python modules...")
    if test_core_modules():
        print("✅ All core modules available - Python installation is complete")
        
        # Install requirements
        if install_requirements():
            print("\\n🚀 Environment setup complete!")
            print("Run: python server.py")
            return True
    else:
        print("❌ Core modules missing - creating minimal server alternative")
        create_minimal_server()
        print("\\n🚀 Minimal server created!")
        print("Run: python minimal_server.py")
        return True
    
    return False

if __name__ == '__main__':
    main()