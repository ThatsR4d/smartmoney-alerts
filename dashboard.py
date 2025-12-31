#!/usr/bin/env python3
"""
SmartMoneyAlerts Dashboard - Simple Web GUI
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, jsonify, request
from core.database import get_connection, get_stats_summary
from datetime import datetime

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SmartMoney Alerts Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #58a6ff; margin-bottom: 20px; }
        h2 { color: #8b949e; font-size: 14px; text-transform: uppercase; margin: 20px 0 10px; }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .stat-value { font-size: 28px; font-weight: bold; color: #58a6ff; }
        .stat-label { font-size: 12px; color: #8b949e; margin-top: 5px; }

        .trades-table {
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border-radius: 8px;
            overflow: hidden;
        }
        .trades-table th, .trades-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #30363d;
        }
        .trades-table th {
            background: #21262d;
            color: #8b949e;
            font-size: 12px;
            text-transform: uppercase;
        }
        .trades-table tr:hover { background: #1f2428; }

        .ticker { color: #58a6ff; font-weight: bold; }
        .buy { color: #3fb950; }
        .sell { color: #f85149; }
        .score {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        .tier1 { background: #238636; color: white; }
        .tier2 { background: #1f6feb; color: white; }
        .tier3 { background: #6e7681; color: white; }

        .posted { color: #3fb950; }
        .pending { color: #d29922; }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #c9d1d9;
            cursor: pointer;
            text-decoration: none;
        }
        .tab:hover, .tab.active { background: #30363d; color: #58a6ff; }

        .refresh-btn {
            background: #238636;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover { background: #2ea043; }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .last-update { color: #8b949e; font-size: 12px; }

        .value-large { font-size: 13px; }

        @media (max-width: 600px) {
            .trades-table { font-size: 12px; }
            .trades-table th, .trades-table td { padding: 8px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SmartMoney Alerts</h1>
            <div>
                <span class="last-update">Last update: <span id="update-time">-</span></span>
                <button class="refresh-btn" onclick="refresh()">Refresh</button>
            </div>
        </div>

        <h2>Database Stats</h2>
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card"><div class="stat-value">-</div><div class="stat-label">Loading...</div></div>
        </div>

        <div class="tabs">
            <a href="#" class="tab active" onclick="showTab('insider')">Insider Trades</a>
            <a href="#" class="tab" onclick="showTab('congress')">Congress</a>
            <a href="#" class="tab" onclick="showTab('13f')">13F Filings</a>
        </div>

        <div id="insider-tab">
            <h2>Recent Insider Trades</h2>
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Role</th>
                        <th>Type</th>
                        <th>Value</th>
                        <th>Score</th>
                        <th>Posted</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody id="insider-tbody">
                    <tr><td colspan="7">Loading...</td></tr>
                </tbody>
            </table>
        </div>

        <div id="congress-tab" style="display:none">
            <h2>Congressional Trades</h2>
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Politician</th>
                        <th>Party</th>
                        <th>Ticker</th>
                        <th>Type</th>
                        <th>Amount</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody id="congress-tbody">
                    <tr><td colspan="6">Loading...</td></tr>
                </tbody>
            </table>
        </div>

        <div id="13f-tab" style="display:none">
            <h2>Hedge Fund 13F Filings</h2>
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Fund Name</th>
                        <th>Manager</th>
                        <th>Positions</th>
                        <th>Total Value</th>
                        <th>Filing Date</th>
                    </tr>
                </thead>
                <tbody id="13f-tbody">
                    <tr><td colspan="5">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function formatValue(val) {
            if (!val) return '-';
            if (val >= 1e9) return '$' + (val/1e9).toFixed(1) + 'B';
            if (val >= 1e6) return '$' + (val/1e6).toFixed(1) + 'M';
            if (val >= 1e3) return '$' + (val/1e3).toFixed(0) + 'K';
            return '$' + val.toFixed(0);
        }

        function getTierClass(score) {
            if (score >= 70) return 'tier1';
            if (score >= 50) return 'tier2';
            return 'tier3';
        }

        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('insider-tab').style.display = tab === 'insider' ? 'block' : 'none';
            document.getElementById('congress-tab').style.display = tab === 'congress' ? 'block' : 'none';
            document.getElementById('13f-tab').style.display = tab === '13f' ? 'block' : 'none';
        }

        async function loadStats() {
            const res = await fetch('/api/stats');
            const data = await res.json();
            const grid = document.getElementById('stats-grid');
            grid.innerHTML = `
                <div class="stat-card"><div class="stat-value">${data.total_trades}</div><div class="stat-label">Total Trades</div></div>
                <div class="stat-card"><div class="stat-value">${data.total_purchases}</div><div class="stat-label">Purchases</div></div>
                <div class="stat-card"><div class="stat-value">${data.twitter_posted}</div><div class="stat-label">Posted to X</div></div>
                <div class="stat-card"><div class="stat-value">${data.today_trades}</div><div class="stat-label">Today</div></div>
                <div class="stat-card"><div class="stat-value">${data.avg_virality_score}</div><div class="stat-label">Avg Score</div></div>
                <div class="stat-card"><div class="stat-value">${data.congress_trades || 0}</div><div class="stat-label">Congress</div></div>
                <div class="stat-card"><div class="stat-value">${data.hedge_fund_filings || 0}</div><div class="stat-label">13F Filings</div></div>
            `;
        }

        async function loadInsiderTrades() {
            const res = await fetch('/api/trades/insider');
            const trades = await res.json();
            const tbody = document.getElementById('insider-tbody');
            if (trades.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7">No trades found</td></tr>';
                return;
            }
            tbody.innerHTML = trades.map(t => `
                <tr>
                    <td class="ticker">$${t.ticker || 'N/A'}</td>
                    <td>${t.insider_role || '-'}</td>
                    <td class="${t.transaction_type === 'P' ? 'buy' : 'sell'}">${t.transaction_type === 'P' ? 'BUY' : 'SELL'}</td>
                    <td class="value-large">${formatValue(t.total_value)}</td>
                    <td><span class="score ${getTierClass(t.virality_score)}">${t.virality_score}</span></td>
                    <td class="${t.twitter_posted ? 'posted' : 'pending'}">${t.twitter_posted ? 'Yes' : 'No'}</td>
                    <td>${t.filing_date || '-'}</td>
                </tr>
            `).join('');
        }

        async function loadCongressTrades() {
            const res = await fetch('/api/trades/congress');
            const trades = await res.json();
            const tbody = document.getElementById('congress-tbody');
            if (trades.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">No trades found</td></tr>';
                return;
            }
            tbody.innerHTML = trades.map(t => `
                <tr>
                    <td>${t.politician_name || '-'}</td>
                    <td>${t.politician_party || '-'}</td>
                    <td class="ticker">$${t.ticker || 'N/A'}</td>
                    <td class="${t.transaction_type === 'purchase' ? 'buy' : 'sell'}">${t.transaction_type || '-'}</td>
                    <td>${t.amount_range || '-'}</td>
                    <td>${t.transaction_date || '-'}</td>
                </tr>
            `).join('');
        }

        async function load13fFilings() {
            const res = await fetch('/api/trades/13f');
            const filings = await res.json();
            const tbody = document.getElementById('13f-tbody');
            if (filings.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No filings found</td></tr>';
                return;
            }
            tbody.innerHTML = filings.map(f => `
                <tr>
                    <td>${f.fund_name || '-'}</td>
                    <td>${f.manager_name || '-'}</td>
                    <td>${f.position_count || 0}</td>
                    <td>${formatValue(f.total_value)}</td>
                    <td>${f.filing_date || '-'}</td>
                </tr>
            `).join('');
        }

        function refresh() {
            loadStats();
            loadInsiderTrades();
            loadCongressTrades();
            load13fFilings();
            document.getElementById('update-time').textContent = new Date().toLocaleTimeString();
        }

        refresh();
        setInterval(refresh, 60000); // Auto-refresh every minute
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/stats')
def api_stats():
    stats = get_stats_summary()

    # Add congress and 13f counts
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM congress_trades")
    stats['congress_trades'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM hedge_fund_filings")
    stats['hedge_fund_filings'] = cursor.fetchone()[0]

    conn.close()
    return jsonify(stats)

@app.route('/api/trades/insider')
def api_insider_trades():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticker, insider_role, transaction_type, total_value,
               virality_score, twitter_posted, filing_date
        FROM insider_trades
        ORDER BY id DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/trades/congress')
def api_congress_trades():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT politician_name, politician_party, ticker, transaction_type,
               amount_range, transaction_date
        FROM congress_trades
        ORDER BY id DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/trades/13f')
def api_13f_filings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fund_name, manager_name, position_count, total_value, filing_date
        FROM hedge_fund_filings
        ORDER BY id DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

if __name__ == '__main__':
    print("Starting SmartMoney Dashboard...")
    print("Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=True)
