// App State
let appState = {
    selectedTickers: [],
    selectedStrategies: [],
    isConnected: false,
    isScanning: false,
    autoRefresh: false,
    refreshTimer: null,
    countdownTimer: null,
    lastScanTime: null
};

// Strategy Categories
const STRATEGY_CATEGORIES = {
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
};

// Initialize App
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    renderStrategyCategories();
    loadDefaultTickers();
    checkConnection();
}

function setupEventListeners() {
    // Ticker source selection
    document.querySelectorAll('input[name="tickerSource"]').forEach(radio => {
        radio.addEventListener('change', handleTickerSourceChange);
    });

    // Number of tickers slider
    const numTickersSlider = document.getElementById('numTickers');
    const numTickersValue = document.getElementById('numTickersValue');
    numTickersSlider.addEventListener('input', function() {
        numTickersValue.textContent = this.value;
    });

    // Data limit slider
    const dataLimitSlider = document.getElementById('dataLimit');
    const dataLimitValue = document.getElementById('dataLimitValue');
    dataLimitSlider.addEventListener('input', function() {
        dataLimitValue.textContent = this.value;
    });

    // Load top volume button
    document.getElementById('loadTopVolume').addEventListener('click', loadTopVolumeTickers);

    // Custom tickers input
    document.getElementById('customTickers').addEventListener('input', handleCustomTickersInput);

    // Strategy selection buttons
    document.getElementById('selectAllStrategies').addEventListener('click', selectAllStrategies);
    document.getElementById('clearAllStrategies').addEventListener('click', clearAllStrategies);

    // Auto refresh checkbox
    document.getElementById('autoRefresh').addEventListener('change', handleAutoRefreshChange);

    // Start scan button
    document.getElementById('startScan').addEventListener('click', startScan);
}

function handleTickerSourceChange(event) {
    const topVolumeControls = document.getElementById('topVolumeControls');
    const customTickerControls = document.getElementById('customTickerControls');
    
    if (event.target.value === 'top') {
        topVolumeControls.style.display = 'block';
        customTickerControls.style.display = 'none';
        loadDefaultTickers();
    } else {
        topVolumeControls.style.display = 'none';
        customTickerControls.style.display = 'block';
        handleCustomTickersInput();
    }
}

function handleCustomTickersInput() {
    const input = document.getElementById('customTickers').value;
    const tickers = input
        .replace(/,/g, '\n')
        .split('\n')
        .map(ticker => ticker.trim().toUpperCase())
        .filter(ticker => ticker.length > 0);
    
    appState.selectedTickers = tickers;
    updateSelectedTickersDisplay();
}

function handleAutoRefreshChange(event) {
    appState.autoRefresh = event.target.checked;
    if (appState.autoRefresh && appState.lastScanTime) {
        startRefreshCountdown();
    } else {
        stopRefreshCountdown();
    }
}

function renderStrategyCategories() {
    const container = document.getElementById('strategyCategories');
    container.innerHTML = '';

    Object.entries(STRATEGY_CATEGORIES).forEach(([category, strategies]) => {
        const categoryDiv = document.createElement('div');
        categoryDiv.className = 'strategy-category';

        const header = document.createElement('div');
        header.className = 'category-header';
        header.innerHTML = `
            <span>${category}</span>
            <i class="fas fa-chevron-down"></i>
        `;

        const strategiesDiv = document.createElement('div');
        strategiesDiv.className = 'category-strategies';

        strategies.forEach(strategy => {
            const strategyDiv = document.createElement('div');
            strategyDiv.className = 'strategy-item';
            strategyDiv.innerHTML = `
                <input type="checkbox" id="strategy-${strategy}" value="${strategy}">
                <label for="strategy-${strategy}">${strategy}</label>
            `;

            const checkbox = strategyDiv.querySelector('input');
            checkbox.addEventListener('change', handleStrategySelection);

            strategiesDiv.appendChild(strategyDiv);
        });

        header.addEventListener('click', () => {
            const isExpanded = strategiesDiv.classList.contains('expanded');
            strategiesDiv.classList.toggle('expanded');
            const icon = header.querySelector('i');
            icon.className = isExpanded ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
        });

        categoryDiv.appendChild(header);
        categoryDiv.appendChild(strategiesDiv);
        container.appendChild(categoryDiv);
    });
}

