#!/usr/bin/env python
"""
LiquiditySniper 增强工具 - 将模拟数据替换为真实市场数据

此脚本修改现有的 LiquiditySniper 模块，将其随机生成的模拟数据替换为
从真实市场数据源获取的数据。
"""

import os
import sys
import logging
import shutil
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# LiquiditySniper 文件路径
LIQUIDITY_SNIPER_PATH = Path("warmachine/liquidity_sniper.py")
BACKUP_PATH = Path("warmachine/liquidity_sniper.py.bak")

# 新的真实市场数据相关代码
REAL_MARKET_IMPORTS = """import os
import logging
import time
import json
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# 导入真实市场数据连接器
from real_market_connector import MarketDataConnector

# 设置日志
logger = logging.getLogger(__name__)
"""

REAL_MARKET_INIT = """    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Liquidity Sniper
        
        Args:
            config: Platform configuration dictionary
        """
        self.config = config
        self.trading_config = config.get("trading", {})
        self.hf_config = config.get("hf_trading", {})
        self.running = False
        
        # 初始化真实市场数据连接器
        self.market_connector = MarketDataConnector(config)
        logger.info("真实市场数据连接器已初始化")
        
        # Initialize trackers
        self.monitored_symbols = self.config.get("market_data", {}).get("symbols", [])
        self.whale_thresholds = self._initialize_whale_thresholds()
        
        # Order flow state
        self.order_flow = {}
        self.whale_alerts = []
        
        # Data storage paths
        self.data_path = "data/market/order_flow"
        os.makedirs(self.data_path, exist_ok=True)
        
        # Alert signal path
        self.alert_path = "data/alerts"
        os.makedirs(self.alert_path, exist_ok=True)
        
        logger.info("Liquidity Sniper initialized with real market data")
"""

REAL_MONITOR_ORDER_FLOW = """    def _monitor_order_flow(self):
        """从真实市场数据源获取订单流数据"""
        try:
            for symbol in self.monitored_symbols:
                # 创建当前数据点的时间戳
                timestamp = datetime.now().isoformat()
                
                # 获取市场类型
                market_type = "stock"
                if "-" in symbol:  # 简单判断加密货币市场
                    market_type = "crypto"
                
                # 获取真实订单簿数据
                orderbook = self.market_connector.get_orderbook(symbol, market_type=market_type)
                
                # 计算买卖量
                bid_volume = sum(bid[1] for bid in orderbook.get("bids", []))
                ask_volume = sum(ask[1] for ask in orderbook.get("asks", []))
                
                # 获取大额交易
                large_trades = self.market_connector.get_large_trades(
                    symbol, 
                    market_type=market_type,
                    min_value=self.whale_thresholds.get(symbol, 100000)
                )
                
                # 格式化大额交易数据为内部格式
                formatted_large_orders = []
                for trade in large_trades:
                    formatted_large_orders.append({
                        "side": trade["side"],
                        "price": trade["price"],
                        "volume": trade["volume"],
                        "exchange": trade.get("exchange", "unknown"),
                        "timestamp": trade["timestamp"]
                    })
                
                # 创建订单流数据点
                order_flow_data = {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "bid_volume": bid_volume,
                    "ask_volume": ask_volume,
                    "buy_market_orders": len([t for t in large_trades if t["side"] == "buy"]),
                    "sell_market_orders": len([t for t in large_trades if t["side"] == "sell"]),
                    "large_orders": formatted_large_orders
                }
                
                # 存储到内存
                if symbol not in self.order_flow:
                    self.order_flow[symbol] = []
                
                self.order_flow[symbol].append(order_flow_data)
                
                # 只保留每个交易对的最近100个数据点
                if len(self.order_flow[symbol]) > 100:
                    self.order_flow[symbol] = self.order_flow[symbol][-100:]
                
                # 将最新数据写入磁盘
                with open(os.path.join(self.data_path, f"{symbol}_order_flow.json"), "w") as f:
                    json.dump(self.order_flow[symbol][-10:], f, indent=2)
            
            logger.debug(f"已监控 {len(self.monitored_symbols)} 个交易对的真实订单流")
                
        except Exception as e:
            logger.error(f"订单流监控失败: {str(e)}")
