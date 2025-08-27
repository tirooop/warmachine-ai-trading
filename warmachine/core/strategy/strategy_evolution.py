"""
策略进化系统核心模块
实现了基于遗传算法的策略优化和进化机制
"""

import os
import json
import random
import numpy as np
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

@dataclass
class StrategyDNA:
    """策略DNA类，包含所有可进化的参数"""
    spread_ratio: float
    gamma_threshold: float
    iv_skew_sensitivity: float
    theta_decay_rate: float
    hedge_frequency: int
    max_position_size: float
    stop_loss_threshold: float
    take_profit_threshold: float
    volatility_lookback: int
    correlation_threshold: float
    
    def mutate(self, config: Dict[str, Any]) -> None:
        """基于配置的变异率进行定向变异"""
        genes_config = config['strategy_evolution']['genes']
        
        for gene_name in genes_config:
            if random.random() < genes_config[gene_name]['mutation_rate']:
                current_value = getattr(self, gene_name)
                gene_config = genes_config[gene_name]
                
                # 基于历史表现调整变异方向
                profit_bias = self._get_gene_profitability(gene_name)
                mutation = (random.random() - 0.5 + profit_bias) * gene_config['mutation_strength']
                new_value = current_value * (1 + mutation)
                
                # 确保在有效范围内
                new_value = max(gene_config['min'], min(gene_config['max'], new_value))
                setattr(self, gene_name, new_value)
    
    def _get_gene_profitability(self, gene_name: str) -> float:
        """获取基因的历史盈利能力（-1到1之间）"""
        # TODO: 实现基于历史数据的盈利能力计算
        return random.random() * 2 - 1

