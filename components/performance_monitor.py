"""
性能监控组件
负责监控系统性能指标
"""

import os
import sys
import time
import logging
import asyncio
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd

from core.exceptions import PerformanceError, ValidationError
from core.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'performance_monitor.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('PerformanceMonitor')


class PerformanceType(Enum):
    """性能类型枚举"""
    SYSTEM = "system"
    TRADING = "trading"
    APPLICATION = "application"
    NETWORK = "network"
    DATABASE = "database"


class PerformanceLevel(Enum):
    """性能等级枚举"""
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    performance_type: PerformanceType
    metric_name: str
    value: float
    unit: str
    threshold: float
    level: PerformanceLevel
    timestamp: datetime
    details: Dict[str, Any]


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    load_average: List[float]
    timestamp: datetime


@dataclass
class TradingMetrics:
    """交易性能指标数据类"""
    order_latency: float
    execution_speed: float
    success_rate: float
    throughput: float
    error_rate: float
    timestamp: datetime


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.config = get_config()
        self.metrics_history: List[SystemMetrics] = []
        self.running = False
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # 网络IO
            network_io = psutil.net_io_counters()
            network_metrics = {
                'bytes_sent': network_io.bytes_sent,
                'bytes_recv': network_io.bytes_recv,
                'packets_sent': network_io.packets_sent,
                'packets_recv': network_io.packets_recv
            }
            
            # 负载平均值
            load_average = psutil.getloadavg()
            
            metrics = SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_metrics,
                load_average=list(load_average),
                timestamp=datetime.now()
            )
            
            # 保存历史数据
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            return metrics
        
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            raise PerformanceError(f"收集系统指标失败: {e}")
    
    def get_system_summary(self) -> Dict[str, Any]:
        """获取系统摘要"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-100:]  # 最近100个指标
        
        return {
            "avg_cpu_usage": np.mean([m.cpu_usage for m in recent_metrics]),
            "avg_memory_usage": np.mean([m.memory_usage for m in recent_metrics]),
            "avg_disk_usage": np.mean([m.disk_usage for m in recent_metrics]),
            "max_cpu_usage": max([m.cpu_usage for m in recent_metrics]),
            "max_memory_usage": max([m.memory_usage for m in recent_metrics]),
            "current_load_average": recent_metrics[-1].load_average if recent_metrics else [0, 0, 0]
        }


class TradingPerformanceMonitor:
    """交易性能监控器"""
    
    def __init__(self):
        self.metrics_history: List[TradingMetrics] = []
        self.order_history: List[Dict[str, Any]] = []
        self.running = False
    
    async def record_order(self, order_data: Dict[str, Any]):
        """记录订单执行"""
        try:
            order_data['timestamp'] = datetime.now()
            self.order_history.append(order_data)
            
            # 保持历史记录在合理范围内
            if len(self.order_history) > 10000:
                self.order_history = self.order_history[-10000:]
        
        except Exception as e:
            logger.error(f"记录订单失败: {e}")
            raise PerformanceError(f"记录订单失败: {e}")
    
    async def calculate_trading_metrics(self) -> TradingMetrics:
        """计算交易性能指标"""
        try:
            if len(self.order_history) < 10:
                return TradingMetrics(
                    order_latency=0.0,
                    execution_speed=0.0,
                    success_rate=1.0,
                    throughput=0.0,
                    error_rate=0.0,
                    timestamp=datetime.now()
                )
            
            # 计算订单延迟
            recent_orders = self.order_history[-100:]
            latencies = []
            for order in recent_orders:
                if 'submit_time' in order and 'execution_time' in order:
                    latency = (order['execution_time'] - order['submit_time']).total_seconds()
                    latencies.append(latency)
            
            avg_latency = np.mean(latencies) if latencies else 0.0
            
            # 计算执行速度
            execution_speed = 1.0 / avg_latency if avg_latency > 0 else 0.0
            
            # 计算成功率
            successful_orders = [o for o in recent_orders if o.get('status') == 'filled']
            success_rate = len(successful_orders) / len(recent_orders) if recent_orders else 1.0
            
            # 计算吞吐量 (每秒订单数)
            if len(recent_orders) >= 2:
                time_span = (recent_orders[-1]['timestamp'] - recent_orders[0]['timestamp']).total_seconds()
                throughput = len(recent_orders) / time_span if time_span > 0 else 0.0
            else:
                throughput = 0.0
            
            # 计算错误率
            error_orders = [o for o in recent_orders if o.get('status') == 'rejected']
            error_rate = len(error_orders) / len(recent_orders) if recent_orders else 0.0
            
            metrics = TradingMetrics(
                order_latency=avg_latency,
                execution_speed=execution_speed,
                success_rate=success_rate,
                throughput=throughput,
                error_rate=error_rate,
                timestamp=datetime.now()
            )
            
            # 保存历史数据
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            return metrics
        
        except Exception as e:
            logger.error(f"计算交易性能指标失败: {e}")
            raise PerformanceError(f"计算交易性能指标失败: {e}")
    
    def get_trading_summary(self) -> Dict[str, Any]:
        """获取交易性能摘要"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-100:]
        
        return {
            "avg_order_latency": np.mean([m.order_latency for m in recent_metrics]),
            "avg_execution_speed": np.mean([m.execution_speed for m in recent_metrics]),
            "avg_success_rate": np.mean([m.success_rate for m in recent_metrics]),
            "avg_throughput": np.mean([m.throughput for m in recent_metrics]),
            "avg_error_rate": np.mean([m.error_rate for m in recent_metrics]),
            "total_orders": len(self.order_history),
            "recent_orders": len(self.order_history[-100:])
        }


