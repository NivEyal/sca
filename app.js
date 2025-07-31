// App State
let appState = {
    selectedTickers: [],
    selectedStrategies: [],
    isConnected: false,
    isScanning: false,
    autoRefresh: false,
    refreshTimer: null,
    countdownTimer: null,
    lastScanTime: null,
    animationQueue: []
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
    initializeAnimations();
});

function initializeApp() {
    setupEventListeners();
    renderStrategyCategories();
    loadDefaultTickers();
    checkConnection();
    setupMobileOptimizations();
}

function initializeAnimations() {
    // Add entrance animations to elements
    const animatedElements = document.querySelectorAll('.sidebar, .results-area, .header');
    animatedElements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        setTimeout(() => {
            el.style.transition = 'all 0.6s ease';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, index * 200);
    });
}

function setupMobileOptimizations() {
    // Show/hide mobile FAB based on screen size
    function updateMobileView() {
        const fab = document.getElementById('mobileFab');
        const startScanBtn = document.getElementById('startScan');
        
        if (window.innerWidth <= 768) {
            fab.style.display = 'flex';
            fab.onclick = () => startScan();
        } else {
            fab.style.display = 'none';
        }
    }
    
    updateMobileView();
    window.addEventListener('resize', updateMobileView);
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
        // Add pulse animation to value
        numTickersValue.style.transform = 'scale(1.2)';
        setTimeout(() => {
            numTickersValue.style.transform = 'scale(1)';
        }, 150);
    });

    // Data limit slider
    const dataLimitSlider = document.getElementById('dataLimit');
    const dataLimitValue = document.getElementById('dataLimitValue');
    dataLimitSlider.addEventListener('input', function() {
        dataLimitValue.textContent = this.value;
        // Add pulse animation to value
        dataLimitValue.style.transform = 'scale(1.2)';
        setTimeout(() => {
            dataLimitValue.style.transform = 'scale(1)';
        }, 150);
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
            
            // Add rotation animation
            icon.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(180deg)';
        });

        categoryDiv.appendChild(header);
        categoryDiv.appendChild(strategiesDiv);
        container.appendChild(categoryDiv);
    });
}

function handleStrategySelection() {
    const selectedCheckboxes = document.querySelectorAll('#strategyCategories input[type="checkbox"]:checked');
    appState.selectedStrategies = Array.from(selectedCheckboxes).map(cb => cb.value);
    
    // Update UI with selection count
    updateStrategySelectionCount();
}

function updateStrategySelectionCount() {
    const count = appState.selectedStrategies.length;
    const scanButton = document.getElementById('startScan');
    const icon = scanButton.querySelector('i');
    
    if (count > 0) {
        scanButton.innerHTML = `<i class="fas fa-search"></i> Scan with ${count} Strategies`;
        scanButton.classList.add('btn-ready');
    } else {
        scanButton.innerHTML = `<i class="fas fa-search"></i> Start Premium Scan`;
        scanButton.classList.remove('btn-ready');
    }
}

function selectAllStrategies() {
    const checkboxes = document.querySelectorAll('#strategyCategories input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = true);
    appState.selectedStrategies = Array.from(checkboxes).map(cb => cb.value);
    updateStrategySelectionCount();
    showNotification(`Selected all ${appState.selectedStrategies.length} strategies`, 'success');
}

function clearAllStrategies() {
    const checkboxes = document.querySelectorAll('#strategyCategories input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
    appState.selectedStrategies = [];
    updateStrategySelectionCount();
    showNotification('Cleared all strategy selections', 'info');
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
        showNotification(`Loaded ${appState.selectedTickers.length} default tickers`, 'info');
    } catch (error) {
        console.error('Error loading default tickers:', error);
        showNotification('Failed to load top volume tickers', 'error');
    }
}

async function loadTopVolumeTickers() {
    try {
        const loadButton = document.getElementById('loadTopVolume');
        const originalText = loadButton.innerHTML;
        
        // Show loading state
        loadButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        loadButton.disabled = true;
        
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
            showNotification(`✨ Loaded ${appState.selectedTickers.length} top volume tickers`, 'success');
        } else {
            throw new Error('Failed to fetch top volume tickers');
        }
    } catch (error) {
        console.error('Error loading top volume tickers:', error);
        // Fallback to default tickers
        loadDefaultTickers();
        showNotification('⚠️ Using default tickers (API unavailable)', 'warning');
    } finally {
        // Restore button state
        const loadButton = document.getElementById('loadTopVolume');
        loadButton.innerHTML = '<i class="fas fa-download"></i> Load Top Volume';
        loadButton.disabled = false;
    }
}