"""

REAL_ANALYZE_WHALE = """    def _analyze_whale_movements(self):
        """分析大户活动并检测重要市场信号"""
        try:
            current_time = datetime.now().isoformat()
            
            for symbol in self.monitored_symbols:
                # 获取市场类型
                market_type = "stock"
                if "-" in symbol:  # 简单判断加密货币市场
                    market_type = "crypto"
                
                # 使用市场连接器分析大户活动
                whale_activity = self.market_connector.get_whale_activity(
                    symbol, 
                    market_type=market_type,
                    lookback=12  # 查看最近12小时
                )
                
                # 如果有明确的方向信号
                if whale_activity["direction"] != "neutral":
                    direction = "BUY" if whale_activity["direction"] == "accumulation" else "SELL"
                    logger.info(f"Whale {whale_activity['direction']} signal: {direction} {symbol}")
                
                # 检查大额交易
                large_trades = self.market_connector.get_large_trades(
                    symbol, 
                    market_type=market_type,
                    min_value=self.whale_thresholds.get(symbol, 100000)
                )
                
                # 处理每个大单交易
                for trade in large_trades:
                    # 创建鲸鱼警报
                    whale_alert = {
                        "timestamp": trade["timestamp"],
                        "symbol": symbol,
                        "side": trade["side"],
                        "volume": trade["volume"],
                        "price": trade["price"],
                        "value": trade["price"] * trade["volume"],
                        "exchange": trade.get("exchange", "unknown")
                    }
                    
                    # 添加到警报列表
                    if whale_alert not in self.whale_alerts:  # 避免重复
                        self.whale_alerts.append(whale_alert)
                        
                        # 保持最近的100条警报
                        if len(self.whale_alerts) > 100:
                            self.whale_alerts = self.whale_alerts[-100:]
                        
                        # 写入磁盘
                        alert_file = os.path.join(self.alert_path, "whale_alerts.json")
                        with open(alert_file, "w") as f:
                            json.dump(self.whale_alerts[-20:], f, indent=2)
                        
                        logger.info(f"Whale alert: {whale_alert['side']} {whale_alert['symbol']} ${whale_alert['value']:,.2f}")
            
        except Exception as e:
            logger.error(f"大户活动分析失败: {str(e)}")
"""

REMOVE_RANDOM_METHODS = """    # 以下方法已替换为真实市场数据，不再需要
    # def _generate_random_volume(self) -> float:
    #    pass
    
    # def _generate_random_orders(self) -> int:
    #    pass
    
    # def _generate_large_orders(self, symbol: str) -> List[Dict[str, Any]]:
    #    pass
    
    def get_market_imbalance(self, symbol: str) -> float:
        """获取指定交易对的市场不平衡度"""
        # 确定市场类型
        market_type = "stock"
        if "-" in symbol:
            market_type = "crypto"
            
        # 使用真实市场数据计算不平衡度
        return self.market_connector.calculate_order_imbalance(symbol, market_type)
