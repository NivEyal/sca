# 🚀 Trading Strategy Scanner

A modern, web-based trading strategy scanner that analyzes market data using 50+ professional trading strategies. Built with a clean HTML/CSS/JavaScript frontend and Python Flask backend.

## ✨ Features

- **Real-time Market Data**: Connect to Alpaca Markets for live data
- **50+ Trading Strategies**: Comprehensive collection of momentum, trend-following, mean reversion, and breakout strategies
- **Interactive Charts**: Beautiful candlestick charts with signal overlays
- **Modern UI**: Clean, responsive design that works on all devices
- **Auto-refresh**: Automatic scanning with customizable intervals
- **Top Volume Stocks**: Automatically load the most active stocks
- **Custom Ticker Lists**: Add your own symbols to scan

## 🚀 Quick Start

### Option 1: One-Click Start
```bash
python run.py
```

### Option 2: Manual Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python server.py
```

3. Open your browser to: `http://localhost:5000`

## 📊 How to Use

1. **Select Tickers**: Choose from top volume stocks or enter custom symbols
2. **Pick Strategies**: Select from organized categories of trading strategies
3. **Configure Settings**: Set timeframe and data points
4. **Start Scan**: Click the scan button to analyze markets
5. **View Results**: See signals, charts, and market data

## 🔧 Configuration

The app is pre-configured with your API keys:
- **API Key**: AK2V88RDO5MYCFOE8FJH
- **Secret Key**: gmCM49z9z3VlmTnoF7vsn9wliXZz6SE6NHCs5d5I
- **Data Feed**: IEX (Free tier)
- **Paper Trading**: Disabled (Live data)

## 📈 Strategy Categories

- **🎯 Momentum**: MACD, ADX, MFI-based strategies
- **📈 Trend Following**: EMA, Golden Cross, Ichimoku
- **🔄 Mean Reversion**: RSI, Bollinger Bands, CCI
- **💥 Breakout & Patterns**: Support/Resistance, Gap trading
- **📊 Volume & Volatility**: VWAP, Volume analysis
- **🔧 Advanced Oscillators**: PSAR, TSI, Awesome Oscillator
- **🎪 Pattern Recognition**: Candlestick patterns, Divergences
- **🔀 Hybrid Strategies**: Multi-indicator combinations

## 🛠️ Technical Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Charts**: Chart.js
- **Backend**: Python Flask
- **Data**: Alpaca Markets API
- **Strategies**: pandas-ta, custom implementations

## 📁 Project Structure

```
trading-scanner/
├── index.html          # Main web interface
├── styles.css          # Styling and responsive design
├── app.js             # Frontend JavaScript logic
├── server.py          # Flask backend API
├── run.py             # Quick start script
├── requirements.txt   # Python dependencies
├── README.md          # This file
└── [existing modules] # Your strategy and data modules
```

## 🔌 API Endpoints

- `GET /` - Main application
- `GET /api/status` - Connection status
- `POST /api/scan` - Run strategy scan
- `POST /api/top-volume` - Get top volume stocks
- `GET /api/strategies` - Available strategies
- `GET /api/config` - Configuration options

## 🎨 Features Highlights

### Modern Design
- Gradient backgrounds and glass-morphism effects
- Smooth animations and transitions
- Responsive layout for all screen sizes
- Dark/light theme support

### Smart Scanning
- Progress indicators during scans
- Real-time signal detection
- Automatic data validation
- Error handling and fallbacks

### Interactive Results
- Expandable strategy categories
- Live price charts with signals
- Market data summaries
- Auto-refresh capabilities

## 🔒 Security Notes

- API keys are configured in the server code
- All requests are validated server-side
- CORS enabled for local development
- No sensitive data stored in browser

## 🚨 Disclaimer

This application is for educational and research purposes only. It is not financial advice. Always do your own research and consult with financial professionals before making investment decisions.

## 📞 Support

If you encounter any issues:
1. Check the console for error messages
2. Verify your internet connection
3. Ensure all required files are present
4. Try restarting the server

## 🎯 Next Steps

1. Run the application: `python run.py`
2. Open your browser to `http://localhost:5000`
3. Select your tickers and strategies
4. Start scanning the markets!

Happy trading! 🚀📈