class ApplicationPerformanceMonitor:
    """应用性能监控器"""
    
    def __init__(self):
        self.metrics_history: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.running = False
    
    async def collect_application_metrics(self) -> Dict[str, Any]:
        """收集应用性能指标"""
        try:
            # 进程信息
            process = psutil.Process()
            
            # 内存使用
            memory_info = process.memory_info()
            memory_usage_mb = memory_info.rss / 1024 / 1024
            
            # CPU使用
            cpu_percent = process.cpu_percent()
            
            # 线程数
            num_threads = process.num_threads()
            
            # 文件描述符数
            num_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
            
            # 运行时间
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            metrics = {
                "memory_usage_mb": memory_usage_mb,
                "cpu_percent": cpu_percent,
                "num_threads": num_threads,
                "num_fds": num_fds,
                "uptime_seconds": uptime,
                "timestamp": datetime.now()
            }
            
            # 保存历史数据
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            return metrics
        
        except Exception as e:
            logger.error(f"收集应用性能指标失败: {e}")
            raise PerformanceError(f"收集应用性能指标失败: {e}")
    
    def get_application_summary(self) -> Dict[str, Any]:
        """获取应用性能摘要"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-100:]
        
        return {
            "avg_memory_usage_mb": np.mean([m["memory_usage_mb"] for m in recent_metrics]),
            "avg_cpu_percent": np.mean([m["cpu_percent"] for m in recent_metrics]),
            "avg_num_threads": np.mean([m["num_threads"] for m in recent_metrics]),
            "max_memory_usage_mb": max([m["memory_usage_mb"] for m in recent_metrics]),
            "max_cpu_percent": max([m["cpu_percent"] for m in recent_metrics]),
            "uptime_hours": recent_metrics[-1]["uptime_seconds"] / 3600 if recent_metrics else 0
        }


class NetworkMonitor:
    """网络监控器"""
    
    def __init__(self):
        self.metrics_history: List[Dict[str, Any]] = []
        self.running = False
    
    async def collect_network_metrics(self) -> Dict[str, Any]:
        """收集网络指标"""
        try:
            # 网络连接统计
            connections = psutil.net_connections()
            
            # 按状态分组
            connection_states = {}
            for conn in connections:
                state = conn.status
                if state not in connection_states:
                    connection_states[state] = 0
                connection_states[state] += 1
            
            # 网络IO统计
            net_io = psutil.net_io_counters()
            
            # 网络接口统计
            net_if_stats = psutil.net_if_stats()
            
            metrics = {
                "total_connections": len(connections),
                "connection_states": connection_states,
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "active_interfaces": len([iface for iface, stats in net_if_stats.items() if stats.isup]),
                "timestamp": datetime.now()
            }
            
            # 保存历史数据
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            return metrics
        
        except Exception as e:
            logger.error(f"收集网络指标失败: {e}")
            raise PerformanceError(f"收集网络指标失败: {e}")
    
    def get_network_summary(self) -> Dict[str, Any]:
        """获取网络性能摘要"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-100:]
        
        return {
            "avg_total_connections": np.mean([m["total_connections"] for m in recent_metrics]),
            "avg_bytes_sent": np.mean([m["bytes_sent"] for m in recent_metrics]),
            "avg_bytes_recv": np.mean([m["bytes_recv"] for m in recent_metrics]),
            "max_connections": max([m["total_connections"] for m in recent_metrics]),
            "active_interfaces": recent_metrics[-1]["active_interfaces"] if recent_metrics else 0
        }


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self):
        self.thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0,
            "order_latency": 1.0,  # 秒
            "success_rate": 0.95,
            "error_rate": 0.05
        }
    
    def analyze_performance(self, metrics: Dict[str, Any]) -> List[PerformanceMetrics]:
        """分析性能指标"""
        performance_metrics = []
        
        try:
            # 分析系统性能
            if "system" in metrics:
                system = metrics["system"]
                
                # CPU使用率
                cpu_level = self._get_performance_level(system.cpu_usage, self.thresholds["cpu_usage"])
                performance_metrics.append(PerformanceMetrics(
                    performance_type=PerformanceType.SYSTEM,
                    metric_name="cpu_usage",
                    value=system.cpu_usage,
                    unit="%",
                    threshold=self.thresholds["cpu_usage"],
                    level=cpu_level,
                    timestamp=system.timestamp,
                    details={"load_average": system.load_average}
                ))
                
                # 内存使用率
                memory_level = self._get_performance_level(system.memory_usage, self.thresholds["memory_usage"])
                performance_metrics.append(PerformanceMetrics(
                    performance_type=PerformanceType.SYSTEM,
                    metric_name="memory_usage",
                    value=system.memory_usage,
                    unit="%",
                    threshold=self.thresholds["memory_usage"],
                    level=memory_level,
                    timestamp=system.timestamp,
                    details={}
                ))
            
            # 分析交易性能
            if "trading" in metrics:
                trading = metrics["trading"]
                
                # 订单延迟
                latency_level = self._get_performance_level(trading.order_latency, self.thresholds["order_latency"], reverse=True)
                performance_metrics.append(PerformanceMetrics(
                    performance_type=PerformanceType.TRADING,
                    metric_name="order_latency",
                    value=trading.order_latency,
                    unit="seconds",
                    threshold=self.thresholds["order_latency"],
                    level=latency_level,
                    timestamp=trading.timestamp,
                    details={}
                ))
                
                # 成功率
                success_level = self._get_performance_level(trading.success_rate, self.thresholds["success_rate"])
                performance_metrics.append(PerformanceMetrics(
                    performance_type=PerformanceType.TRADING,
                    metric_name="success_rate",
                    value=trading.success_rate,
                    unit="ratio",
                    threshold=self.thresholds["success_rate"],
                    level=success_level,
                    timestamp=trading.timestamp,
                    details={}
                ))
            
            return performance_metrics
        
        except Exception as e:
            logger.error(f"分析性能指标失败: {e}")
            raise PerformanceError(f"分析性能指标失败: {e}")
    
    def _get_performance_level(self, value: float, threshold: float, reverse: bool = False) -> PerformanceLevel:
        """获取性能等级"""
        if reverse:
            # 对于延迟等指标，值越小越好
            if value <= threshold * 0.5:
                return PerformanceLevel.EXCELLENT
            elif value <= threshold:
                return PerformanceLevel.GOOD
            elif value <= threshold * 1.5:
                return PerformanceLevel.WARNING
            else:
                return PerformanceLevel.CRITICAL
        else:
            # 对于使用率等指标，值越小越好
            if value <= threshold * 0.5:
                return PerformanceLevel.EXCELLENT
            elif value <= threshold:
                return PerformanceLevel.GOOD
            elif value <= threshold * 1.2:
                return PerformanceLevel.WARNING
            else:
                return PerformanceLevel.CRITICAL