function handleStrategySelection() {
    const selectedCheckboxes = document.querySelectorAll('#strategyCategories input[type="checkbox"]:checked');
    appState.selectedStrategies = Array.from(selectedCheckboxes).map(cb => cb.value);
}

function selectAllStrategies() {
    const checkboxes = document.querySelectorAll('#strategyCategories input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = true);
    appState.selectedStrategies = Array.from(checkboxes).map(cb => cb.value);
}

function clearAllStrategies() {
    const checkboxes = document.querySelectorAll('#strategyCategories input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
    appState.selectedStrategies = [];
}

async function loadDefaultTickers() {
    try {
        const numTickers = document.getElementById('numTickers').value;
        // For demo purposes, using default tickers
        const defaultTickers = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", 
            "NVDA", "META", "NFLX", "AMD", "INTC",
            "BABA", "UBER", "SNAP", "ZOOM", "ROKU",
            "SQ", "PYPL", "SHOP", "TWTR", "PINS"
        ];
        
        appState.selectedTickers = defaultTickers.slice(0, parseInt(numTickers));
        updateSelectedTickersDisplay();
    } catch (error) {
        console.error('Error loading default tickers:', error);
        showNotification('Failed to load top volume tickers', 'error');
    }
}

async function loadTopVolumeTickers() {
    try {
        showNotification('Loading top volume tickers...', 'info');
        const numTickers = document.getElementById('numTickers').value;
        
        // In a real implementation, this would call your backend API
        const response = await fetch('/api/top-volume', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ limit: parseInt(numTickers) })
        });

        if (response.ok) {
            const data = await response.json();
            appState.selectedTickers = data.tickers || [];
            updateSelectedTickersDisplay();
            showNotification(`Loaded ${appState.selectedTickers.length} tickers`, 'success');
        } else {
            throw new Error('Failed to fetch top volume tickers');
        }
    } catch (error) {
        console.error('Error loading top volume tickers:', error);
        // Fallback to default tickers
        loadDefaultTickers();
        showNotification('Using default tickers (API unavailable)', 'warning');
    }
}

function updateSelectedTickersDisplay() {
    const container = document.getElementById('selectedTickers');
    if (appState.selectedTickers.length === 0) {
        container.innerHTML = '<small>No tickers selected</small>';
    } else {
        const displayTickers = appState.selectedTickers.slice(0, 5);
        const remaining = appState.selectedTickers.length - 5;
        let text = displayTickers.join(', ');
        if (remaining > 0) {
            text += ` +${remaining} more`;
        }
        container.innerHTML = `<small><strong>Selected:</strong> ${text}</small>`;
    }
}

async function checkConnection() {
    try {
        const response = await fetch('/api/status');
        if (response.ok) {
            const data = await response.json();
            updateConnectionStatus(data.connected, data.message);
        } else {
            updateConnectionStatus(false, 'API unavailable');
        }
    } catch (error) {
        updateConnectionStatus(false, 'Connection failed');
    }
}

function updateConnectionStatus(connected, message) {
    const statusElement = document.getElementById('connectionStatus');
    const icon = statusElement.querySelector('i');
    const text = statusElement.querySelector('span');
    
    appState.isConnected = connected;
    
    if (connected) {
        statusElement.className = 'connection-status connected';
        icon.className = 'fas fa-circle';
        text.textContent = 'Connected';
    } else {
        statusElement.className = 'connection-status disconnected';
        icon.className = 'fas fa-circle';
        text.textContent = message || 'Disconnected';
    }
}

async function startScan() {
    if (appState.selectedTickers.length === 0) {
        showNotification('Please select at least one ticker', 'warning');
        return;
    }

    if (appState.selectedStrategies.length === 0) {
        showNotification('Please select at least one strategy', 'warning');
        return;
    }

    if (appState.isScanning) {
        return;
    }

    appState.isScanning = true;
    showLoadingScreen();
    
    try {
        const timeframe = document.getElementById('timeframe').value;
        const dataLimit = document.getElementById('dataLimit').value;

        const scanData = {
            tickers: appState.selectedTickers,
            strategies: appState.selectedStrategies,
            timeframe: timeframe,
            limit: parseInt(dataLimit)
        };

        // Simulate scanning progress
        await simulateScanProgress();

        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(scanData)
        });

        if (response.ok) {
            const results = await response.json();
            displayResults(results);
            appState.lastScanTime = Date.now();
            
            if (appState.autoRefresh) {
                startRefreshCountdown();
            }
        } else {
            throw new Error('Scan failed');
        }
    } catch (error) {
        console.error('Scan error:', error);
        showNotification('Scan failed. Please try again.', 'error');
        showWelcomeScreen();
    } finally {
        appState.isScanning = false;
    }
}