"""

def backup_original_file():
    """备份原始文件"""
    if LIQUIDITY_SNIPER_PATH.exists():
        shutil.copy(LIQUIDITY_SNIPER_PATH, BACKUP_PATH)
        logger.info(f"已备份原始文件至 {BACKUP_PATH}")
    else:
        logger.error(f"未找到原始文件: {LIQUIDITY_SNIPER_PATH}")
        return False
    return True

def modify_file():
    """修改文件以使用真实市场数据"""
    try:
        with open(LIQUIDITY_SNIPER_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换导入部分
        import_pattern = 'import os\nimport logging\nimport time\nimport json\nimport threading\nfrom datetime import datetime\nfrom typing import Dict, List, Any, Optional, Tuple'
        if import_pattern in content:
            content = content.replace(import_pattern, REAL_MARKET_IMPORTS)
        else:
            logger.warning("未找到匹配的导入部分，直接在顶部添加新导入")
            content = REAL_MARKET_IMPORTS + content
        
        # 替换初始化方法
        init_pattern = '    def __init__(self, config: Dict[str, Any]):'
        if init_pattern in content:
            init_end = content.find('    def run(self)')
            if init_end > 0:
                old_init = content[content.find(init_pattern):init_end]
                content = content.replace(old_init, REAL_MARKET_INIT)
            else:
                logger.warning("未找到初始化方法结束位置，跳过替换")
        else:
            logger.warning("未找到匹配的初始化方法，跳过替换")
        
        # 替换订单流监控方法
        monitor_pattern = '    def _monitor_order_flow(self):'
        if monitor_pattern in content:
            monitor_end = content.find('    def _analyze_whale_movements(self):')
            if monitor_end > 0:
                old_monitor = content[content.find(monitor_pattern):monitor_end]
                content = content.replace(old_monitor, REAL_MONITOR_ORDER_FLOW)
            else:
                logger.warning("未找到订单流监控方法结束位置，跳过替换")
        else:
            logger.warning("未找到匹配的订单流监控方法，跳过替换")
        
        # 替换大户分析方法
        analyze_pattern = '    def _analyze_whale_movements(self):'
        if analyze_pattern in content:
            analyze_end = content.find('    def _generate_signals(self):')
            if analyze_end > 0:
                old_analyze = content[content.find(analyze_pattern):analyze_end]
                content = content.replace(old_analyze, REAL_ANALYZE_WHALE)
            else:
                logger.warning("未找到大户分析方法结束位置，跳过替换")
        else:
            logger.warning("未找到匹配的大户分析方法，跳过替换")
        
        # 移除随机数据生成方法
        random_volume_pattern = '    def _generate_random_volume(self) -> float:'
        if random_volume_pattern in content:
            # 找到这一部分的结束位置
            next_method_pos = content.find('    def get_latest_signals', content.find(random_volume_pattern))
            if next_method_pos > 0:
                old_random_methods = content[content.find(random_volume_pattern):next_method_pos]
                content = content.replace(old_random_methods, REMOVE_RANDOM_METHODS)
            else:
                logger.warning("未找到随机方法结束位置，跳过替换")
        else:
            logger.warning("未找到匹配的随机方法，跳过替换")
        
        # 保存修改后的文件
        with open(LIQUIDITY_SNIPER_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"成功修改 {LIQUIDITY_SNIPER_PATH}")
        return True
    except Exception as e:
        logger.error(f"修改文件时出错: {str(e)}")
        return False

def create_config_file():
    """创建API密钥配置文件模板"""
    config_path = Path("config/api_keys.json")
    config_dir = config_path.parent
    
    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
    
    if not config_path.exists():
        config = {
            "alpha_vantage_key": "",
            "finnhub_key": "",
            "polygon_key": "",
            "binance_key": "",
            "binance_secret": "",
            "coinbase_key": "",
            "coinbase_secret": "",
            "tradier_key": "",
            "iex_key": ""
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"已创建API密钥配置文件模板: {config_path}")
        logger.info("请在此文件中填入您的API密钥")
    
    # 创建环境变量设置脚本
    env_script_path = Path("set_api_keys.ps1")  # Windows PowerShell
    
    with open(env_script_path, 'w', encoding='utf-8') as f:
        f.write('# 设置API密钥环境变量\n\n')
        f.write('$config = Get-Content -Raw -Path "./config/api_keys.json" | ConvertFrom-Json\n\n')
        f.write('# 设置环境变量\n')
        f.write('$env:ALPHA_VANTAGE_API_KEY = $config.alpha_vantage_key\n')
        f.write('$env:FINNHUB_API_KEY = $config.finnhub_key\n')
        f.write('$env:POLYGON_API_KEY = $config.polygon_key\n')
        f.write('$env:BINANCE_API_KEY = $config.binance_key\n')
        f.write('$env:BINANCE_SECRET_KEY = $config.binance_secret\n')
        f.write('$env:COINBASE_API_KEY = $config.coinbase_key\n')
        f.write('$env:COINBASE_SECRET_KEY = $config.coinbase_secret\n')
        f.write('$env:TRADIER_API_KEY = $config.tradier_key\n')
        f.write('$env:IEX_API_KEY = $config.iex_key\n\n')
        f.write('Write-Host "API密钥环境变量已设置成功!" -ForegroundColor Green\n')
    
    logger.info(f"已创建环境变量设置脚本: {env_script_path}")

def main():
    """主函数"""
    logger.info("开始增强 LiquiditySniper 使用真实市场数据")
    
    # 检查是否已存在MarketDataConnector
    if not Path("real_market_connector.py").exists():
        logger.error("未找到 real_market_connector.py，请先创建此文件")
        return False
    
    # 备份原始文件
    if not backup_original_file():
        return False
    
    # 修改文件
    if not modify_file():
        logger.error("修改失败，恢复原始文件")
        if BACKUP_PATH.exists():
            shutil.copy(BACKUP_PATH, LIQUIDITY_SNIPER_PATH)
        return False
    
    # 创建配置文件
    create_config_file()
    
    logger.info("LiquiditySniper 增强完成！")
    logger.info("请按照以下步骤进行配置：")
    logger.info("1. 在 config/api_keys.json 中填入您的API密钥")
    logger.info("2. 运行 ./set_api_keys.ps1 设置环境变量")
    logger.info("3. 重启系统以使用真实市场数据")
    
    return True

if __name__ == "__main__":
    import json
    main() 