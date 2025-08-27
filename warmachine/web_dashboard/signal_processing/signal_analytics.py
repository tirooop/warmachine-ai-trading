"""
Signal Analytics Engine Module
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SignalAnalyticsEngine:
    """信号分析引擎"""
    
    @staticmethod
    def calculate_metrics(df: pd.DataFrame) -> Dict[str, Any]:
        """计算信号指标"""
        try:
            if df.empty:
                return {
                    'status': 'error',
                    'error': 'No data available for analysis'
                }
            
            # 计算基础指标
            metrics = {
                'cumulative_alpha': float((df['final_score'] * df['confidence']).sum()),
                'sharpe_ratio': float(df['final_score'].mean() / df['final_score'].std() if df['final_score'].std() != 0 else 0),
                'signal_stability': float(np.corrcoef(
                    df['final_score'].values,
                    np.arange(len(df))
                )[0, 1]),
                'anomaly_count': int(sum(
                    (df['final_score'] - df['final_score'].rolling(5).mean()).abs() > 2
                ))
            }
            
            # 计算趋势指标
            metrics.update({
                'trend_strength': float(df['final_score'].diff().mean()),
                'volatility_trend': float(df['volatility'].diff().mean()),
                'confidence_trend': float(df['confidence'].diff().mean())
            })
            
            # 计算异常检测
            rolling_mean = df['final_score'].rolling(window=20).mean()
            rolling_std = df['final_score'].rolling(window=20).std()
            z_scores = (df['final_score'] - rolling_mean) / rolling_std
            metrics['anomaly_z_scores'] = z_scores.tolist()
            
            return {
                'status': 'success',
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def detect_abnormal_signals(df: pd.DataFrame) -> pd.DataFrame:
        """检测异常信号"""
        try:
            if df.empty:
                return pd.DataFrame()
            
            # 计算移动平均和标准差
            rolling_mean = df['final_score'].rolling(window=20).mean()
            rolling_std = df['final_score'].rolling(window=20).std()
            
            # 计算Z分数
            z_scores = (df['final_score'] - rolling_mean) / rolling_std
            
            # 标记异常值
            anomalies = df[abs(z_scores) > 2].copy()
            anomalies['z_score'] = z_scores[abs(z_scores) > 2]
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting abnormal signals: {str(e)}")
            return pd.DataFrame()
    
    @staticmethod
    def analyze_signal_quality(df: pd.DataFrame) -> Dict[str, Any]:
        """分析信号质量"""
        try:
            if df.empty:
                return {
                    'status': 'error',
                    'error': 'No data available for analysis'
                }
            
            # 计算信号质量指标
            quality_metrics = {
                'signal_to_noise_ratio': float(
                    df['final_score'].mean() / df['final_score'].std()
                    if df['final_score'].std() != 0 else 0
                ),
                'confidence_consistency': float(df['confidence'].std()),
                'volatility_consistency': float(df['volatility'].std()),
                'signal_persistence': float(
                    (df['final_score'].diff().abs() < 0.1).mean()
                )
            }
            
            # 计算时间相关性
            quality_metrics['time_correlation'] = float(
                df['final_score'].autocorr()
            )
            
            return {
                'status': 'success',
                'quality_metrics': quality_metrics
            }
            
        except Exception as e:
            logger.error(f"Error analyzing signal quality: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def generate_signal_report(df: pd.DataFrame) -> Dict[str, Any]:
        """生成信号报告"""
        try:
            if df.empty:
                return {
                    'status': 'error',
                    'error': 'No data available for report'
                }
            
            # 计算基础指标
            metrics = SignalAnalyticsEngine.calculate_metrics(df)
            quality = SignalAnalyticsEngine.analyze_signal_quality(df)
            anomalies = SignalAnalyticsEngine.detect_abnormal_signals(df)
            
            # 生成报告
            report = {
                'status': 'success',
                'report': {
                    'timestamp': datetime.now().isoformat(),
                    'period': {
                        'start': df.index[0].isoformat(),
                        'end': df.index[-1].isoformat()
                    },
                    'metrics': metrics.get('metrics', {}),
                    'quality_metrics': quality.get('quality_metrics', {}),
                    'anomalies': {
                        'count': len(anomalies),
                        'details': anomalies.to_dict('records') if not anomalies.empty else []
                    }
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating signal report: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            } 