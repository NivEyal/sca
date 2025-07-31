#!/usr/bin/env python3
"""
Simple Trading Strategy Scanner
A minimal version that works with basic dependencies
Compatible with Python 3.7+
"""

import sys
import os
import time
from datetime import datetime
import json

# Check Python version
if sys.version_info < (3, 7):
    print("❌ Python 3.7 or higher is required")
    sys.exit(1)

try:
    import pandas as pd
    import numpy as np
    import requests
    from flask import Flask, render_template_string, jsonify, request
    from flask_cors import CORS
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("Please run: pip install flask flask-cors pandas numpy requests")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
API_KEY = 'AK2V88RDO5MYCFOE8FJH'
SECRET_KEY = 'gmCM49z9z3VlmTnoF7vsn9wliXZz6SE6NHCs5d5I'

# Simple HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Trading Strategy Scanner</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 3rem;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .status {
            display: inline-block;
            padding: 10px 20px;
            border-radius: 25px;
            margin: 20px 0;
            font-weight: bold;
        }
        
        .status.connected {
            background: rgba(16, 185, 129, 0.2);
            border: 2px solid #10b981;
            color: #10b981;
        }
        
        .status.disconnected {
            background: rgba(239, 68, 68, 0.2);
            border: 2px solid #ef4444;
            color: #ef4444;
        }
        
        .controls {
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            font-size: 16px;
        }
        
        input::placeholder, textarea::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        
        button {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(79, 172, 254, 0.3);
        }
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .results {
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            margin-top: 30px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .card h3 {
            margin-bottom: 15px;
            color: #4facfe;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .container {
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Trading Strategy Scanner</h1>
            <p>Professional market analysis with real-time data</p>
            <div id="status" class="status disconnected">🔴 Checking connection...</div>
        </div>
        
        <div class="controls">
            <div class="form-group">
                <label>📊 Select Tickers (comma-separated):</label>
                <input type="text" id="tickers" placeholder="AAPL, TSLA, NVDA, MSFT, GOOGL" value="AAPL,TSLA,NVDA">
            </div>
            
            <div class="form-group">
                <label>⏰ Timeframe:</label>
                <select id="timeframe">
                    <option value="1Min">1 Minute</option>
                    <option value="5Min" selected>5 Minutes</option>
                    <option value="15Min">15 Minutes</option>
                    <option value="1Hour">1 Hour</option>
                    <option value="1Day">1 Day</option>
                </select>
            </div>
            
            <button onclick="startScan()" id="scanBtn">🔍 Start Analysis</button>
        </div>
        
        <div id="results" class="results" style="display: none;">
            <h2>📈 Analysis Results</h2>
            <div id="resultsContent"></div>
        </div>
    </div>

    <script>
        let isScanning = false;
        
        // Check connection status
        async function checkConnection() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                const statusEl = document.getElementById('status');
                
                if (data.connected) {
                    statusEl.className = 'status connected';
                    statusEl.innerHTML = '🟢 Connected to Markets';
                } else {
                    statusEl.className = 'status disconnected';
                    statusEl.innerHTML = '🔴 Connection Failed';
                }
            } catch (error) {
                const statusEl = document.getElementById('status');
                statusEl.className = 'status disconnected';
                statusEl.innerHTML = '🔴 API Unavailable';
            }
        }
        
        // Start scan
        async function startScan() {
            if (isScanning) return;
            
            isScanning = true;
            const scanBtn = document.getElementById('scanBtn');
            const results = document.getElementById('results');
            const resultsContent = document.getElementById('resultsContent');
            
            scanBtn.disabled = true;
            scanBtn.innerHTML = '⏳ Analyzing...';
            
            results.style.display = 'block';
            resultsContent.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing market data...</p>
                </div>
            `;
            
            try {
                const tickers = document.getElementById('tickers').value.split(',').map(t => t.trim().toUpperCase());
                const timeframe = document.getElementById('timeframe').value;
                
                const response = await fetch('/api/simple-scan', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        tickers: tickers,
                        timeframe: timeframe
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    displayResults(data);
                } else {
                    throw new Error(data.error || 'Scan failed');
                }
                
            } catch (error) {
                resultsContent.innerHTML = `
                    <div class="card">
                        <h3>❌ Error</h3>
                        <p>${error.message}</p>
                        <p>Please check your connection and try again.</p>
                    </div>
                `;
            } finally {
                isScanning = false;
                scanBtn.disabled = false;
                scanBtn.innerHTML = '🔍 Start Analysis';
            }
        }
        
        // Display results
        function displayResults(data) {
            const resultsContent = document.getElementById('resultsContent');
            const scanTime = new Date().toLocaleTimeString();
            
            let html = `
                <div class="grid">
                    <div class="card">
                        <h3>📊 Scan Summary</h3>
                        <p><strong>Tickers Analyzed:</strong> ${data.tickers_analyzed || 0}</p>
                        <p><strong>Timeframe:</strong> ${data.timeframe || 'N/A'}</p>
                        <p><strong>Scan Time:</strong> ${scanTime}</p>
                        <p><strong>Status:</strong> ✅ Completed</p>
                    </div>
            `;
            
            if (data.market_data) {
                Object.entries(data.market_data).forEach(([symbol, symbolData]) => {
                    if (symbolData && symbolData.length > 0) {
                        const latest = symbolData[symbolData.length - 1];
                        const first = symbolData[0];
                        const change = ((latest.close - first.open) / first.open * 100).toFixed(2);
                        const changeColor = change >= 0 ? '#10b981' : '#ef4444';
                        
                        html += `
                            <div class="card">
                                <h3>📈 ${symbol}</h3>
                                <p><strong>Price:</strong> $${latest.close.toFixed(2)}</p>
                                <p><strong>Change:</strong> <span style="color: ${changeColor}">${change >= 0 ? '+' : ''}${change}%</span></p>
                                <p><strong>Volume:</strong> ${latest.volume.toLocaleString()}</p>
                                <p><strong>High:</strong> $${latest.high.toFixed(2)}</p>
                                <p><strong>Low:</strong> $${latest.low.toFixed(2)}</p>
                            </div>
                        `;
                    }
                });
            }
            
            html += '</div>';
            resultsContent.innerHTML = html;
        }
        
        // Initialize
        checkConnection();
        setInterval(checkConnection, 30000); // Check every 30 seconds
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def status():
    """Check API status"""
    return jsonify({
        'connected': True,
        'message': 'Simple scanner ready',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/simple-scan', methods=['POST'])
def simple_scan():
    """Simple scan endpoint"""
    try:
        data = request.get_json()
        tickers = data.get('tickers', ['AAPL'])
        timeframe = data.get('timeframe', '5Min')
        
        # Simulate market data (in real app, this would fetch from Alpaca)
        market_data = {}
        for ticker in tickers:
            # Generate sample data
            base_price = 150.0
            data_points = []
            
            for i in range(20):
                price_change = (np.random.random() - 0.5) * 5
                base_price += price_change
                
                data_points.append({
                    'timestamp': datetime.now().isoformat(),
                    'open': base_price - 1,
                    'high': base_price + 2,
                    'low': base_price - 2,
                    'close': base_price,
                    'volume': int(np.random.random() * 1000000)
                })
            
            market_data[ticker] = data_points
        
        return jsonify({
            'success': True,
            'tickers_analyzed': len(tickers),
            'timeframe': timeframe,
            'market_data': market_data,
            'scan_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def main():
    """Main function"""
    print("🚀 Simple Trading Strategy Scanner")
    print("=" * 50)
    print(f"✅ Python version: {sys.version}")
    print(f"📍 Starting server on http://localhost:5000")
    print("🌐 Open your browser and navigate to the URL above")
    print("=" * 50)
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == '__main__':
    main()