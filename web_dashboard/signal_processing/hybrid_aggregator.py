"""
Hybrid Signal Aggregator
结合量子投票和动态权重系统的混合信号聚合器
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import time
import qiskit
from qiskit_aer import Aer
from qiskit import transpile
from sklearn.manifold import TSNE
from sklearn.metrics.pairwise import pairwise_distances
from itertools import islice
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class SignalMetrics:
    """信号指标数据类"""
    strength: float
    confidence: float
    volatility: float
    volume: int
    timestamp: Any

class VotingDynamics:
    """投票动力学模型"""
    def __init__(self):
        self.crowd_parameter = 1.68  # 从众效应强度
        self.noise_floor = 0.15      # 基础噪声水平

    def simulate_disturbance(self, raw_scores: np.ndarray) -> np.ndarray:
        """基于Ising模型的分数扰动预测"""
        magnetization = np.mean(raw_scores)
        disturbed_scores = []
      
        for score in raw_scores:
            # 朗之万方程描述打分者动态
            disturbance = (self.crowd_parameter * (magnetization - score) 
                         + self.noise_floor * np.random.normal())
            disturbed_scores.append(score + disturbance)
          
        return self._apply_bounds(np.array(disturbed_scores))

    @staticmethod
    def _apply_bounds(scores: np.ndarray) -> np.ndarray:
        """强制限制在有效评分范围内"""
        return np.clip(scores, 0, 5)

class ScoreDenoiser:
    """基于流形学习的降噪器"""
    def __init__(self, n_components: int = 2):
        self.embedding = TSNE(n_components=n_components)

    def clean_scores(self, raw_scores: np.ndarray, 
                    user_features: np.ndarray) -> float:
        """在行为流形上重构真实意图"""
        # 构建联合特征空间
        composite_features = np.hstack([
            raw_scores.reshape(-1,1),
            user_features
        ])
      
        # 非线性降维发现本征模式
        manifold = self.embedding.fit_transform(composite_features)
      
        # 基于流形距离重新加权
        weights = self._compute_manifold_weights(manifold)
        return float(np.average(raw_scores, weights=weights))

    def _compute_manifold_weights(self, points: np.ndarray) -> np.ndarray:
        """局部密度反比加权"""
        distances = pairwise_distances(points)
        return 1 / (distances.sum(axis=1) + 1e-6)

class DynamicWeighter:
    """动态信用权重分配系统"""
    def __init__(self):
        self.reliability_scores = defaultdict(lambda: 0.7)
        self.decay_factor = 0.95

    def update_weights(self, user_id: str, historical_std: float) -> None:
        """基于新表现更新权重"""
        new_reliability = 1 / (1 + np.log(historical_std + 1e-6))
        self.reliability_scores[user_id] = (
            self.decay_factor * self.reliability_scores[user_id] 
            + (1 - self.decay_factor) * new_reliability
        )

    def get_aggregated_score(self, vote_dict: Dict[str, float]) -> float:
        """信用加权聚合"""
        total_weight = sum(self.reliability_scores[u] for u in vote_dict)
        return float(sum(
            s * self.reliability_scores[u] 
            for u, s in vote_dict.items()
        ) / total_weight)

class QuantumVoting:
    """量子投票共识协议"""
    def __init__(self, n_voters: int):
        self.n_voters = n_voters
        self._create_circuit()

    def _create_circuit(self) -> None:
        """创建新的量子电路"""
        self.circuit = qiskit.QuantumCircuit(self.n_voters, self.n_voters)
        self._build_entanglement_network()

    def _build_entanglement_network(self) -> None:
        """创建GHZ态连接投票者"""
        self.circuit.h(0)
        for qubit in range(1, self.circuit.num_qubits):
            self.circuit.cx(0, qubit)

    def measure_consensus(self, votes: List[float]) -> str:
        """量子干涉提取共识"""
        try:
            # 重置电路
            self._create_circuit()
            
            # 应用投票旋转
            for i, vote in enumerate(votes):
                if vote > 3:  # 正向评价旋转相位
                    self.circuit.rx(vote/5 * np.pi, i)
                else:         # 负向评价旋转相位
                    self.circuit.ry(vote/5 * np.pi, i)
            
            # 添加测量操作
            self.circuit.measure_all()
            
            return self._execute_simulation()
            
        except Exception as e:
            logging.error(f"Error in quantum consensus: {str(e)}")
            # 返回默认值
            return "0" * self.n_voters

    def _execute_simulation(self) -> str:
        """模拟量子测量"""
        try:
            backend = Aer.get_backend('qasm_simulator')
            transpiled_circuit = transpile(self.circuit, backend)
            job = backend.run(transpiled_circuit, shots=1024)
            result = job.result()
            counts = result.get_counts()
            
            if not counts:
                logging.warning("No measurement results obtained")
                return "0" * self.n_voters
                
            return max(counts.items(), key=lambda x: x[1])[0]
            
        except Exception as e:
            logging.error(f"Error in quantum simulation: {str(e)}")
            return "0" * self.n_voters

class HybridAggregator:
    """混合信号聚合器"""
    
    def __init__(self):
        """初始化混合信号聚合器"""
        self._signal_buffer = deque(maxlen=1000)  # 循环缓冲区存储最近1000个信号
        self._lock = threading.RLock()  # 线程安全锁
        self._weights = {}  # 信号源权重
        self._confidence_threshold = 0.7  # 置信度阈值
        
    def get_current_signals(self, lookback: int = 50) -> pd.DataFrame:
        """获取最近N个信号的时序数据"""
        try:
            with self._lock:
                recent_signals = list(islice(self._signal_buffer, 
                                          max(0, len(self._signal_buffer)-lookback), 
                                          len(self._signal_buffer)))
            
            if not recent_signals:
                return pd.DataFrame()
            
            return pd.DataFrame({
                'timestamp': [s['timestamp'] for s in recent_signals],
                'final_score': [s['final_score'] for s in recent_signals],
                'confidence': [s['confidence'] for s in recent_signals],
                'volatility': [s.get('metadata', {}).get('volatility', 0) for s in recent_signals]
            }).set_index('timestamp')
            
        except Exception as e:
            logger.error(f"Error getting current signals: {str(e)}")
            return pd.DataFrame()
    
    def aggregate(self, raw_votes: List[float], **kwargs) -> Dict[str, Any]:
        """聚合原始投票信号"""
        try:
            # 计算基础统计量
            mean_score = np.mean(raw_votes)
            std_score = np.std(raw_votes)
            confidence = 1.0 / (1.0 + std_score)  # 标准差越小，置信度越高
            
            # 计算最终得分
            final_score = mean_score * confidence
            
            # 构建结果
            result = {
                'timestamp': datetime.now().isoformat(),
                'final_score': float(final_score),
                'confidence': float(confidence),
                'metadata': {
                    'volatility': float(std_score),
                    'vote_count': len(raw_votes),
                    'source_ip': kwargs.get('source_ip', 'unknown')
                }
            }
            
            # 保存到缓冲区
            with self._lock:
                self._signal_buffer.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error aggregating signals: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """获取信号统计信息"""
        try:
            with self._lock:
                if not self._signal_buffer:
                    return {
                        'status': 'error',
                        'error': 'No signals available'
                    }
                
                df = self.get_current_signals()
                
                return {
                    'status': 'success',
                    'statistics': {
                        'total_signals': len(df),
                        'mean_score': float(df['final_score'].mean()),
                        'mean_confidence': float(df['confidence'].mean()),
                        'mean_volatility': float(df['volatility'].mean()),
                        'latest_score': float(df['final_score'].iloc[-1]),
                        'latest_confidence': float(df['confidence'].iloc[-1])
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting signal statistics: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """更新信号源权重"""
        with self._lock:
            self._weights.update(new_weights)
    
    def get_weights(self) -> Dict[str, float]:
        """获取当前信号源权重"""
        return self._weights.copy()
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """设置置信度阈值"""
        if 0 <= threshold <= 1:
            self._confidence_threshold = threshold
        else:
            raise ValueError("Confidence threshold must be between 0 and 1")

    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """验证信号有效性"""
        try:
            # 检查必要字段
            required_fields = ["final_score", "confidence", "metadata"]
            if not all(field in signal for field in required_fields):
                return False
            
            # 检查数值范围
            if not (0 <= signal["final_score"] <= 5):
                return False
            if not (0 <= signal["confidence"] <= 1):
                return False
            
            # 检查元数据
            if not isinstance(signal["metadata"], dict):
                return False
            
            return True
            
        except Exception:
            return False 