class StrategyEvaluator:
    """策略评估器，负责评估策略的表现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics = {
            'sharpe_ratio': self._calculate_sharpe_ratio,
            'sortino_ratio': self._calculate_sortino_ratio,
            'max_drawdown': self._calculate_max_drawdown,
            'win_rate': self._calculate_win_rate,
            'profit_factor': self._calculate_profit_factor
        }
    
    async def evaluate_strategy(self, dna: StrategyDNA, market_data: pd.DataFrame) -> float:
        """评估策略的表现"""
        try:
            # 模拟策略执行
            trades = await self._simulate_strategy(dna, market_data)
            
            # 计算各项指标
            returns = self._calculate_returns(trades)
            metrics = {}
            for metric_name, metric_func in self.metrics.items():
                metrics[metric_name] = metric_func(returns)
            
            # 计算综合得分
            weights = self.config['strategy_evolution']['evaluation']['metric_weights']
            score = sum(metrics[metric] * weights[metric] for metric in metrics)
            
            # 应用风险惩罚
            risk_penalty = self._calculate_risk_penalty(metrics)
            final_score = score * (1 - risk_penalty)
            
            return final_score
            
        except Exception as e:
            logger.error(f"Strategy evaluation failed: {e}")
            return float('-inf')
    
    async def _simulate_strategy(self, dna: StrategyDNA, market_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """模拟策略执行"""
        trades = []
        position = 0
        entry_price = 0
        
        for i in range(len(market_data)):
            current_price = market_data.iloc[i]['price']
            volatility = market_data.iloc[i]['volatility']
            
            # 基于策略参数生成交易信号
            signal = self._generate_signal(dna, market_data.iloc[i])
            
            if signal != 0 and position == 0:  # 开仓
                position = signal
                entry_price = current_price
                trades.append({
                    'type': 'entry',
                    'price': current_price,
                    'timestamp': market_data.index[i],
                    'position': position
                })
            elif position != 0:  # 检查是否需要平仓
                if self._should_close_position(dna, position, entry_price, current_price, volatility):
                    trades.append({
                        'type': 'exit',
                        'price': current_price,
                        'timestamp': market_data.index[i],
                        'position': position,
                        'pnl': (current_price - entry_price) * position
                    })
                    position = 0
        
        return trades
    
    def _generate_signal(self, dna: StrategyDNA, market_data: pd.Series) -> int:
        """生成交易信号"""
        # 基于策略参数和市场数据生成交易信号
        # 返回: 1 (做多), -1 (做空), 0 (不操作)
        return 0  # TODO: 实现具体的信号生成逻辑
    
    def _should_close_position(self, dna: StrategyDNA, position: int, entry_price: float, 
                             current_price: float, volatility: float) -> bool:
        """判断是否应该平仓"""
        pnl = (current_price - entry_price) * position
        pnl_pct = pnl / entry_price
        
        # 止盈止损检查
        if pnl_pct <= -dna.stop_loss_threshold or pnl_pct >= dna.take_profit_threshold:
            return True
        
        # 波动率检查
        if volatility > dna.volatility_lookback:
            return True
        
        return False
    
    def _calculate_returns(self, trades: List[Dict[str, Any]]) -> np.ndarray:
        """计算策略收益序列"""
        returns = []
        for trade in trades:
            if trade['type'] == 'exit':
                returns.append(trade['pnl'])
        return np.array(returns)
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """计算夏普比率"""
        if len(returns) < 2:
            return 0
        return np.mean(returns) / np.std(returns) * np.sqrt(252)
    
    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float:
        """计算索提诺比率"""
        if len(returns) < 2:
            return 0
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return float('inf')
        return np.mean(returns) / np.std(downside_returns) * np.sqrt(252)
    
    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """计算最大回撤"""
        if len(returns) < 2:
            return 0
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (running_max - cumulative) / running_max
        return np.max(drawdown)
    
    def _calculate_win_rate(self, returns: np.ndarray) -> float:
        """计算胜率"""
        if len(returns) == 0:
            return 0
        return np.mean(returns > 0)
    
    def _calculate_profit_factor(self, returns: np.ndarray) -> float:
        """计算盈亏比"""
        if len(returns) == 0:
            return 0
        gross_profit = np.sum(returns[returns > 0])
        gross_loss = abs(np.sum(returns[returns < 0]))
        return gross_profit / gross_loss if gross_loss != 0 else float('inf')
    
    def _calculate_risk_penalty(self, metrics: Dict[str, float]) -> float:
        """计算风险惩罚因子"""
        max_drawdown = metrics['max_drawdown']
        volatility = metrics.get('volatility', 0)
        
        # 基于最大回撤和波动率的风险惩罚
        drawdown_penalty = max_drawdown * 2  # 最大回撤惩罚
        volatility_penalty = min(volatility, 0.5)  # 波动率惩罚
        
        return min(drawdown_penalty + volatility_penalty, 0.5)  # 最大惩罚50%

class StrategyEvolution:
    """策略进化系统主类"""
    
    def __init__(self, config_path: str = "config/strategy_evolution_config.json"):
        self.config = self._load_config(config_path)
        self.population: List[StrategyDNA] = []
        self.generation = 0
        self.best_strategy: Optional[StrategyDNA] = None
        self.best_fitness = float('-inf')
        self.evaluator = StrategyEvaluator(self.config)
        self.history: List[Dict[str, Any]] = []
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count())
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def initialize_population(self) -> None:
        """初始化策略种群"""
        genes_config = self.config['strategy_evolution']['genes']
        population_size = self.config['strategy_evolution']['evolution']['population_size']
        
        self.population = []
        for _ in range(population_size):
            dna = StrategyDNA(
                spread_ratio=random.uniform(
                    genes_config['spread_ratio']['min'],
                    genes_config['spread_ratio']['max']
                ),
                gamma_threshold=random.uniform(
                    genes_config['gamma_threshold']['min'],
                    genes_config['gamma_threshold']['max']
                ),
                iv_skew_sensitivity=random.uniform(
                    genes_config['iv_skew_sensitivity']['min'],
                    genes_config['iv_skew_sensitivity']['max']
                ),
                theta_decay_rate=random.uniform(
                    genes_config['theta_decay_rate']['min'],
                    genes_config['theta_decay_rate']['max']
                ),
                hedge_frequency=int(random.uniform(
                    genes_config['hedge_frequency']['min'],
                    genes_config['hedge_frequency']['max']
                )),
                max_position_size=random.uniform(
                    genes_config['max_position_size']['min'],
                    genes_config['max_position_size']['max']
                ),
                stop_loss_threshold=random.uniform(
                    genes_config['stop_loss_threshold']['min'],
                    genes_config['stop_loss_threshold']['max']
                ),
                take_profit_threshold=random.uniform(
                    genes_config['take_profit_threshold']['min'],
                    genes_config['take_profit_threshold']['max']
                ),
                volatility_lookback=int(random.uniform(
                    genes_config['volatility_lookback']['min'],
                    genes_config['volatility_lookback']['max']
                )),
                correlation_threshold=random.uniform(
                    genes_config['correlation_threshold']['min'],
                    genes_config['correlation_threshold']['max']
                )
            )
            self.population.append(dna)
    
    async def evolve(self, market_data: pd.DataFrame) -> None:
        """执行一代进化"""
        if not self.population:
            self.initialize_population()
        
        # 并行评估当前种群
        fitness_scores = await self._evaluate_population(market_data)
        
        # 选择最优个体
        self._select_best(fitness_scores)
        
        # 生成新一代
        new_population = self._create_next_generation()
        
        # 更新种群
        self.population = new_population
        self.generation += 1
        
        # 记录历史
        self._record_generation(fitness_scores)
        
        logger.info(f"Generation {self.generation} completed. Best fitness: {self.best_fitness}")
    
    async def _evaluate_population(self, market_data: pd.DataFrame) -> List[float]:
        """并行评估种群中每个策略的适应度"""
        tasks = []
        for dna in self.population:
            task = asyncio.create_task(
                self.evaluator.evaluate_strategy(dna, market_data)
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    def _select_best(self, fitness_scores: List[float]) -> None:
        """选择最优个体"""
        best_idx = np.argmax(fitness_scores)
        best_fitness = fitness_scores[best_idx]
        
        if best_fitness > self.best_fitness:
            self.best_fitness = best_fitness
            self.best_strategy = self.population[best_idx]
    
    def _create_next_generation(self) -> List[StrategyDNA]:
        """创建新一代种群"""
        evolution_config = self.config['strategy_evolution']['evolution']
        new_population = []
        
        # 保留最优个体
        survival_count = int(len(self.population) * evolution_config['survival_rate'])
        sorted_indices = np.argsort(self._evaluate_population())[-survival_count:]
        for idx in sorted_indices:
            new_population.append(self.population[idx])
        
        # 通过交叉和变异生成新个体
        while len(new_population) < evolution_config['population_size']:
            if random.random() < evolution_config['crossover_rate']:
                # 交叉
                parent1 = self._select_parent()
                parent2 = self._select_parent()
                child = self._crossover(parent1, parent2)
            else:
                # 变异
                parent = self._select_parent()
                child = self._mutate(parent)
            
            # 验证新个体
            if self._validate_strategy(child):
                new_population.append(child)
        
        return new_population
    
    def _select_parent(self) -> StrategyDNA:
        """使用轮盘赌选择父代"""
        fitness_scores = self._evaluate_population()
        total_fitness = sum(fitness_scores)
        if total_fitness == 0:
            return random.choice(self.population)
        
        probabilities = [score/total_fitness for score in fitness_scores]
        return np.random.choice(self.population, p=probabilities)
    
    def _crossover(self, parent1: StrategyDNA, parent2: StrategyDNA) -> StrategyDNA:
        """执行两个父代DNA的交叉操作"""
        # 使用算术交叉
        alpha = random.random()
        return StrategyDNA(
            spread_ratio=alpha * parent1.spread_ratio + (1-alpha) * parent2.spread_ratio,
            gamma_threshold=alpha * parent1.gamma_threshold + (1-alpha) * parent2.gamma_threshold,
            iv_skew_sensitivity=alpha * parent1.iv_skew_sensitivity + (1-alpha) * parent2.iv_skew_sensitivity,
            theta_decay_rate=alpha * parent1.theta_decay_rate + (1-alpha) * parent2.theta_decay_rate,
            hedge_frequency=int(alpha * parent1.hedge_frequency + (1-alpha) * parent2.hedge_frequency),
            max_position_size=alpha * parent1.max_position_size + (1-alpha) * parent2.max_position_size,
            stop_loss_threshold=alpha * parent1.stop_loss_threshold + (1-alpha) * parent2.stop_loss_threshold,
            take_profit_threshold=alpha * parent1.take_profit_threshold + (1-alpha) * parent2.take_profit_threshold,
            volatility_lookback=int(alpha * parent1.volatility_lookback + (1-alpha) * parent2.volatility_lookback),
            correlation_threshold=alpha * parent1.correlation_threshold + (1-alpha) * parent2.correlation_threshold
        )
    
    def _mutate(self, parent: StrategyDNA) -> StrategyDNA:
        """执行变异操作"""
        child = StrategyDNA(
            spread_ratio=parent.spread_ratio,
            gamma_threshold=parent.gamma_threshold,
            iv_skew_sensitivity=parent.iv_skew_sensitivity,
            theta_decay_rate=parent.theta_decay_rate,
            hedge_frequency=parent.hedge_frequency,
            max_position_size=parent.max_position_size,
            stop_loss_threshold=parent.stop_loss_threshold,
            take_profit_threshold=parent.take_profit_threshold,
            volatility_lookback=parent.volatility_lookback,
            correlation_threshold=parent.correlation_threshold
        )
        child.mutate(self.config)
        return child
    
    def _validate_strategy(self, strategy: StrategyDNA) -> bool:
        """验证策略参数的有效性"""
        # 检查参数是否在有效范围内
        genes_config = self.config['strategy_evolution']['genes']
        for gene_name in genes_config:
            value = getattr(strategy, gene_name)
            if not (genes_config[gene_name]['min'] <= value <= genes_config[gene_name]['max']):
                return False
        
        # 检查参数之间的逻辑关系
        if strategy.stop_loss_threshold >= strategy.take_profit_threshold:
            return False
        
        if strategy.hedge_frequency <= 0:
            return False
        
        return True
    
    def _record_generation(self, fitness_scores: List[float]) -> None:
        """记录当前代的信息"""
        generation_info = {
            "generation": self.generation,
            "timestamp": datetime.now().isoformat(),
            "best_fitness": self.best_fitness,
            "avg_fitness": np.mean(fitness_scores),
            "std_fitness": np.std(fitness_scores),
            "best_strategy": self.get_best_strategy()
        }
        self.history.append(generation_info)
    
    def get_best_strategy(self) -> Dict[str, Any]:
        """获取当前最优策略的信息"""
        if not self.best_strategy:
            return {}
        
        return {
            "generation": self.generation,
            "fitness": self.best_fitness,
            "genes": {
                "spread_ratio": self.best_strategy.spread_ratio,
                "gamma_threshold": self.best_strategy.gamma_threshold,
                "iv_skew_sensitivity": self.best_strategy.iv_skew_sensitivity,
                "theta_decay_rate": self.best_strategy.theta_decay_rate,
                "hedge_frequency": self.best_strategy.hedge_frequency,
                "max_position_size": self.best_strategy.max_position_size,
                "stop_loss_threshold": self.best_strategy.stop_loss_threshold,
                "take_profit_threshold": self.best_strategy.take_profit_threshold,
                "volatility_lookback": self.best_strategy.volatility_lookback,
                "correlation_threshold": self.best_strategy.correlation_threshold
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def save_history(self, filepath: str) -> None:
        """保存进化历史到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save evolution history: {e}")
    
    def load_history(self, filepath: str) -> None:
        """从文件加载进化历史"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load evolution history: {e}") 