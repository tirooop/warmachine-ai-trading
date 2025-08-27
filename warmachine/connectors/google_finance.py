#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Finance数据获取模块
提供实时股票数据、历史数据和期权数据获取功能
"""

import requests
import pandas as pd
import yfinance as yf  # 作为备选数据源
import time
from datetime import datetime, timedelta
import json
import os
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/google_finance_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GoogleFinance")

class GoogleFinanceAPI:
    """Google Finance数据获取类"""
    
    def __init__(self, cache_dir="data/cache"):
        """初始化Google Finance API客户端
        
        Args:
            cache_dir: 数据缓存目录
        """
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        
        self.session = requests.Session()
        # 设置请求头，模拟浏览器访问
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml'
        })
        logger.info("GoogleFinanceAPI 初始化完成")
    
    def get_real_time_quotes(self, symbols):
        """获取实时股票报价
        
        Args:
            symbols: 股票代码列表或单个代码
            
        Returns:
            包含实时报价数据的字典或DataFrame
        """
        if isinstance(symbols, str):
            symbols = [symbols]
            
        logger.info(f"获取实时报价: {symbols}")
        
        try:
            # 通过Yahoo Finance API获取数据（作为替代，因为Google API不稳定）
            data = yf.download(symbols, period="1d", interval="1m", group_by="ticker", progress=False)
            
            if len(symbols) == 1:
                # 单个股票情况，返回最新一行数据
                latest = data.iloc[-1].to_dict()
                return {
                    "symbol": symbols[0],
                    "price": latest.get("Close", None),
                    "change": latest.get("Close", 0) - latest.get("Open", 0),
                    "change_percent": (latest.get("Close", 0) / latest.get("Open", 0) - 1) * 100 if latest.get("Open", 0) else 0,
                    "volume": latest.get("Volume", 0),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "Yahoo Finance (Google Finance替代)"
                }
            else:
                # 多个股票情况
                result = {}
                for symbol in symbols:
                    if symbol in data.columns.levels[0]:
                        symbol_data = data[symbol].iloc[-1].to_dict()
                        result[symbol] = {
                            "price": symbol_data.get("Close", None),
                            "change": symbol_data.get("Close", 0) - symbol_data.get("Open", 0),
                            "change_percent": (symbol_data.get("Close", 0) / symbol_data.get("Open", 0) - 1) * 100 if symbol_data.get("Open", 0) else 0,
                            "volume": symbol_data.get("Volume", 0),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "source": "Yahoo Finance (Google Finance替代)"
                        }
                return result
                
        except Exception as e:
            logger.error(f"获取实时报价失败: {e}")
            return None
    
    def get_historical_data(self, symbol, period="1y", interval="1d"):
        """获取历史价格数据
        
        Args:
            symbol: 股票代码
            period: 时间范围，可选 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            interval: 时间间隔，可选 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
            
        Returns:
            包含历史价格数据的DataFrame
        """
        cache_file = os.path.join(self.cache_dir, f"{symbol}_{period}_{interval}_{datetime.now().strftime('%Y%m%d')}.csv")
        
        # 检查是否有当日缓存
        if os.path.exists(cache_file):
            logger.info(f"从缓存加载历史数据: {cache_file}")
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        logger.info(f"获取历史数据: {symbol}, 周期: {period}, 间隔: {interval}")
        
        try:
            # 使用yfinance作为替代数据源
            data = yf.download(symbol, period=period, interval=interval, progress=False)
            
            # 保存到缓存
            data.to_csv(cache_file)
            
            return data
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return None
    
    def get_options_chain(self, symbol):
        """获取期权链数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含看涨和看跌期权数据的字典
        """
        logger.info(f"获取期权链数据: {symbol}")
        
        try:
            # 使用yfinance获取期权数据
            stock = yf.Ticker(symbol)
            options = stock.options
            
            if not options:
                logger.warning(f"{symbol} 没有可用的期权数据")
                return None
            
            result = {}
            for expiry in options:
                option_chain = stock.option_chain(expiry)
                result[expiry] = {
                    "calls": option_chain.calls.to_dict('records'),
                    "puts": option_chain.puts.to_dict('records')
                }
            
            # 缓存期权数据
            cache_file = os.path.join(self.cache_dir, f"{symbol}_options_{datetime.now().strftime('%Y%m%d')}.json")
            with open(cache_file, 'w') as f:
                json.dump(result, f)
            
            return result
        except Exception as e:
            logger.error(f"获取期权链数据失败: {e}")
            return None
    
    def calculate_option_price(self, symbol, option_type, strike, expiry, method="black_scholes"):
        """计算期权理论价格
        
        Args:
            symbol: 标的股票代码
            option_type: 期权类型 ('call' 或 'put')
            strike: 行权价
            expiry: 到期日 (格式: 'YYYY-MM-DD')
            method: 定价模型 ('black_scholes' 或 'binomial')
            
        Returns:
            期权理论价格
        """
        from scipy import stats
        import numpy as np
        
        logger.info(f"计算期权价格: {symbol} {option_type} {strike} {expiry}")
        
        try:
            # 获取当前股价
            stock_data = self.get_real_time_quotes(symbol)
            if not stock_data or "price" not in stock_data:
                raise ValueError("无法获取当前股价")
            
            S = stock_data["price"]  # 当前股价
            K = float(strike)  # 行权价
            
            # 计算到期时间（年）
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
            T = (expiry_date - datetime.now()).days / 365.0
            
            if T <= 0:
                raise ValueError("期权已到期")
            
            # 使用固定值代替实际值
            r = 0.01  # 无风险利率
            sigma = 0.20  # 波动率
            
            # 尝试获取股票的历史波动率
            try:
                hist_data = self.get_historical_data(symbol, "3mo")
                if hist_data is not None:
                    returns = np.log(hist_data['Close'] / hist_data['Close'].shift(1))
                    sigma = returns.std() * np.sqrt(252)  # 年化波动率
            except Exception as e:
                logger.warning(f"计算历史波动率失败，使用默认值: {e}")
            
            if method == "black_scholes":
                # Black-Scholes 模型
                d1 = (np.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * np.sqrt(T))
                d2 = d1 - sigma * np.sqrt(T)
                
                if option_type.lower() == 'call':
                    price = S * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)
                else:  # put
                    price = K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * stats.norm.cdf(-d1)
                
                return round(price, 2)
            
            elif method == "binomial":
                # 二叉树模型 (简化版)
                n = 100  # 时间步数
                dt = T / n
                u = np.exp(sigma * np.sqrt(dt))
                d = 1 / u
                p = (np.exp(r * dt) - d) / (u - d)
                
                # 创建最终节点的股价
                prices = np.zeros(n + 1)
                for i in range(n + 1):
                    prices[i] = S * (u ** (n - i)) * (d ** i)
                
                # 创建最终节点的期权价值
                option_values = np.zeros(n + 1)
                for i in range(n + 1):
                    if option_type.lower() == 'call':
                        option_values[i] = max(0, prices[i] - K)
                    else:  # put
                        option_values[i] = max(0, K - prices[i])
                
                # 向后迭代计算期权价值
                for j in range(n - 1, -1, -1):
                    for i in range(j + 1):
                        option_values[i] = np.exp(-r * dt) * (p * option_values[i] + (1 - p) * option_values[i + 1])
                
                return round(option_values[0], 2)
            
            else:
                raise ValueError(f"不支持的定价模型: {method}")
                
        except Exception as e:
            logger.error(f"计算期权价格失败: {e}")
            return None
    
    def get_market_news(self, symbol=None, count=5):
        """获取市场或特定股票的新闻
        
        Args:
            symbol: 股票代码，如不指定则获取一般市场新闻
            count: 返回新闻条数
            
        Returns:
            包含新闻条目的列表
        """
        logger.info(f"获取{'市场' if symbol is None else symbol}新闻")
        
        try:
            if symbol:
                # 获取特定股票相关新闻
                stock = yf.Ticker(symbol)
                news = stock.news
                
                if not news:
                    logger.warning(f"没有找到关于 {symbol} 的新闻")
                    return []
                
                # 处理新闻数据
                result = []
                for item in news[:count]:
                    result.append({
                        "title": item.get("title"),
                        "publisher": item.get("publisher"),
                        "link": item.get("link"),
                        "published": datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                        "summary": item.get("summary")
                    })
                return result
            else:
                # 获取一般市场新闻(使用主要指数如SPY)
                stock = yf.Ticker("SPY")
                news = stock.news
                
                # 处理新闻数据
                result = []
                for item in news[:count]:
                    result.append({
                        "title": item.get("title"),
                        "publisher": item.get("publisher"),
                        "link": item.get("link"),
                        "published": datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                        "summary": item.get("summary")
                    })
                return result
                
        except Exception as e:
            logger.error(f"获取新闻失败: {e}")
            return []

# 策略回测简单框架
class SimpleBacktester:
    """简单的策略回测框架"""
    
    def __init__(self, data_api=None):
        """初始化回测系统
        
        Args:
            data_api: 数据API实例，默认创建新的GoogleFinanceAPI实例
        """
        self.data_api = data_api or GoogleFinanceAPI()
        self.portfolio = {
            "cash": 10000.0,  # 初始资金
            "positions": {},  # 持仓
            "history": [],    # 交易历史
            "equity": []      # 权益曲线
        }
        logger.info("回测系统初始化完成")
    
    def run_backtest(self, strategy, symbols, start_date, end_date, interval="1d"):
        """运行回测
        
        Args:
            strategy: 策略函数，接收价格数据和当前持仓，返回交易指令
            symbols: 交易的股票代码列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            interval: 数据时间间隔
            
        Returns:
            回测结果统计
        """
        logger.info(f"开始回测: {symbols} 从 {start_date} 到 {end_date}")
        
        # 初始化组合
        self.portfolio = {
            "cash": 10000.0,
            "positions": {},
            "history": [],
            "equity": []
        }
        
        # 获取历史数据
        data = {}
        for symbol in symbols:
            # 计算时间范围
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            days = (end - start).days
            
            period = "max"  # 默认获取最长时间
            if days <= 30:
                period = "1mo"
            elif days <= 90:
                period = "3mo"
            elif days <= 180:
                period = "6mo"
            elif days <= 365:
                period = "1y"
            elif days <= 730:
                period = "2y"
            elif days <= 1825:
                period = "5y"
            
            # 获取数据
            symbol_data = self.data_api.get_historical_data(symbol, period=period, interval=interval)
            if symbol_data is not None:
                # 过滤时间范围
                data[symbol] = symbol_data[(symbol_data.index >= start) & (symbol_data.index <= end)]
        
        if not data:
            logger.error("无法获取回测所需的历史数据")
            return None
        
        # 获取所有唯一的时间点
        all_dates = set()
        for symbol, df in data.items():
            all_dates.update(df.index.tolist())
        all_dates = sorted(list(all_dates))
        
        # 运行回测
        equity_history = []
        for date in all_dates:
            # 当前价格数据
            current_data = {}
            for symbol, df in data.items():
                if date in df.index:
                    current_data[symbol] = df.loc[date].to_dict()
            
            if not current_data:
                continue
            
            # 执行策略
            orders = strategy(current_data, self.portfolio)
            
            # 执行订单
            if orders:
                self._execute_orders(orders, current_data, date)
            
            # 更新权益
            equity = self.portfolio["cash"]
            for symbol, position in self.portfolio["positions"].items():
                if symbol in current_data and "Close" in current_data[symbol]:
                    equity += position["quantity"] * current_data[symbol]["Close"]
            
            self.portfolio["equity"].append({"date": date.strftime("%Y-%m-%d"), "equity": equity})
            equity_history.append(equity)
        
        # 计算结果统计
        if len(equity_history) > 1:
            start_equity = equity_history[0]
            end_equity = equity_history[-1]
            total_return = (end_equity / start_equity - 1) * 100
            
            # 计算年化收益
            years = (all_dates[-1] - all_dates[0]).days / 365.0
            annual_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
            
            # 计算最大回撤
            max_drawdown = 0
            peak = equity_history[0]
            for value in equity_history:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            return {
                "total_return": round(total_return, 2),
                "annual_return": round(annual_return, 2),
                "max_drawdown": round(max_drawdown, 2),
                "trades": len(self.portfolio["history"]),
                "ending_cash": round(self.portfolio["cash"], 2),
                "ending_equity": round(end_equity, 2),
                "equity_curve": self.portfolio["equity"],
                "trade_history": self.portfolio["history"]
            }
        
        logger.error("回测数据不足")
        return None
    
    def _execute_orders(self, orders, current_data, date):
        """执行交易订单
        
        Args:
            orders: 订单列表
            current_data: 当天价格数据
            date: 交易日期
        """
        for order in orders:
            symbol = order.get("symbol")
            action = order.get("action")  # 'buy' 或 'sell'
            quantity = order.get("quantity", 0)
            
            if not symbol or not action or quantity <= 0 or symbol not in current_data:
                logger.warning(f"无效的订单: {order}")
                continue
            
            price = current_data[symbol].get("Close", 0)
            if price <= 0:
                logger.warning(f"无效的价格: {symbol} {price}")
                continue
            
            if action.lower() == "buy":
                cost = price * quantity
                if cost <= self.portfolio["cash"]:
                    # 扣除现金
                    self.portfolio["cash"] -= cost
                    
                    # 更新持仓
                    if symbol not in self.portfolio["positions"]:
                        self.portfolio["positions"][symbol] = {"quantity": 0, "cost_basis": 0}
                    
                    # 计算新的成本基础
                    current_position = self.portfolio["positions"][symbol]
                    total_quantity = current_position["quantity"] + quantity
                    total_cost = current_position["cost_basis"] * current_position["quantity"] + cost
                    current_position["cost_basis"] = total_cost / total_quantity if total_quantity > 0 else 0
                    current_position["quantity"] = total_quantity
                    
                    # 记录交易
                    self.portfolio["history"].append({
                        "date": date.strftime("%Y-%m-%d"),
                        "action": "buy",
                        "symbol": symbol,
                        "quantity": quantity,
                        "price": price,
                        "cost": cost
                    })
                    
                    logger.info(f"买入: {quantity} {symbol} @ {price} 总额: {cost}")
                else:
                    logger.warning(f"资金不足，无法买入: {symbol} {quantity} 需要: {cost} 可用: {self.portfolio['cash']}")
            
            elif action.lower() == "sell":
                if symbol in self.portfolio["positions"] and self.portfolio["positions"][symbol]["quantity"] >= quantity:
                    # 计算收益
                    proceeds = price * quantity
                    
                    # 增加现金
                    self.portfolio["cash"] += proceeds
                    
                    # 更新持仓
                    self.portfolio["positions"][symbol]["quantity"] -= quantity
                    
                    # 如果持仓量为0，移除该股票
                    if self.portfolio["positions"][symbol]["quantity"] == 0:
                        cost_basis = self.portfolio["positions"][symbol]["cost_basis"]
                        del self.portfolio["positions"][symbol]
                    else:
                        cost_basis = self.portfolio["positions"][symbol]["cost_basis"]
                    
                    # 记录交易
                    self.portfolio["history"].append({
                        "date": date.strftime("%Y-%m-%d"),
                        "action": "sell",
                        "symbol": symbol,
                        "quantity": quantity,
                        "price": price,
                        "proceeds": proceeds,
                        "profit": proceeds - (cost_basis * quantity)
                    })
                    
                    logger.info(f"卖出: {quantity} {symbol} @ {price} 总额: {proceeds}")
                else:
                    logger.warning(f"持仓不足，无法卖出: {symbol} {quantity}")


# 示例使用
if __name__ == "__main__":
    # 创建API实例
    api = GoogleFinanceAPI()
    
    # 获取实时数据
    quotes = api.get_real_time_quotes("AAPL")
    print(f"实时报价: {quotes}")
    
    # 获取历史数据
    hist_data = api.get_historical_data("MSFT", period="1mo")
    if hist_data is not None:
        print(f"历史数据: {hist_data.tail()}")
    
    # 获取期权数据
    options = api.get_options_chain("SPY")
    if options:
        print(f"期权数据: {list(options.keys())}")
    
    # 计算期权价格
    option_price = api.calculate_option_price(
        "AAPL", 
        "call", 
        strike=quotes["price"] * 1.1,  # 10% OTM
        expiry=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    )
    print(f"期权理论价格: {option_price}")
    
    # 获取市场新闻
    news = api.get_market_news(count=3)
    print(f"市场新闻: {news}")
    
    # 简单回测示例
    def simple_strategy(data, portfolio):
        """简单的移动平均线策略"""
        orders = []
        for symbol, prices in data.items():
            current_price = prices.get("Close", 0)
            # 假设我们有一个移动平均线的计算
            # 在这里做简单模拟
            if symbol in portfolio["positions"]:
                # 持有股票，考虑卖出
                quantity = portfolio["positions"][symbol]["quantity"]
                orders.append({
                    "symbol": symbol,
                    "action": "sell",
                    "quantity": quantity
                })
            else:
                # 没有持股，考虑买入
                cash_to_use = portfolio["cash"] * 0.95  # 使用95%可用资金
                quantity = int(cash_to_use / current_price)
                if quantity > 0:
                    orders.append({
                        "symbol": symbol,
                        "action": "buy",
                        "quantity": quantity
                    })
        return orders
    
    # 初始化回测器
    backtest = SimpleBacktester(api)
    
    # 运行回测
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    result = backtest.run_backtest(
        simple_strategy, 
        ["AAPL", "MSFT"], 
        start_date, 
        end_date
    )
    
    if result:
        print(f"回测结果: {result}") 