class PerformanceMonitor:
    """性能监控器主类"""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.trading_monitor = TradingPerformanceMonitor()
        self.app_monitor = ApplicationPerformanceMonitor()
        self.network_monitor = NetworkMonitor()
        self.analyzer = PerformanceAnalyzer()
        self.running = False
        self.alerts: List[Dict[str, Any]] = []
        logger.info("性能监控器初始化完成")
    
    async def start(self):
        """启动性能监控"""
        self.running = True
        logger.info("性能监控器启动")
        
        try:
            while self.running:
                # 收集各种性能指标
                system_metrics = await self.system_monitor.collect_system_metrics()
                trading_metrics = await self.trading_monitor.calculate_trading_metrics()
                app_metrics = await self.app_monitor.collect_application_metrics()
                network_metrics = await self.network_monitor.collect_network_metrics()
                
                # 分析性能
                all_metrics = {
                    "system": system_metrics,
                    "trading": trading_metrics,
                    "application": app_metrics,
                    "network": network_metrics
                }
                
                performance_metrics = self.analyzer.analyze_performance(all_metrics)
                
                # 检查性能警报
                await self._check_performance_alerts(performance_metrics)
                
                await asyncio.sleep(5)  # 每5秒检查一次
        
        except Exception as e:
            logger.error(f"性能监控出错: {e}")
            self.running = False
    
    async def stop(self):
        """停止性能监控"""
        self.running = False
        logger.info("性能监控器停止")
    
    async def _check_performance_alerts(self, performance_metrics: List[PerformanceMetrics]):
        """检查性能警报"""
        for metric in performance_metrics:
            if metric.level in [PerformanceLevel.WARNING, PerformanceLevel.CRITICAL]:
                alert = {
                    "timestamp": datetime.now(),
                    "performance_type": metric.performance_type.value,
                    "metric_name": metric.metric_name,
                    "level": metric.level.value,
                    "value": metric.value,
                    "threshold": metric.threshold,
                    "unit": metric.unit,
                    "message": f"性能警报: {metric.metric_name} 达到 {metric.level.value} 级别 ({metric.value}{metric.unit})"
                }
                self.alerts.append(alert)
                logger.warning(f"性能警报: {alert['message']}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            return {
                "system": self.system_monitor.get_system_summary(),
                "trading": self.trading_monitor.get_trading_summary(),
                "application": self.app_monitor.get_application_summary(),
                "network": self.network_monitor.get_network_summary(),
                "total_alerts": len(self.alerts),
                "recent_alerts": len([a for a in self.alerts if (datetime.now() - a["timestamp"]).hours <= 1])
            }
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def record_order(self, order_data: Dict[str, Any]):
        """记录订单执行"""
        await self.trading_monitor.record_order(order_data)


if __name__ == "__main__":
    async def main():
        monitor = PerformanceMonitor()
        try:
            await monitor.start()
        except KeyboardInterrupt:
            await monitor.stop()
            logger.info("性能监控器已停止")
    
    asyncio.run(main()) 