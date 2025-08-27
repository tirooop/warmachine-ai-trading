"""
Backtest Engine Module
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self):
        """初始化回测引擎"""
        self._backtest_results = None
        self._backtest_history = []
        
    def run_backtest(self, 
                    start_date: str,
                    end_date: str,
                    initial_capital: float = 100000.0,
                    strategy_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行回测"""
        try:
            # 生成示例回测数据
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            prices = np.random.normal(100, 10, len(dates))
            signals = np.random.choice([-1, 0, 1], len(dates))
            
            # 创建回测数据框
            df = pd.DataFrame({
                'date': dates,
                'price': prices,
                'signal': signals
            })
            
            # 计算持仓
            df['position'] = df['signal'].cumsum()
            
            # 计算收益
            df['returns'] = df['price'].pct_change()
            df['strategy_returns'] = df['position'].shift(1) * df['returns']
            
            # 计算累积收益
            df['cumulative_returns'] = (1 + df['returns']).cumprod()
            df['strategy_cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
            
            # 计算回撤
            df['drawdown'] = df['strategy_cumulative_returns'] / df['strategy_cumulative_returns'].cummax() - 1
            
            # 生成交易记录
            trades = []
            for i in range(1, len(df)):
                if df['signal'].iloc[i] != 0:
                    trades.append({
                        'timestamp': df['date'].iloc[i].isoformat(),
                        'price': df['price'].iloc[i],
                        'signal': df['signal'].iloc[i],
                        'position': df['position'].iloc[i],
                        'returns': df['strategy_returns'].iloc[i]
                    })
            
            # 计算回测指标
            total_return = df['strategy_cumulative_returns'].iloc[-1] - 1
            sharpe_ratio = np.sqrt(252) * df['strategy_returns'].mean() / df['strategy_returns'].std()
            max_drawdown = df['drawdown'].min()
            win_rate = len(df[df['strategy_returns'] > 0]) / len(df[df['strategy_returns'] != 0])
            
            # 保存回测结果
            self._backtest_results = {
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'trades': trades,
                'equity_curve': df['strategy_cumulative_returns'].tolist(),
                'drawdown': df['drawdown'].tolist()
            }
            
            # 记录回测历史
            self._backtest_history.append({
                'timestamp': datetime.now().isoformat(),
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'strategy_params': strategy_params,
                'results': self._backtest_results.copy()
            })
            
            return {
                'status': 'success',
                'results': self._backtest_results
            }
            
        except Exception as e:
            logger.error(f"Error running backtest: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def get_backtest_results(self) -> Dict[str, Any]:
        """获取回测结果"""
        if self._backtest_results is None:
            return {
                'status': 'error',
                'error': 'No backtest results available'
            }
            
        return {
            'status': 'success',
            'results': self._backtest_results
        }
        
    def get_backtest_history(self) -> List[Dict[str, Any]]:
        """获取回测历史"""
        return self._backtest_history.copy()
        
    def clear_backtest_history(self):
        """清除回测历史"""
        self._backtest_history.clear()
        self._backtest_results = None
        
    def get_backtest_report(self) -> Dict[str, Any]:
        """获取回测报告"""
        try:
            if self._backtest_results is None:
                return {
                    'status': 'error',
                    'error': 'No backtest results available'
                }
                
            # 生成回测报告
            return {
                'status': 'success',
                'report': {
                    'timestamp': datetime.now().isoformat(),
                    'results': self._backtest_results,
                    'history_size': len(self._backtest_history)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting backtest report: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def export_backtest_results(self, file_path: str) -> Dict[str, Any]:
        """导出回测结果"""
        try:
            if self._backtest_results is None:
                return {
                    'status': 'error',
                    'error': 'No backtest results available'
                }
                
            # 创建回测结果数据框
            df = pd.DataFrame(self._backtest_results['trades'])
            
            # 导出到CSV文件
            df.to_csv(file_path, index=False)
            
            return {
                'status': 'success',
                'message': f'Backtest results exported to {file_path}'
            }
            
        except Exception as e:
            logger.error(f"Error exporting backtest results: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            } 