async function simulateScanProgress() {
    const progressFill = document.getElementById('progressFill');
    const steps = [20, 40, 60, 80, 100];
    
    for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 500));
        progressFill.style.width = steps[i] + '%';
    }
}

function showLoadingScreen() {
    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('resultsContainer').style.display = 'none';
    document.getElementById('loadingScreen').style.display = 'flex';
    
    // Reset progress
    document.getElementById('progressFill').style.width = '0%';
}

function showWelcomeScreen() {
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('resultsContainer').style.display = 'none';
    document.getElementById('welcomeScreen').style.display = 'flex';
}

function showResultsScreen() {
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('resultsContainer').style.display = 'block';
}

function displayResults(results) {
    showResultsScreen();
    
    // Display metrics
    displayMetrics(results);
    
    // Display individual results
    displayResultCards(results);
}

function displayMetrics(results) {
    const metricsRow = document.getElementById('metricsRow');
    
    const totalSignals = results.strategy_results ? results.strategy_results.length : 0;
    const buySignals = results.strategy_results ? 
        results.strategy_results.filter(r => 
            r.entry_signals && r.entry_signals.some(s => s.includes('Buy'))
        ).length : 0;
    const sellSignals = results.strategy_results ? 
        results.strategy_results.filter(r => 
            r.entry_signals && r.entry_signals.some(s => s.includes('Sell'))
        ).length : 0;
    
    const scanTime = new Date().toLocaleTimeString();
    
    metricsRow.innerHTML = `
        <div class="metric-card">
            <div class="metric-value">${totalSignals}</div>
            <div class="metric-label">Total Signals</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${buySignals}</div>
            <div class="metric-label">Buy Signals</div>
            <div class="metric-change positive">+${buySignals}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${sellSignals}</div>
            <div class="metric-label">Sell Signals</div>
            <div class="metric-change negative">${sellSignals > 0 ? '-' : ''}${sellSignals}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${scanTime}</div>
            <div class="metric-label">Last Scan</div>
        </div>
    `;
}

function displayResultCards(results) {
    const resultsGrid = document.getElementById('resultsGrid');
    resultsGrid.innerHTML = '';

    if (!results.strategy_results || results.strategy_results.length === 0) {
        resultsGrid.innerHTML = `
            <div class="result-card">
                <div class="result-header">
                    <div class="result-symbol">No Signals Found</div>
                </div>
                <p>No trading signals were detected for the selected tickers and strategies. Try adjusting your selection or timeframe.</p>
            </div>
        `;
        return;
    }

    // Group results by symbol
    const groupedResults = {};
    results.strategy_results.forEach(result => {
        const symbol = result.symbol;
        if (!groupedResults[symbol]) {
            groupedResults[symbol] = [];
        }
        groupedResults[symbol].push(result);
    });

    Object.entries(groupedResults).forEach(([symbol, symbolResults]) => {
        const resultCard = createResultCard(symbol, symbolResults, results.market_data);
        resultsGrid.appendChild(resultCard);
    });
}

