#!/usr/bin/env python3
"""
Modern Trading Strategy Scanner Backend
A Flask-based API server for the trading strategy scanner web application.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np

# Import your existing modules
try:
    from alpaca_connector import AlpacaConnector, DataFeed
    from strategy import run_strategies, STRATEGY_MAP
    from top_volume import get_top_volume_tickers
    from config import STRATEGY_CATEGORIES, TIMEFRAMES, DATA_LIMITS, DEFAULT_TICKERS
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required modules are available")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='.')
CORS(app)

# Global state
app_state = {
    'alpaca_connector': None,
    'is_connected': False,
    'last_scan_time': None,
    'executor': ThreadPoolExecutor(max_workers=4)
}

# API Configuration - Using your provided keys
API_CONFIG = {
    'ALPACA_API_KEY': 'AK2V88RDO5MYCFOE8FJH',
    'ALPACA_SECRET_KEY': 'gmCM49z9z3VlmTnoF7vsn9wliXZz6SE6NHCs5d5I',
    'PAPER_TRADING': False,
    'DATA_FEED': 'iex'
}

def initialize_alpaca_connector():
    """Initialize the Alpaca connector with provided credentials"""
    try:
        logger.info("Initializing Alpaca connector...")
        connector = AlpacaConnector(
            api_key=API_CONFIG['ALPACA_API_KEY'],
            secret_key=API_CONFIG['ALPACA_SECRET_KEY'],
            paper=API_CONFIG['PAPER_TRADING'],
            feed=DataFeed.IEX
        )
        
        if connector.is_operational:
            app_state['alpaca_connector'] = connector
            app_state['is_connected'] = True
            logger.info("✅ Alpaca connector initialized successfully")
            return True
        else:
            logger.error("❌ Alpaca connector failed to initialize")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error initializing Alpaca connector: {e}")
        return False

def run_async_in_thread(coro):
    """Run async function in thread pool"""
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    return app_state['executor'].submit(run_in_thread)

# Routes

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('.', filename)

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get connection status"""
    return jsonify({
        'connected': app_state['is_connected'],
        'message': 'Connected to Alpaca' if app_state['is_connected'] else 'Not connected',
        'last_scan': app_state['last_scan_time'].isoformat() if app_state['last_scan_time'] else None
    })

@app.route('/api/reconnect', methods=['POST'])
def reconnect():
    """Reconnect to Alpaca"""
    success = initialize_alpaca_connector()
    return jsonify({
        'success': success,
        'connected': app_state['is_connected'],
        'message': 'Reconnected successfully' if success else 'Reconnection failed'
    })

@app.route('/api/top-volume', methods=['POST'])
def get_top_volume():
    """Get top volume tickers"""
    try:
        data = request.get_json()
        limit = data.get('limit', 10)
        
        # Try to get top volume tickers
        tickers = get_top_volume_tickers(limit=limit)
        
        if not tickers:
            # Fallback to default tickers
            tickers = DEFAULT_TICKERS[:limit]
            logger.warning("Using default tickers as fallback")
        
        return jsonify({
            'success': True,
            'tickers': tickers,
            'count': len(tickers)
        })
        
    except Exception as e:
        logger.error(f"Error getting top volume tickers: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'tickers': DEFAULT_TICKERS[:10]  # Fallback
        }), 500

@app.route('/api/scan', methods=['POST'])
def run_scan():
    """Run trading strategy scan"""
    try:
        if not app_state['is_connected'] or not app_state['alpaca_connector']:
            return jsonify({
                'success': False,
                'error': 'Not connected to Alpaca. Please check connection.'
            }), 400
        
        data = request.get_json()
        tickers = data.get('tickers', [])
        strategies = data.get('strategies', [])
        timeframe = data.get('timeframe', '5Min')
        limit = data.get('limit', 200)
        
        if not tickers:
            return jsonify({
                'success': False,
                'error': 'No tickers provided'
            }), 400
        
        if not strategies:
            return jsonify({
                'success': False,
                'error': 'No strategies selected'
            }), 400
        
        logger.info(f"Starting scan for {len(tickers)} tickers with {len(strategies)} strategies")
        
        # Get market data
        logger.info("Fetching market data...")
        market_data = app_state['alpaca_connector'].get_historical_data(
            tickers=tickers,
            timeframe_str=timeframe,
            limit=limit
        )
        
        if not market_data:
            return jsonify({
                'success': False,
                'error': 'No market data retrieved'
            }), 500
        
        logger.info(f"Retrieved data for {len(market_data)} symbols")
        
        # Run strategies
        logger.info("Running strategy analysis...")
        strategy_results = run_strategies(market_data, strategies)
        
        # Prepare response data
        response_data = {
            'success': True,
            'scan_time': datetime.now().isoformat(),
            'tickers_scanned': len(tickers),
            'strategies_used': len(strategies),
            'market_data': prepare_market_data_for_response(market_data),
            'strategy_results': strategy_results,
            'summary': {
                'total_signals': len(strategy_results),
                'buy_signals': len([r for r in strategy_results if any('Buy' in str(s) for s in r.get('entry_signals', []))]),
                'sell_signals': len([r for r in strategy_results if any('Sell' in str(s) for s in r.get('entry_signals', []))]),
                'symbols_with_signals': len(set(r['symbol'] for r in strategy_results))
            }
        }
        
        app_state['last_scan_time'] = datetime.now()
        logger.info(f"Scan completed: {response_data['summary']}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Scan error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Scan failed: {str(e)}'
        }), 500

def prepare_market_data_for_response(market_data: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict]]:
    """Convert pandas DataFrames to JSON-serializable format"""
    response_data = {}
    
    for symbol, df in market_data.items():
        if df.empty:
            continue
            
        # Convert DataFrame to list of dictionaries
        records = []
        for idx, row in df.iterrows():
            record = {
                'timestamp': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'high': float(row['high']) if pd.notna(row['high']) else None,
                'low': float(row['low']) if pd.notna(row['low']) else None,
                'close': float(row['close']) if pd.notna(row['close']) else None,
                'volume': int(row['volume']) if pd.notna(row['volume']) else None
            }
            records.append(record)
        
        response_data[symbol] = records
    
    return response_data

@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """Get available strategies"""
    return jsonify({
        'categories': STRATEGY_CATEGORIES,
        'total_strategies': sum(len(strategies) for strategies in STRATEGY_CATEGORIES.values())
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get configuration options"""
    return jsonify({
        'timeframes': TIMEFRAMES,
        'data_limits': DATA_LIMITS,
        'default_tickers': DEFAULT_TICKERS
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def main():
    """Main function to start the server"""
    print("🚀 Starting Trading Strategy Scanner Server...")
    print("=" * 50)
    
    # Initialize Alpaca connector
    if initialize_alpaca_connector():
        print("✅ Alpaca connection established")
    else:
        print("⚠️  Alpaca connection failed - some features may not work")
    
    print(f"📊 Available strategies: {sum(len(s) for s in STRATEGY_CATEGORIES.values())}")
    print(f"🔧 API Keys configured: {'✅' if API_CONFIG['ALPACA_API_KEY'] else '❌'}")
    print("=" * 50)
    
    # Start the Flask server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🌐 Server starting on http://localhost:{port}")
    print("📱 Open your browser and navigate to the URL above")
    print("=" * 50)
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        # Cleanup
        if app_state['executor']:
            app_state['executor'].shutdown(wait=True)
        print("🧹 Cleanup completed")

if __name__ == '__main__':
    main()