function updateSelectedTickersDisplay() {
    const container = document.getElementById('selectedTickers');
    if (appState.selectedTickers.length === 0) {
        container.innerHTML = '<i class="fas fa-info-circle"></i><span>No tickers selected</span>';
    } else {
        const displayTickers = appState.selectedTickers.slice(0, 5);
        const remaining = appState.selectedTickers.length - 5;
        let text = displayTickers.join(', ');
        if (remaining > 0) {
            text += ` +${remaining} more`;
        }
        container.innerHTML = `<i class="fas fa-check-circle"></i><span><strong>Selected:</strong> ${text}</span>`;
        
        // Add success styling
        container.style.background = 'rgba(16, 185, 129, 0.1)';
        container.style.borderColor = 'rgba(16, 185, 129, 0.3)';
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
        text.textContent = '✨ Connected';
        // Add success pulse animation
        statusElement.style.animation = 'pulse 2s infinite';
    } else {
        statusElement.className = 'connection-status disconnected';
        icon.className = 'fas fa-circle';
        text.textContent = message || '❌ Disconnected';
        statusElement.style.animation = 'none';
    }
}

async function startScan() {
    if (appState.selectedTickers.length === 0) {
        showNotification('⚠️ Please select at least one ticker', 'warning');
        return;
    }

    if (appState.selectedStrategies.length === 0) {
        showNotification('⚠️ Please select at least one strategy', 'warning');
        return;
    }

    if (appState.isScanning) {
        return;
    }

    appState.isScanning = true;
    
    // Update scan button state
    const scanButton = document.getElementById('startScan');
    scanButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
    scanButton.disabled = true;
    
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
            
            showNotification(`✅ Scan completed! Found ${results.summary?.total_signals || 0} signals`, 'success');
            
            if (appState.autoRefresh) {
                startRefreshCountdown();
            }
        } else {
            throw new Error('Scan failed');
        }
    } catch (error) {
        console.error('Scan error:', error);
        showNotification('❌ Scan failed. Please try again.', 'error');
        showWelcomeScreen();
    } finally {
        appState.isScanning = false;
        
        // Restore scan button
        const scanButton = document.getElementById('startScan');
        updateStrategySelectionCount(); // This will restore the proper button text
        scanButton.disabled = false;
    }
}

