#!/usr/bin/env python
# Simple Web Dashboard for Trading System
import os
import json
import glob
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, send_file, jsonify
from io import BytesIO
import base64
import threading
import time

# Initialize Flask app
app = Flask(__name__)

# Dashboard data caching
cache = {
    'last_update': None,
    'system_status': 'Unknown',
    'data_sources': [],
    'signals': [],
    'performance': {},
    'charts': {},
    'update_in_progress': False
}

# Ensure necessary directories exist
def ensure_directories():
    dirs = ['data', 'data/signals', 'data/historical', 'data/analysis', 
            'data/backtests', 'logs', 'reports', 'templates', 'static']
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)

# Create template folder and HTML files
def create_template_files():
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
        
    # Create base template
    with open('templates/base.html', 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Trading System Dashboard{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin-top: 20px;
            background-color: #f5f5f5;
        }
        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .card {
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border: none;
        }
        .card-header {
            font-weight: bold;
            background-color: #f8f9fa;
            border-radius: 10px 10px 0 0 !important;
        }
        .system-status {
            padding: 10px 15px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
        }
        .status-ok {
            background-color: #d4edda;
            color: #155724;
        }
        .status-warning {
            background-color: #fff3cd;
            color: #856404;
        }
        .status-error {
            background-color: #f8d7da;
            color: #721c24;
        }
        .signal-buy {
            color: #28a745;
            font-weight: bold;
        }
        .signal-sell {
            color: #dc3545;
            font-weight: bold;
        }
        .chart-container {
            width: 100%;
            height: 400px;
            overflow: hidden;
        }
        .refresh-button {
            float: right;
            margin-top: -5px;
        }
        .last-update {
            font-size: 12px;
            color: #6c757d;
        }
    </style>
    {% block head %}{% endblock %}
</head>
<body>
    <div class="dashboard-container">
        <div class="row mb-4">
            <div class="col">
                <h1 class="display-5">Trading System Dashboard</h1>
                <p class="text-muted">
                    Last updated: <span id="last-update">{{ last_update }}</span>
                    <button id="refresh-dashboard" class="btn btn-sm btn-primary ms-3">
                        <i class="bi bi-arrow-clockwise"></i> Refresh
                    </button>
                </p>
            </div>
        </div>
        
        {% block content %}{% endblock %}
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        document.getElementById('refresh-dashboard').addEventListener('click', function() {
            location.reload();
        });
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>''')
    
    # Create index template
    with open('templates/index.html', 'w') as f:
        f.write('''{% extends "base.html" %}

{% block content %}
<div class="row">
    <!-- System Status -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                System Status
            </div>
            <div class="card-body">
                <h5>Current Status: 
                    <span class="system-status {% if system_status == 'OK' %}status-ok{% elif system_status == 'Warning' %}status-warning{% else %}status-error{% endif %}">
                        {{ system_status }}
                    </span>
                </h5>
                <div class="mt-4">
                    <h6>Data Sources:</h6>
                    <ul class="list-group">
                        {% for source in data_sources %}
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            {{ source.name }}
                            {% if source.status == 'OK' %}
                            <span class="badge bg-success rounded-pill">Connected</span>
                            {% else %}
                            <span class="badge bg-danger rounded-pill">Disconnected</span>
                            {% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Recent Signals -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                Recent Trading Signals
            </div>
            <div class="card-body">
                {% if signals %}
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Symbol</th>
                                <th>Signal</th>
                                <th>Price</th>
                                <th>Confidence</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for signal in signals %}
                            <tr>
                                <td>{{ signal.date }}</td>
                                <td>{{ signal.symbol }}</td>
                                <td class="{% if signal.action == 'BUY' or signal.action == 'BUY_TO_OPEN' %}signal-buy{% elif signal.action == 'SELL' or signal.action == 'SELL_TO_OPEN' %}signal-sell{% endif %}">
                                    {{ signal.action }}
                                </td>
                                <td>${{ signal.price }}</td>
                                <td>{{ signal.confidence }}%</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <p class="text-center">No recent signals available</p>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<div class="row">
    <!-- Performance Charts -->
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                Performance Overview
            </div>
            <div class="card-body">
                <div class="row">
                    {% if performance %}
                    <div class="col-md-4">
                        <div class="card mb-3">
                            <div class="card-body text-center">
                                <h3 class="card-title">Overall Return</h3>
                                <p class="display-5 {% if performance.total_return > 0 %}text-success{% else %}text-danger{% endif %}">
                                    {{ performance.total_return }}%
                                </p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card mb-3">
                            <div class="card-body text-center">
                                <h3 class="card-title">Sharpe Ratio</h3>
                                <p class="display-5 {% if performance.sharpe > 1 %}text-success{% else %}text-warning{% endif %}">
                                    {{ performance.sharpe }}
                                </p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card mb-3">
                            <div class="card-body text-center">
                                <h3 class="card-title">Win Rate</h3>
                                <p class="display-5 {% if performance.win_rate > 50 %}text-success{% else %}text-warning{% endif %}">
                                    {{ performance.win_rate }}%
                                </p>
                            </div>
                        </div>
                    </div>
                    {% else %}
                    <div class="col-12">
                        <p class="text-center">No performance data available</p>
                    </div>
                    {% endif %}
                </div>
                
                <!-- Performance Charts -->
                <div class="row mt-4">
                    {% if charts %}
                    {% for symbol, chart_img in charts.items() %}
                    <div class="col-md-6 mb-3">
                        <h5>{{ symbol }} Performance</h5>
                        <div class="chart-container">
                            <img src="data:image/png;base64,{{ chart_img }}" class="img-fluid" alt="{{ symbol }} chart">
                        </div>
                    </div>
                    {% endfor %}
                    {% else %}
                    <div class="col-12">
                        <p class="text-center">No charts available</p>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <!-- System Logs -->
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                Recent System Logs
            </div>
            <div class="card-body">
                <div class="log-container p-3 bg-light" style="max-height: 300px; overflow-y: auto; font-family: monospace;">
                    {% for log in logs %}
                    <div class="log-entry {% if 'error' in log.lower() or 'failed' in log.lower() %}text-danger{% elif 'warning' in log.lower() %}text-warning{% endif %}">
                        {{ log }}
                    </div>
                    {% else %}
                    <p class="text-center">No logs available</p>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}''')

# Background update thread
def background_updater():
    while True:
        try:
            update_dashboard_data()
        except Exception as e:
            print(f"Error in background updater: {e}")
        time.sleep(300)  # Update every 5 minutes

# Update dashboard data
def update_dashboard_data():
    if cache['update_in_progress']:
        return
    
    cache['update_in_progress'] = True
    try:
        # Update system status
        cache['last_update'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check data source status
        data_sources = []
        
        # Google Finance status
        try:
            # Try to run a simple check command - redirect stderr to stdout
            check_output = os.popen("python -c \"from googlefinance import getQuotes; quotes = getQuotes('AAPL'); print('OK' if quotes else 'ERROR')\" 2>&1").read()
            if 'OK' in check_output:
                data_sources.append({"name": "Google Finance", "status": "OK"})
            else:
                data_sources.append({"name": "Google Finance", "status": "ERROR"})
        except:
            data_sources.append({"name": "Google Finance", "status": "ERROR"})
        
        # Yahoo Finance status (fallback)
        try:
            # Try to run a simple check command
            check_output = os.popen("python -c \"import yfinance as yf; data = yf.download('AAPL', period='1d', progress=False); print('OK' if not data.empty else 'ERROR')\" 2>&1").read()
            if 'OK' in check_output:
                data_sources.append({"name": "Yahoo Finance", "status": "OK"})
            else:
                data_sources.append({"name": "Yahoo Finance", "status": "ERROR"})
        except:
            data_sources.append({"name": "Yahoo Finance", "status": "ERROR"})
        
        cache['data_sources'] = data_sources
        
        # Determine overall system status
        if all(source['status'] == 'OK' for source in data_sources):
            cache['system_status'] = 'OK'
        elif any(source['status'] == 'OK' for source in data_sources):
            cache['system_status'] = 'Warning'
        else:
            cache['system_status'] = 'Error'
        
        # Collect latest signals
        signals = []
        signal_files = glob.glob('data/signals/*_signals_*.json')
        for signal_file in sorted(signal_files, reverse=True)[:5]:  # Latest 5 signal files
            try:
                with open(signal_file, 'r') as f:
                    file_signals = json.load(f)
                    if isinstance(file_signals, list):
                        signals.extend(file_signals)
                    else:
                        signals.append(file_signals)
            except Exception as e:
                print(f"Error loading signal file {signal_file}: {e}")
        
        # Sort by date (most recent first) and take top 10
        signals = sorted(signals, key=lambda s: s.get('date', ''), reverse=True)[:10]
        cache['signals'] = signals
        
        # Collect performance metrics
        performance = {}
        backtest_files = glob.glob('data/backtests/*_backtest_results_*.csv')
        if backtest_files:
            latest_backtest = sorted(backtest_files, reverse=True)[0]
            try:
                results = pd.read_csv(latest_backtest)
                
                # Calculate key metrics
                if not results.empty:
                    # Overall return
                    initial_value = results['Total_Value'].iloc[0]
                    final_value = results['Total_Value'].iloc[-1]
                    total_return = round((final_value - initial_value) / initial_value * 100, 2)
                    
                    # Sharpe ratio
                    if 'Returns' in results.columns:
                        daily_returns = results['Returns'].dropna()
                        sharpe = round(np.sqrt(252) * daily_returns.mean() / daily_returns.std(), 2) if daily_returns.std() > 0 else 0
                    else:
                        sharpe = 0
                    
                    # Win rate - see if we have a trades file
                    win_rate = 0
                    trades_file = latest_backtest.replace('_results_', '_trades_')
                    if os.path.exists(trades_file):
                        trades = pd.read_csv(trades_file)
                        if not trades.empty:
                            wins = 0
                            trades_count = 0
                            for i, trade in trades.iterrows():
                                if trade['action'] in ['SELL', 'COVER']:
                                    trades_count += 1
                                    if ('value' in trades.columns and trade['value'] > 0) or \
                                       ('profit' in trades.columns and trade['profit'] > 0):
                                        wins += 1
                            
                            win_rate = round((wins / trades_count) * 100, 2) if trades_count > 0 else 0
                    
                    performance = {
                        'total_return': total_return,
                        'sharpe': sharpe,
                        'win_rate': win_rate
                    }
            except Exception as e:
                print(f"Error processing backtest file {latest_backtest}: {e}")
        
        cache['performance'] = performance
        
        # Generate or load charts
        charts = {}
        backtest_charts = glob.glob('data/backtests/*_backtest_*.png')
        if backtest_charts:
            # Get latest chart for each symbol
            symbols = set()
            for chart_file in backtest_charts:
                symbol = os.path.basename(chart_file).split('_')[0]
                symbols.add(symbol)
            
            for symbol in symbols:
                symbol_charts = [f for f in backtest_charts if os.path.basename(f).startswith(f"{symbol}_")]
                if symbol_charts:
                    latest_chart = sorted(symbol_charts, reverse=True)[0]
                    with open(latest_chart, 'rb') as f:
                        img_data = f.read()
                        charts[symbol] = base64.b64encode(img_data).decode('utf-8')
        
        cache['charts'] = charts
    
    except Exception as e:
        print(f"Error updating dashboard data: {e}")
    
    finally:
        cache['update_in_progress'] = False

# Route for dashboard home page
@app.route('/')
def index():
    # Update cache if needed
    if cache['last_update'] is None:
        update_dashboard_data()
    
    # Get recent logs
    logs = []
    log_files = glob.glob('logs/*.log')
    if log_files:
        latest_log = sorted(log_files, reverse=True)[0]
        try:
            with open(latest_log, 'r') as f:
                # Get last 50 lines
                logs = f.readlines()[-50:]
        except Exception as e:
            logs = [f"Error reading log file: {e}"]
    
    return render_template('index.html',
                          last_update=cache['last_update'],
                          system_status=cache['system_status'],
                          data_sources=cache['data_sources'],
                          signals=cache['signals'],
                          performance=cache['performance'],
                          charts=cache['charts'],
                          logs=logs)

# API route for getting latest data
@app.route('/api/refresh-data')
def refresh_data():
    update_dashboard_data()
    return jsonify({'status': 'ok', 'last_update': cache['last_update']})

# Run Flask app
if __name__ == '__main__':
    # Setup
    ensure_directories()
    create_template_files()
    
    # Start background updater thread
    updater_thread = threading.Thread(target=background_updater, daemon=True)
    updater_thread.start()
    
    # Start Flask server
    app.run(debug=True, host='0.0.0.0', port=5000) 