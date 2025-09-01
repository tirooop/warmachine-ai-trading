"""
Performance Metrics Module
"""

import logging
from typing import Dict, Any, List
import psutil
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """系统指标数据类"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    process_count: int
    timestamp: datetime

class PerformanceMetrics:
    """性能指标类"""
    
    def __init__(self, history_size: int = 1000):
        """初始化性能指标"""
        self._history_size = history_size
        self._metrics_history = deque(maxlen=history_size)
        self._start_time = datetime.now()
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        try:
            # 获取CPU使用率
            cpu_usage = psutil.cpu_percent()
            
            # 获取内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 获取磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # 获取网络IO
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # 获取进程数
            process_count = len(psutil.pids())
            
            # 创建系统指标
            metrics = SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                process_count=process_count,
                timestamp=datetime.now()
            )
            
            # 保存到历史记录
            self._metrics_history.append(metrics)
            
            return {
                'status': 'success',
                'metrics': {
                    'cpu_usage': metrics.cpu_usage,
                    'memory_usage': metrics.memory_usage,
                    'disk_usage': metrics.disk_usage,
                    'network_io': metrics.network_io,
                    'process_count': metrics.process_count,
                    'timestamp': metrics.timestamp.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            if not self._metrics_history:
                return {
                    'status': 'error',
                    'error': 'No metrics history available'
                }
            
            # 计算平均值
            averages = {
                'cpu_usage': np.mean([m.cpu_usage for m in self._metrics_history]),
                'memory_usage': np.mean([m.memory_usage for m in self._metrics_history]),
                'disk_usage': np.mean([m.disk_usage for m in self._metrics_history]),
                'process_count': np.mean([m.process_count for m in self._metrics_history])
            }
            
            # 计算标准差
            std_devs = {
                'cpu_usage': np.std([m.cpu_usage for m in self._metrics_history]),
                'memory_usage': np.std([m.memory_usage for m in self._metrics_history]),
                'disk_usage': np.std([m.disk_usage for m in self._metrics_history]),
                'process_count': np.std([m.process_count for m in self._metrics_history])
            }
            
            # 计算最大值
            max_values = {
                'cpu_usage': max(m.cpu_usage for m in self._metrics_history),
                'memory_usage': max(m.memory_usage for m in self._metrics_history),
                'disk_usage': max(m.disk_usage for m in self._metrics_history),
                'process_count': max(m.process_count for m in self._metrics_history)
            }
            
            # 计算最小值
            min_values = {
                'cpu_usage': min(m.cpu_usage for m in self._metrics_history),
                'memory_usage': min(m.memory_usage for m in self._metrics_history),
                'disk_usage': min(m.disk_usage for m in self._metrics_history),
                'process_count': min(m.process_count for m in self._metrics_history)
            }
            
            return {
                'status': 'success',
                'summary': {
                    'averages': averages,
                    'std_devs': std_devs,
                    'max_values': max_values,
                    'min_values': min_values,
                    'history_size': len(self._metrics_history),
                    'time_range': {
                        'start': self._metrics_history[0].timestamp.isoformat(),
                        'end': self._metrics_history[-1].timestamp.isoformat()
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def get_uptime(self) -> float:
        """获取系统运行时间（秒）"""
        return (datetime.now() - self._start_time).total_seconds()
        
    def clear_history(self):
        """清除历史记录"""
        self._metrics_history.clear()
        
    def get_history_size(self) -> int:
        """获取历史记录大小"""
        return len(self._metrics_history)
        
    def set_history_size(self, size: int):
        """设置历史记录大小"""
        if size > 0:
            self._history_size = size
            self._metrics_history = deque(self._metrics_history, maxlen=size)
        else:
            raise ValueError("History size must be greater than 0") 