async function simulateScanProgress() {
    const progressFill = document.getElementById('progressFill');
    const loadingText = document.querySelector('.loading-text');
    const steps = [
        { progress: 15, text: 'Connecting to market data...' },
        { progress: 35, text: 'Fetching ticker information...' },
        { progress: 55, text: 'Running strategy analysis...' },
        { progress: 75, text: 'Processing signals...' },
        { progress: 90, text: 'Generating results...' },
        { progress: 100, text: 'Finalizing scan...' }
    ];
    
    for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 600));
        progressFill.style.width = steps[i].progress + '%';
        loadingText.textContent = steps[i].text;
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
            <div class="metric-icon"><i class="fas fa-signal"></i></div>
            <div class="metric-value">${totalSignals}</div>
            <div class="metric-label">Total Signals</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon"><i class="fas fa-arrow-up"></i></div>
            <div class="metric-value">${buySignals}</div>
            <div class="metric-label">Buy Signals</div>
            ${buySignals > 0 ? '<div class="metric-change positive">+' + buySignals + '</div>' : ''}
        </div>
        <div class="metric-card">
            <div class="metric-icon"><i class="fas fa-arrow-down"></i></div>
            <div class="metric-value">${sellSignals}</div>
            <div class="metric-label">Sell Signals</div>
            ${sellSignals > 0 ? '<div class="metric-change negative">-' + sellSignals + '</div>' : ''}
        </div>
        <div class="metric-card">
            <div class="metric-icon"><i class="fas fa-clock"></i></div>
            <div class="metric-value">${scanTime}</div>
            <div class="metric-label">Last Scan</div>
        </div>
    `;
    
    // Animate metric cards
    const metricCards = document.querySelectorAll('.metric-card');
    metricCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

function displayResultCards(results) {
    const resultsGrid = document.getElementById('resultsGrid');
    resultsGrid.innerHTML = '';

    if (!results.strategy_results || results.strategy_results.length === 0) {
        resultsGrid.innerHTML = `
            <div class="result-card">
                <div class="no-signals-icon">
                    <i class="fas fa-search"></i>
                </div>
                <div class="result-header">
                    <div class="result-symbol">No Signals Found</div>
                </div>
                <p>No trading signals were detected for the selected tickers and strategies. Consider:</p>
                <ul>
                    <li>Adjusting your timeframe</li>
                    <li>Selecting different strategies</li>
                    <li>Trying different tickers</li>
                    <li>Checking market hours</li>
                </ul>
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
        
        // Add entrance animation
        setTimeout(() => {
            resultCard.style.opacity = '0';
            resultCard.style.transform = 'translateY(20px)';
            resultCard.style.transition = 'all 0.6s ease';
            setTimeout(() => {
                resultCard.style.opacity = '1';
                resultCard.style.transform = 'translateY(0)';
            }, 50);
        }, 100);
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
                ${latestPrice ? `
                    <div class="price-change ${priceChange >= 0 ? 'positive' : 'negative'}">
                        <i class="fas fa-${priceChange >= 0 ? 'arrow-up' : 'arrow-down'}"></i>
                        ${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)} (${priceChangePercent.toFixed(2)}%)
                    </div>
                ` : ''}
            </div>
        </div>
        <div class="result-content">
            <div class="chart-container">
                <canvas id="chart-${symbol}"></canvas>
            </div>
            <div class="signals-panel">
                <div class="signals-header">
                    <i class="fas fa-bullseye"></i> Active Signals
                </div>
                ${createSignalsHTML(symbolResults)}
                <div class="market-data">
                    <div class="market-data-header">
                        <i class="fas fa-chart-bar"></i> Market Data
                    </div>
                    <div class="market-data-item">
                        <span class="market-data-label"><i class="fas fa-volume-up"></i> Volume:</span>
                        <span class="market-data-value">${latestPrice ? latestPrice.volume.toLocaleString() : 'N/A'}</span>
                    </div>
                    <div class="market-data-item">
                        <span class="market-data-label"><i class="fas fa-arrow-up"></i> High:</span>
                        <span class="market-data-value">$${latestPrice ? latestPrice.high.toFixed(2) : 'N/A'}</span>
                    </div>
                    <div class="market-data-item">
                        <span class="market-data-label"><i class="fas fa-arrow-down"></i> Low:</span>
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
                signalText = '<i class="fas fa-arrow-up"></i> BUY';
            } else if (signal.includes('Sell')) {
                signalClass = 'signal-sell';
                signalText = '<i class="fas fa-arrow-down"></i> SELL';
            } else {
                signalText = '<i class="fas fa-minus"></i> ' + signal;
            }
            
            signalsHTML += `
                <div class="signal-item ${signalClass}">
                    <div class="signal-text">${signalText}</div>
                    <div class="signal-strategy">${strategy}</div>
                </div>
            `;
        });
    });
    
    if (!signalsHTML) {
        signalsHTML = '<div class="signal-item signal-none"><i class="fas fa-minus"></i> No signals detected</div>';
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
                borderColor: priceChange >= 0 ? '#10b981' : '#ef4444',
                backgroundColor: priceChange >= 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: priceChange >= 0 ? '#10b981' : '#ef4444',
                pointHoverBorderColor: '#ffffff',
                pointHoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#667eea',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: false
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false,
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)',
                        maxTicksLimit: 6
                    }
                },
                y: {
                    display: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)',
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
                }
            },
            elements: {
                point: {
                    radius: 0,
                    hoverRadius: 6
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
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
        
        // Add pulsing effect when time is running low
        if (timeLeft <= 10) {
            countdownElement.style.animation = 'pulse 1s infinite';
        }
        
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

function showNotification(message, type = 'info', duration = 4000) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)}"></i>
        <span>${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 1rem;
        right: 2rem;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        border-left: 4px solid ${getNotificationColor(type)};
        display: flex;
        align-items: center;
        gap: 0.5rem;
        z-index: 1000;
        animation: slideInRight 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        max-width: 400px;
        min-width: 300px;
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease';
        }
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, duration);
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
    .slider-container {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin: 0.5rem 0;
    }
    
    .slider-value {
        background: rgba(102, 126, 234, 0.2);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        min-width: 40px;
        text-align: center;
        transition: all 0.2s ease;
        border: 1px solid rgba(102, 126, 234, 0.3);
    }
    
    .btn-ready {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4) !important;
    }
    
    .btn-ready:hover {
        box-shadow: 0 12px 35px rgba(16, 185, 129, 0.6) !important;
    }
    
    .loading-subtitle {
        color: rgba(255, 255, 255, 0.7);
        font-size: 1rem;
        margin-top: 1rem;
        text-align: center;
    }
    
    .metric-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .signal-text {
        font-weight: bold;
        font-size: 1rem;
    }
    
    .signal-strategy {
        font-size: 0.8em;
        margin-top: 0.25rem;
        opacity: 0.8;
    }
    
    .market-data-header {
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: rgba(255, 255, 255, 0.9);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .no-signals-icon {
        text-align: center;
        font-size: 3rem;
        color: rgba(255, 255, 255, 0.5);
        margin-bottom: 1rem;
    }
    
    .fab {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 1.5rem;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        cursor: pointer;
        transition: all 0.3s ease;
        z-index: 1000;
    }
    
    .fab:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(102, 126, 234, 0.6);
    }
    
    .notification-close {
        background: none;
        border: none;
        color: inherit;
        cursor: pointer;
        padding: 0.25rem;
        margin-left: auto;
        opacity: 0.7;
        transition: opacity 0.2s ease;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
    
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    @media (max-width: 768px) {
        .notification {
            top: 1rem !important;
            right: 1rem !important;
            left: 1rem !important;
            max-width: none !important;
            min-width: auto !important;
        }
        
        .fab {
            bottom: 1rem;
            right: 1rem;
        }
    }
`;
document.head.appendChild(style);