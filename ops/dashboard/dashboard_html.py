# path: ops/dashboard/dashboard_html.py
"""Enhanced trading dashboard HTML template."""

def get_dashboard_html() -> str:
    """Generate the trading dashboard HTML with real-time visualization."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WolfeDesk Trading Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }
        
        .logo {
            font-size: 28px;
            font-weight: bold;
            background: linear-gradient(45deg, #00ff88, #00bbff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .status-bar {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .status-chip {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-chip.connected {
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        
        .status-chip.disconnected {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .status-chip.mode-live {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .status-chip.mode-shadow {
            background: rgba(251, 191, 36, 0.2);
            color: #fbbf24;
            border: 1px solid rgba(251, 191, 36, 0.3);
        }
        
        .status-chip.mode-dry {
            background: rgba(59, 130, 246, 0.2);
            color: #3b82f6;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }
        
        .pulse {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .card-title {
            font-size: 14px;
            font-weight: 600;
            color: #9ca3af;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .stat-item {
            background: rgba(255,255,255,0.03);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.05);
        }
        
        .stat-label {
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #fff;
        }
        
        .positions-table {
            width: 100%;
            margin-top: 10px;
        }
        
        .positions-table th {
            text-align: left;
            padding: 10px;
            font-size: 12px;
            color: #6b7280;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .positions-table td {
            padding: 12px 10px;
            font-size: 14px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .position-row:hover {
            background: rgba(255,255,255,0.03);
        }
        
        .side-buy {
            color: #22c55e;
            font-weight: 600;
        }
        
        .side-sell {
            color: #ef4444;
            font-weight: 600;
        }
        
        .profit-positive {
            color: #22c55e;
        }
        
        .profit-negative {
            color: #ef4444;
        }
        
        .trade-feed {
            max-height: 400px;
            overflow-y: auto;
            padding-right: 10px;
        }
        
        .trade-feed::-webkit-scrollbar {
            width: 6px;
        }
        
        .trade-feed::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.05);
            border-radius: 3px;
        }
        
        .trade-feed::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
        }
        
        .trade-item {
            padding: 12px;
            margin-bottom: 10px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            border-left: 3px solid #3b82f6;
            display: flex;
            justify-content: space-between;
            align-items: center;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .trade-item.buy {
            border-left-color: #22c55e;
        }
        
        .trade-item.sell {
            border-left-color: #ef4444;
        }
        
        .trade-info {
            flex: 1;
        }
        
        .trade-symbol {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 4px;
        }
        
        .trade-details {
            font-size: 12px;
            color: #9ca3af;
        }
        
        .trade-time {
            font-size: 11px;
            color: #6b7280;
        }
        
        .watchlist-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        
        .symbol-chip {
            padding: 8px;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 6px;
            text-align: center;
            font-size: 12px;
            font-weight: 600;
            color: #3b82f6;
            transition: all 0.2s;
        }
        
        .symbol-chip.active {
            background: rgba(34, 197, 94, 0.1);
            border-color: rgba(34, 197, 94, 0.3);
            color: #22c55e;
        }
        
        .symbol-chip:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        .chart-container {
            height: 300px;
            position: relative;
            margin-top: 20px;
        }
        
        .activity-chart {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: flex-end;
            justify-content: space-around;
            padding: 20px 10px;
        }
        
        .activity-bar {
            width: 20px;
            background: linear-gradient(to top, #3b82f6, #60a5fa);
            border-radius: 4px 4px 0 0;
            transition: height 0.3s ease;
            position: relative;
        }
        
        .activity-bar:hover::after {
            content: attr(data-value);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            white-space: nowrap;
            margin-bottom: 5px;
        }
        
        .full-width {
            grid-column: 1 / -1;
        }
        
        .two-thirds {
            grid-column: span 2;
        }
        
        .alert-banner {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 12px 20px;
            margin-bottom: 20px;
            display: none;
            align-items: center;
            gap: 10px;
        }
        
        .alert-banner.show {
            display: flex;
        }
        
        .alert-icon {
            font-size: 20px;
        }
        
        .alert-text {
            flex: 1;
            font-size: 14px;
        }
        
        .btn {
            padding: 8px 16px;
            border-radius: 6px;
            border: none;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn-danger {
            background: #ef4444;
            color: white;
        }
        
        .btn-danger:hover {
            background: #dc2626;
        }
        
        .loading {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">WolfeDesk Trading</div>
            <div class="status-bar">
                <div id="connectionStatus" class="status-chip disconnected">
                    <span class="pulse"></span>
                    <span id="connectionText">Connecting...</span>
                </div>
                <div id="modeStatus" class="status-chip mode-dry">
                    <span id="modeText">DRY_RUN</span>
                </div>
                <div id="haStatus" class="status-chip">
                    <span id="haText">HA: OFF</span>
                </div>
            </div>
        </div>
        
        <div id="alertBanner" class="alert-banner">
            <span class="alert-icon">⚠️</span>
            <span class="alert-text" id="alertText"></span>
        </div>
        
        <div class="dashboard-grid">
            <!-- Trading Stats -->
            <div class="card">
                <div class="card-title">Trading Statistics</div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Trades Today</div>
                        <div class="stat-value" id="tradesToday">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Daily DD Limit</div>
                        <div class="stat-value" id="ddLimit">4.0%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Order Rate</div>
                        <div class="stat-value" id="orderRate">0/min</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Risk Mode</div>
                        <div class="stat-value" id="riskMode">-</div>
                    </div>
                </div>
            </div>
            
            <!-- Open Positions -->
            <div class="card two-thirds">
                <div class="card-title">Open Positions</div>
                <div id="positionsContainer">
                    <table class="positions-table">
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Side</th>
                                <th>Volume</th>
                                <th>Ticket</th>
                                <th>P&L</th>
                            </tr>
                        </thead>
                        <tbody id="positionsBody">
                            <tr>
                                <td colspan="5" style="text-align: center; color: #6b7280;">No open positions</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Trade Feed -->
            <div class="card full-width">
                <div class="card-title">Recent Trades</div>
                <div class="trade-feed" id="tradeFeed">
                    <div style="text-align: center; color: #6b7280; padding: 40px;">
                        Waiting for trades...
                    </div>
                </div>
            </div>
            
            <!-- Watchlist -->
            <div class="card">
                <div class="card-title">Watchlist (<span id="watchlistCount">0</span>)</div>
                <div class="watchlist-grid" id="watchlistGrid">
                    <div style="color: #6b7280;">Loading...</div>
                </div>
            </div>
            
            <!-- Activity Chart -->
            <div class="card two-thirds">
                <div class="card-title">Trading Activity (Last 24h)</div>
                <div class="chart-container">
                    <div class="activity-chart" id="activityChart">
                        <!-- Activity bars will be inserted here -->
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Configuration
        const API_BASE = '';
        const REFRESH_INTERVAL = 2000; // 2 seconds
        const AUTH_TOKEN = ''; // Add token if needed
        
        // State
        let lastTradeTimestamp = null;
        let tradeCount = 0;
        
        // Helper function for API calls
        async function apiCall(endpoint) {
            const headers = {};
            if (AUTH_TOKEN) {
                headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
            }
            
            try {
                const response = await fetch(API_BASE + endpoint, { headers });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return await response.json();
            } catch (error) {
                console.error(`API call failed: ${endpoint}`, error);
                return null;
            }
        }
        
        // Update connection status
        async function updateConnectionStatus() {
            const status = await apiCall('/adapter/mt5/status');
            const connectionStatus = document.getElementById('connectionStatus');
            const connectionText = document.getElementById('connectionText');
            
            if (status && status.connected) {
                connectionStatus.className = 'status-chip connected';
                connectionText.textContent = `Connected: ${status.server}`;
            } else {
                connectionStatus.className = 'status-chip disconnected';
                connectionText.textContent = 'Disconnected';
            }
        }
        
        // Update HA status
        async function updateHAStatus() {
            const status = await apiCall('/ha/status');
            const haStatus = document.getElementById('haStatus');
            const haText = document.getElementById('haText');
            
            if (status) {
                if (status.running) {
                    haStatus.className = status.leader ? 'status-chip connected' : 'status-chip mode-shadow';
                    haText.textContent = `HA: ${status.leader ? 'LEADER' : 'FOLLOWER'}`;
                } else {
                    haStatus.className = 'status-chip';
                    haText.textContent = 'HA: OFF';
                }
            }
        }
        
        // Update trading stats
        async function updateStats() {
            const stats = await apiCall('/trades/stats');
            if (stats) {
                document.getElementById('tradesToday').textContent = stats.total_trades_today || '0';
                document.getElementById('ddLimit').textContent = stats.daily_dd_limit || '-';
                document.getElementById('orderRate').textContent = stats.order_rate_cap || '-';
                document.getElementById('riskMode').textContent = stats.risk_mode || '-';
                
                // Update mode status
                const modeStatus = document.getElementById('modeStatus');
                const modeText = document.getElementById('modeText');
                const mode = stats.mode || 'UNKNOWN';
                
                modeText.textContent = mode;
                if (mode === 'LIVE') {
                    modeStatus.className = 'status-chip mode-live';
                } else if (mode === 'SHADOW') {
                    modeStatus.className = 'status-chip mode-shadow';
                } else {
                    modeStatus.className = 'status-chip mode-dry';
                }
            }
        }
        
        // Update positions
        async function updatePositions() {
            const data = await apiCall('/trades/positions');
            const tbody = document.getElementById('positionsBody');
            
            if (data && data.positions && data.positions.length > 0) {
                tbody.innerHTML = data.positions.map(pos => `
                    <tr class="position-row">
                        <td style="font-weight: 600;">${pos.symbol}</td>
                        <td class="${pos.side === 'BUY' ? 'side-buy' : 'side-sell'}">${pos.side}</td>
                        <td>${pos.volume.toFixed(2)}</td>
                        <td>${pos.ticket || '-'}</td>
                        <td class="${pos.profit >= 0 ? 'profit-positive' : 'profit-negative'}">
                            ${pos.profit >= 0 ? '+' : ''}${pos.profit.toFixed(2)}
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #6b7280;">No open positions</td></tr>';
            }
        }
        
        // Update trade feed
        async function updateTradeFeed() {
            const data = await apiCall('/trades/feed?limit=20');
            const feedContainer = document.getElementById('tradeFeed');
            
            if (data && data.trades && data.trades.length > 0) {
                const tradesHtml = data.trades.map(trade => {
                    const timestamp = new Date(trade.timestamp).toLocaleTimeString();
                    const sideClass = trade.side === 'BUY' ? 'buy' : trade.side === 'SELL' ? 'sell' : '';
                    
                    return `
                        <div class="trade-item ${sideClass}">
                            <div class="trade-info">
                                <div class="trade-symbol">${trade.symbol || trade.action || 'Trade'}</div>
                                <div class="trade-details">
                                    ${trade.side || ''} ${trade.qty ? trade.qty.toFixed(2) : ''} 
                                    ${trade.mode ? `[${trade.mode}]` : ''}
                                </div>
                            </div>
                            <div class="trade-time">${timestamp}</div>
                        </div>
                    `;
                }).join('');
                
                feedContainer.innerHTML = tradesHtml;
                
                // Check for new trades and show alert
                if (data.trades[0] && data.trades[0].timestamp !== lastTradeTimestamp) {
                    lastTradeTimestamp = data.trades[0].timestamp;
                    tradeCount++;
                    
                    // Flash animation for new trade
                    const firstItem = feedContainer.querySelector('.trade-item');
                    if (firstItem) {
                        firstItem.style.animation = 'none';
                        setTimeout(() => {
                            firstItem.style.animation = 'slideIn 0.3s ease-out';
                        }, 10);
                    }
                }
            } else {
                feedContainer.innerHTML = '<div style="text-align: center; color: #6b7280; padding: 40px;">No recent trades</div>';
            }
        }
        
        // Update watchlist
        async function updateWatchlist() {
            const data = await apiCall('/trades/watchlist');
            const grid = document.getElementById('watchlistGrid');
            const count = document.getElementById('watchlistCount');
            
            if (data && data.configured) {
                count.textContent = data.count || '0';
                
                if (data.configured.length > 0) {
                    grid.innerHTML = data.configured.map(symbol => {
                        const isActive = data.subscribed && data.subscribed.includes(symbol);
                        return `<div class="symbol-chip ${isActive ? 'active' : ''}">${symbol}</div>`;
                    }).join('');
                } else {
                    grid.innerHTML = '<div style="color: #6b7280;">No symbols in watchlist</div>';
                }
            }
        }
        
        // Generate activity chart
        function generateActivityChart() {
            const chart = document.getElementById('activityChart');
            const hours = 24;
            const bars = [];
            
            for (let i = 0; i < hours; i++) {
                const value = Math.floor(Math.random() * 100);
                bars.push(`
                    <div class="activity-bar" 
                         style="height: ${value}%"
                         data-value="${value} trades">
                    </div>
                `);
            }
            
            chart.innerHTML = bars.join('');
        }
        
        // Main update function
        async function updateDashboard() {
            await Promise.all([
                updateConnectionStatus(),
                updateHAStatus(),
                updateStats(),
                updatePositions(),
                updateTradeFeed(),
                updateWatchlist()
            ]);
        }
        
        // Initialize dashboard
        async function init() {
            // Initial load
            await updateDashboard();
            generateActivityChart();
            
            // Set up periodic updates
            setInterval(updateDashboard, REFRESH_INTERVAL);
            
            // Update activity chart every minute
            setInterval(generateActivityChart, 60000);
        }
        
        // Start the dashboard
        init();
    </script>
</body>
</html>
"""