function createResultCard(symbol, symbolResults, marketData) {
    const card = document.createElement('div');
    card.className = 'result-card';

    // Get market data for this symbol
    const symbolMarketData = marketData && marketData[symbol] ? marketData[symbol] : null;
    const latestPrice = symbolMarketData ? symbolMarketData[symbolMarketData.length - 1] : null;
    const firstPrice = symbolMarketData ? symbolMarketData[0] : null;
    
    let priceChange = 0;
    let priceChangePercent = 0;
    if (latestPrice && firstPrice) {
        priceChange = latestPrice.close - firstPrice.open;
        priceChangePercent = (priceChange / firstPrice.open) * 100;
    }

    card.innerHTML = `
        <div class="result-header">
            <div class="result-symbol">${symbol}</div>
            <div class="result-price">
                <div class="price-value">$${latestPrice ? latestPrice.close.toFixed(2) : 'N/A'}</div>
                <div class="price-change ${priceChange >= 0 ? 'positive' : 'negative'}">
                    ${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)} (${priceChangePercent.toFixed(2)}%)
                </div>
            </div>
        </div>
        <div class="result-content">
            <div class="chart-container">
                <canvas id="chart-${symbol}"></canvas>
            </div>
            <div class="signals-panel">
                <div class="signals-header">🎯 Active Signals</div>
                ${createSignalsHTML(symbolResults)}
                <div class="market-data">
                    <div class="market-data-item">
                        <span class="market-data-label">Volume:</span>
                        <span class="market-data-value">${latestPrice ? latestPrice.volume.toLocaleString() : 'N/A'}</span>
                    </div>
                    <div class="market-data-item">
                        <span class="market-data-label">High:</span>
                        <span class="market-data-value">$${latestPrice ? latestPrice.high.toFixed(2) : 'N/A'}</span>
                    </div>
                    <div class="market-data-item">
                        <span class="market-data-label">Low:</span>
                        <span class="market-data-value">$${latestPrice ? latestPrice.low.toFixed(2) : 'N/A'}</span>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Create chart after the card is added to DOM
    setTimeout(() => {
        if (symbolMarketData) {
            createChart(symbol, symbolMarketData);
        }
    }, 100);

    return card;
}

function createSignalsHTML(symbolResults) {
    let signalsHTML = '';
    
    symbolResults.forEach(result => {
        const strategy = result.strategy;
        const entrySignals = result.entry_signals || [];
        
        entrySignals.forEach(signal => {
            let signalClass = 'signal-none';
            let signalText = signal;
            
            if (signal.includes('Buy')) {
                signalClass = 'signal-buy';
                signalText = '🟢 BUY';
            } else if (signal.includes('Sell')) {
                signalClass = 'signal-sell';
                signalText = '🔴 SELL';
            }
            
            signalsHTML += `
                <div class="signal-item ${signalClass}">
                    <div style="font-weight: bold;">${signalText}</div>
                    <div style="font-size: 0.8em; margin-top: 0.25rem;">${strategy}</div>
                </div>
            `;
        });
    });
    
    if (!signalsHTML) {
        signalsHTML = '<div class="signal-item signal-none">No signals detected</div>';
    }
    
    return signalsHTML;
}

function createChart(symbol, data) {
    const ctx = document.getElementById(`chart-${symbol}`);
    if (!ctx) return;

    const labels = data.map(item => new Date(item.timestamp).toLocaleTimeString());
    const prices = data.map(item => item.close);
    const volumes = data.map(item => item.volume);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Price',
                data: prices,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                }
            },
            elements: {
                point: {
                    radius: 0,
                    hoverRadius: 4
                }
            }
        }
    });
}

function startRefreshCountdown() {
    if (appState.countdownTimer) {
        clearInterval(appState.countdownTimer);
    }

    let timeLeft = 30;
    const countdownElement = document.getElementById('refreshCountdown');
    const timerElement = document.getElementById('countdownTimer');
    
    countdownElement.style.display = 'flex';
    
    appState.countdownTimer = setInterval(() => {
        timeLeft--;
        timerElement.textContent = timeLeft;
        
        if (timeLeft <= 0) {
            clearInterval(appState.countdownTimer);
            countdownElement.style.display = 'none';
            if (appState.autoRefresh) {
                startScan();
            }
        }
    }, 1000);
}

function stopRefreshCountdown() {
    if (appState.countdownTimer) {
        clearInterval(appState.countdownTimer);
        appState.countdownTimer = null;
    }
    document.getElementById('refreshCountdown').style.display = 'none';
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)}"></i>
        <span>${message}</span>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 2rem;
        right: 2rem;
        background: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border-left: 4px solid ${getNotificationColor(type)};
        display: flex;
        align-items: center;
        gap: 0.5rem;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

function getNotificationIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'error': return 'exclamation-circle';
        case 'warning': return 'exclamation-triangle';
        default: return 'info-circle';
    }
}

function getNotificationColor(type) {
    switch (type) {
        case 'success': return '#28a745';
        case 'error': return '#dc3545';
        case 'warning': return '#ffc107';
        default: return '#17a2b8';
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);