"""
Signal Quality Assessment System
交易信号质量评估系统
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from scipy import stats
from sklearn.preprocessing import StandardScaler
import pandas as pd

@dataclass
class QualityMetrics:
    """信号质量指标"""
    reliability: float        # 可靠性得分 (0-1)
    consistency: float       # 一致性得分 (0-1)
    robustness: float        # 鲁棒性得分 (0-1)
    predictability: float    # 可预测性得分 (0-1)
    overall_score: float     # 综合得分 (0-1)

class SignalQualityAnalyzer:
    """信号质量分析器"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.historical_signals = []
        self.quality_threshold = 0.7
        
    def analyze_signal(self, signal: Dict[str, Any], 
                      market_data: pd.DataFrame) -> QualityMetrics:
        """分析信号质量"""
        try:
            # 1. 计算可靠性
            reliability = self._calculate_reliability(signal, market_data)
            
            # 2. 计算一致性
            consistency = self._calculate_consistency(signal)
            
            # 3. 计算鲁棒性
            robustness = self._calculate_robustness(signal, market_data)
            
            # 4. 计算可预测性
            predictability = self._calculate_predictability(signal, market_data)
            
            # 5. 计算综合得分
            overall_score = self._calculate_overall_score(
                reliability, consistency, robustness, predictability
            )
            
            # 更新历史记录
            self.historical_signals.append({
                'signal': signal,
                'metrics': QualityMetrics(
                    reliability=reliability,
                    consistency=consistency,
                    robustness=robustness,
                    predictability=predictability,
                    overall_score=overall_score
                )
            })
            
            return QualityMetrics(
                reliability=reliability,
                consistency=consistency,
                robustness=robustness,
                predictability=predictability,
                overall_score=overall_score
            )
            
        except Exception as e:
            print(f"Error in signal quality analysis: {str(e)}")
            return QualityMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
    
    def _calculate_reliability(self, signal: Dict[str, Any], 
                             market_data: pd.DataFrame) -> float:
        """计算信号可靠性"""
        try:
            # 1. 检查信号强度
            strength_score = min(1.0, signal['signal']['signal_strength'] / 5.0)
            
            # 2. 检查置信度
            confidence_score = signal['signal']['confidence']
            
            # 3. 检查市场条件匹配度
            market_conditions = self._analyze_market_conditions(market_data)
            condition_score = self._calculate_condition_match(
                signal, market_conditions
            )
            
            # 4. 综合评分
            reliability = (strength_score * 0.3 + 
                         confidence_score * 0.4 + 
                         condition_score * 0.3)
            
            return float(reliability)
            
        except Exception:
            return 0.0
    
    def _calculate_consistency(self, signal: Dict[str, Any]) -> float:
        """计算信号一致性"""
        try:
            if not self.historical_signals:
                return 0.7  # 默认值
                
            # 1. 计算历史信号的平均方向
            historical_directions = [
                s['signal']['bias'] 
                for s in self.historical_signals[-5:]
            ]
            direction_consistency = (
                historical_directions.count(signal['signal']['bias']) 
                / len(historical_directions)
            )
            
            # 2. 计算信号强度的稳定性
            strength_std = np.std([
                s['signal']['signal_strength'] 
                for s in self.historical_signals[-5:]
            ])
            strength_stability = 1.0 / (1.0 + strength_std)
            
            # 3. 综合评分
            consistency = (direction_consistency * 0.6 + 
                         strength_stability * 0.4)
            
            return float(consistency)
            
        except Exception:
            return 0.0
    
    def _calculate_robustness(self, signal: Dict[str, Any], 
                            market_data: pd.DataFrame) -> float:
        """计算信号鲁棒性"""
        try:
            # 1. 计算市场波动性
            volatility = market_data['Close'].pct_change().std()
            volatility_score = 1.0 / (1.0 + volatility)
            
            # 2. 计算信号对噪声的敏感度
            noise_sensitivity = self._calculate_noise_sensitivity(signal)
            
            # 3. 计算风险因素的影响
            risk_impact = self._calculate_risk_impact(signal)
            
            # 4. 综合评分
            robustness = (volatility_score * 0.3 + 
                         (1 - noise_sensitivity) * 0.4 + 
                         (1 - risk_impact) * 0.3)
            
            return float(robustness)
            
        except Exception:
            return 0.0
    
    def _calculate_predictability(self, signal: Dict[str, Any], 
                                market_data: pd.DataFrame) -> float:
        """计算信号可预测性"""
        try:
            # 1. 计算技术指标的一致性
            indicator_consistency = self._calculate_indicator_consistency(
                signal, market_data
            )
            
            # 2. 计算历史预测准确率
            historical_accuracy = self._calculate_historical_accuracy()
            
            # 3. 计算信号清晰度
            signal_clarity = self._calculate_signal_clarity(signal)
            
            # 4. 综合评分
            predictability = (indicator_consistency * 0.4 + 
                            historical_accuracy * 0.4 + 
                            signal_clarity * 0.2)
            
            return float(predictability)
            
        except Exception:
            return 0.0
    
    def _calculate_overall_score(self, reliability: float, 
                               consistency: float, 
                               robustness: float, 
                               predictability: float) -> float:
        """计算综合得分"""
        weights = {
            'reliability': 0.3,
            'consistency': 0.2,
            'robustness': 0.3,
            'predictability': 0.2
        }
        
        overall_score = (
            reliability * weights['reliability'] +
            consistency * weights['consistency'] +
            robustness * weights['robustness'] +
            predictability * weights['predictability']
        )
        
        return float(overall_score)
    
    def _analyze_market_conditions(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """分析市场条件"""
        try:
            # 计算各种市场指标
            volatility = market_data['Close'].pct_change().std()
            trend = self._calculate_trend(market_data)
            volume_profile = self._analyze_volume_profile(market_data)
            
            return {
                'volatility': float(volatility),
                'trend': float(trend),
                'volume_profile': float(volume_profile)
            }
        except Exception:
            return {'volatility': 0.0, 'trend': 0.0, 'volume_profile': 0.0}
    
    def _calculate_trend(self, market_data: pd.DataFrame) -> float:
        """计算市场趋势强度"""
        try:
            # 使用线性回归计算趋势
            x = np.arange(len(market_data))
            y = market_data['Close'].values
            slope, _, r_value, _, _ = stats.linregress(x, y)
            
            # 返回趋势强度和方向
            return float(slope * r_value**2)
        except Exception:
            return 0.0
    
    def _analyze_volume_profile(self, market_data: pd.DataFrame) -> float:
        """分析成交量分布"""
        try:
            # 计算成交量分布的特征
            volume_std = market_data['Volume'].std()
            volume_mean = market_data['Volume'].mean()
            
            # 返回成交量分布的稳定性指标
            return float(1.0 / (1.0 + volume_std / volume_mean))
        except Exception:
            return 0.0
    
    def _calculate_condition_match(self, signal: Dict[str, Any], 
                                 market_conditions: Dict[str, float]) -> float:
        """计算信号与市场条件的匹配度"""
        try:
            # 1. 检查波动性匹配
            volatility_match = 1.0 - abs(
                signal['signal']['risk_factors'][0] - 
                market_conditions['volatility']
            )
            
            # 2. 检查趋势匹配
            trend_match = 1.0 if (
                (signal['signal']['bias'] == 'BULLISH' and market_conditions['trend'] > 0) or
                (signal['signal']['bias'] == 'BEARISH' and market_conditions['trend'] < 0)
            ) else 0.0
            
            # 3. 检查成交量匹配
            volume_match = market_conditions['volume_profile']
            
            # 4. 综合评分
            condition_match = (
                volatility_match * 0.3 +
                trend_match * 0.4 +
                volume_match * 0.3
            )
            
            return float(condition_match)
            
        except Exception:
            return 0.0
    
    def _calculate_noise_sensitivity(self, signal: Dict[str, Any]) -> float:
        """计算信号对噪声的敏感度"""
        try:
            # 1. 检查信号强度
            strength = signal['signal']['signal_strength']
            
            # 2. 检查置信度
            confidence = signal['signal']['confidence']
            
            # 3. 检查风险因素
            risk_factors = len(signal['signal']['risk_factors'])
            
            # 4. 计算敏感度
            sensitivity = (
                (1.0 - strength/5.0) * 0.4 +
                (1.0 - confidence) * 0.4 +
                (risk_factors/5.0) * 0.2
            )
            
            return float(sensitivity)
            
        except Exception:
            return 1.0
    
    def _calculate_risk_impact(self, signal: Dict[str, Any]) -> float:
        """计算风险因素的影响"""
        try:
            # 1. 解析风险因素
            risk_factors = signal['signal']['risk_factors']
            
            # 2. 计算风险得分
            risk_scores = []
            for factor in risk_factors:
                if '波动率' in factor:
                    risk_scores.append(float(factor.split(':')[1].strip('%')) / 100)
                elif '成交量' in factor:
                    volume = int(factor.split(':')[1].replace(',', ''))
                    risk_scores.append(min(1.0, volume / 1e6))
                elif '置信度' in factor:
                    risk_scores.append(float(factor.split(':')[1]))
            
            # 3. 计算平均风险影响
            risk_impact = np.mean(risk_scores) if risk_scores else 0.5
            
            return float(risk_impact)
            
        except Exception:
            return 0.5
    
    def _calculate_indicator_consistency(self, signal: Dict[str, Any], 
                                      market_data: pd.DataFrame) -> float:
        """计算技术指标的一致性"""
        try:
            # 1. 提取技术指标
            indicators = signal['signal']['logic_chain']
            
            # 2. 计算指标间的相关性
            indicator_scores = []
            for indicator in indicators:
                if '量子共识' in indicator:
                    score = float(indicator.split(':')[1])
                    indicator_scores.append(score/5.0)
                elif '流形学习' in indicator:
                    score = float(indicator.split(':')[1])
                    indicator_scores.append(score/5.0)
                elif '最终得分' in indicator:
                    score = float(indicator.split(':')[1])
                    indicator_scores.append(score/5.0)
            
            # 3. 计算一致性
            if len(indicator_scores) >= 2:
                consistency = 1.0 - np.std(indicator_scores)
            else:
                consistency = 0.5
            
            return float(consistency)
            
        except Exception:
            return 0.0
    
    def _calculate_historical_accuracy(self) -> float:
        """计算历史预测准确率"""
        try:
            if len(self.historical_signals) < 2:
                return 0.5
                
            # 计算最近信号的准确率
            recent_signals = self.historical_signals[-5:]
            accuracy_scores = [
                s['metrics'].overall_score 
                for s in recent_signals
            ]
            
            return float(np.mean(accuracy_scores))
            
        except Exception:
            return 0.5
    
    def _calculate_signal_clarity(self, signal: Dict[str, Any]) -> float:
        """计算信号清晰度"""
        try:
            # 1. 检查信号强度
            strength = signal['signal']['signal_strength']
            
            # 2. 检查置信度
            confidence = signal['signal']['confidence']
            
            # 3. 检查逻辑链的清晰度
            logic_chain = signal['signal']['logic_chain']
            logic_clarity = len(logic_chain) / 5.0  # 假设最多5个逻辑点
            
            # 4. 综合评分
            clarity = (
                (strength/5.0) * 0.3 +
                confidence * 0.4 +
                logic_clarity * 0.3
            )
            
            return float(clarity)
            
        except Exception:
            return 0.0
    
    def is_signal_acceptable(self, metrics: QualityMetrics) -> bool:
        """判断信号是否可接受"""
        return metrics.overall_score >= self.quality_threshold
    
    def get_quality_report(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """生成质量报告"""
        return {
            'reliability': {
                'score': metrics.reliability,
                'status': 'Good' if metrics.reliability >= 0.7 else 'Poor'
            },
            'consistency': {
                'score': metrics.consistency,
                'status': 'Good' if metrics.consistency >= 0.7 else 'Poor'
            },
            'robustness': {
                'score': metrics.robustness,
                'status': 'Good' if metrics.robustness >= 0.7 else 'Poor'
            },
            'predictability': {
                'score': metrics.predictability,
                'status': 'Good' if metrics.predictability >= 0.7 else 'Poor'
            },
            'overall': {
                'score': metrics.overall_score,
                'status': 'Acceptable' if self.is_signal_acceptable(metrics) else 'Rejected'
            }
        } 