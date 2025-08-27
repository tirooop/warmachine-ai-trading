"""
AI Feedback Learner

Processes trading results to continuously improve AI trading strategies.
Implements feedback loops for model training and strategy refinement.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pickle
import hashlib

# Import necessary modules
from ai_event_pool import AIEventPool
from ai_engine.ai_model_router import AIModelRouter

logger = logging.getLogger(__name__)

class AIFeedbackLearner:
    """
    Learns from trading results to improve AI strategies.
    Implements feedback loops for continuous improvement.
    """
    
    def __init__(self, 
                 config: Dict, 
                 event_pool: AIEventPool,
                 ai_model_router: Optional[AIModelRouter] = None):
        """
        Initialize the AI Feedback Learner.
        
        Args:
            config: Configuration dictionary
            event_pool: AI Event Pool for receiving learning data
            ai_model_router: Optional AI Model Router for LLM interactions
        """
        self.config = config
        self.event_pool = event_pool
        self.ai_model_router = ai_model_router
        
        # Learning settings
        self.learning_enabled = config.get("learning_enabled", True)
        self.min_trades_for_learning = config.get("min_trades_for_learning", 20)
        self.learning_interval = config.get("learning_interval", 24)  # hours
        self.last_learning_time = datetime.now() - timedelta(hours=self.learning_interval + 1)
        
        # Setup directories
        self.models_dir = Path(config.get("models_dir", "data/models"))
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.insights_dir = Path(config.get("insights_dir", "data/insights"))
        self.insights_dir.mkdir(parents=True, exist_ok=True)
        
        # Learning data storage
        self.trade_data = []
        self.strategy_performance = {}
        self.market_conditions = {}
        
        # Strategy improvements
        self.strategy_improvements = []
        
        # Register event handlers
        self._register_event_handlers()
        
        # Load existing learning data
        self._load_learning_data()
        
        logger.info("AI Feedback Learner initialized")
    
    def _register_event_handlers(self):
        """Register handlers for AI learning events"""
        if self.event_pool:
            self.event_pool.register_handler("AI_LEARNING_DATA", self._handle_learning_data)
            logger.info("Event handlers registered")
    
    def _handle_learning_data(self, event_data: Dict):
        """
        Handle incoming learning data from the trading system.
        
        Args:
            event_data: Learning data event
        """
        try:
            logger.debug(f"Received learning data: {event_data}")
            
            # Extract relevant data
            recent_trades = event_data.get("recent_trades", [])
            performance_metrics = event_data.get("performance_metrics", {})
            portfolio_state = event_data.get("portfolio_state", {})
            
            # Store trade data for learning
            self.trade_data.extend(recent_trades)
            
            # Update strategy performance metrics
            for trade in recent_trades:
                strategy = trade.get("strategy", "UNKNOWN")
                if strategy not in self.strategy_performance:
                    self.strategy_performance[strategy] = {
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0,
                        "total_pnl": 0,
                        "avg_win": 0,
                        "avg_loss": 0,
                        "largest_win": 0,
                        "largest_loss": 0,
                        "win_rate": 0
                    }
                
                # Update metrics for this strategy
                perf = self.strategy_performance[strategy]
                perf["total_trades"] += 1
                
                pnl = trade.get("pnl", 0)
                if pnl > 0:
                    perf["winning_trades"] += 1
                    perf["avg_win"] = ((perf["avg_win"] * (perf["winning_trades"] - 1)) + pnl) / perf["winning_trades"]
                    perf["largest_win"] = max(perf["largest_win"], pnl)
                elif pnl < 0:
                    perf["losing_trades"] += 1
                    perf["avg_loss"] = ((perf["avg_loss"] * (perf["losing_trades"] - 1)) + pnl) / perf["losing_trades"]
                    perf["largest_loss"] = min(perf["largest_loss"], pnl)
                
                perf["total_pnl"] += pnl
                if perf["total_trades"] > 0:
                    perf["win_rate"] = perf["winning_trades"] / perf["total_trades"]
            
            # Check if it's time to perform learning
            self._check_and_perform_learning()
            
            # Save learning data periodically
            self._save_learning_data()
            
        except Exception as e:
            logger.error(f"Error handling learning data: {str(e)}")
    
    def _check_and_perform_learning(self):
        """Check if conditions are met to perform learning and execute if necessary"""
        # Check if learning is enabled
        if not self.learning_enabled:
            return
        
        # Check if we have enough data
        if len(self.trade_data) < self.min_trades_for_learning:
            logger.debug(f"Not enough trades for learning: {len(self.trade_data)}/{self.min_trades_for_learning}")
            return
        
        # Check if enough time has passed since last learning
        time_since_last = datetime.now() - self.last_learning_time
        if time_since_last.total_seconds() < self.learning_interval * 3600:
            logger.debug(f"Not enough time elapsed since last learning: {time_since_last.total_seconds()/3600:.2f} hrs")
            return
        
        # Perform learning
        logger.info("Performing AI learning...")
        self._perform_learning()
        self.last_learning_time = datetime.now()
    
    def _perform_learning(self):
        """Perform learning from collected trade data"""
        try:
            # Convert trade data to DataFrame for analysis
            trades_df = pd.DataFrame(self.trade_data)
            
            # Skip if no data
            if trades_df.empty:
                logger.warning("No trade data available for learning")
                return
            
            # Format datetime columns
            for col in ['entry_time', 'exit_time']:
                if col in trades_df.columns:
                    trades_df[col] = pd.to_datetime(trades_df[col])
            
            # Generate strategy insights
            self._generate_strategy_insights(trades_df)
            
            # Generate pattern insights
            self._generate_pattern_insights(trades_df)
            
            # Use AI model router to analyze performance if available
            if self.ai_model_router:
                self._generate_ai_analysis(trades_df)
            
            # Update strategies based on learnings
            self._update_strategies()
            
            # Clear processed data
            self._prune_learning_data()
            
            logger.info("Learning complete, insights generated")
            
        except Exception as e:
            logger.error(f"Error during learning process: {str(e)}")
    
    def _generate_strategy_insights(self, trades_df: pd.DataFrame):
        """
        Generate insights about strategy performance.
        
        Args:
            trades_df: DataFrame containing trade history
        """
        try:
            # Group by strategy
            strategy_groups = trades_df.groupby('strategy')
            
            # Calculate performance metrics by strategy
            insights = {}
            
            for strategy, group in strategy_groups:
                # Skip if too few trades
                if len(group) < 5:  # Need at least 5 trades to make meaningful conclusions
                    continue
                
                # Calculate win rate
                win_rate = len(group[group['pnl'] > 0]) / len(group)
                
                # Calculate risk-reward ratio
                avg_win = group[group['pnl'] > 0]['pnl'].mean() if len(group[group['pnl'] > 0]) > 0 else 0
                avg_loss = abs(group[group['pnl'] < 0]['pnl'].mean()) if len(group[group['pnl'] < 0]) > 0 else 1  # Avoid div by zero
                risk_reward = avg_win / avg_loss if avg_loss != 0 else 0
                
                # Calculate expectancy
                expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
                
                # Calculate sharpe-like ratio (if enough data)
                pnl_series = group['pnl']
                sharpe = pnl_series.mean() / pnl_series.std() if pnl_series.std() != 0 else 0
                
                # Store insights
                insights[strategy] = {
                    "trade_count": len(group),
                    "win_rate": win_rate,
                    "risk_reward": risk_reward,
                    "expectancy": expectancy,
                    "sharpe": sharpe,
                    "avg_win": avg_win,
                    "avg_loss": avg_loss,
                    "net_pnl": group['pnl'].sum(),
                    "recommendation": self._get_strategy_recommendation(win_rate, risk_reward, expectancy)
                }
            
            # Save insights
            today = datetime.now().strftime("%Y-%m-%d")
            insights_path = self.insights_dir / f"strategy_insights_{today}.json"
            with open(insights_path, 'w') as f:
                # Convert values to serializable format
                serializable_insights = {k: {kk: float(vv) if isinstance(vv, (np.float32, np.float64)) else vv 
                                         for kk, vv in v.items()} 
                                      for k, v in insights.items()}
                json.dump(serializable_insights, f, indent=2)
            
            # Store for system use
            self.strategy_insights = insights
            
        except Exception as e:
            logger.error(f"Error generating strategy insights: {str(e)}")
    
    def _get_strategy_recommendation(self, win_rate: float, risk_reward: float, expectancy: float) -> str:
        """
        Get a recommendation for a strategy based on its metrics.
        
        Args:
            win_rate: Win rate of the strategy
            risk_reward: Risk-reward ratio of the strategy
            expectancy: Expectancy of the strategy
            
        Returns:
            Recommendation string
        """
        if expectancy <= 0:
            return "STOP_USING"
        elif win_rate < 0.4 and risk_reward < 1.5:
            return "NEEDS_IMPROVEMENT"
        elif win_rate >= 0.5 or risk_reward >= 2.0:
            return "KEEP_USING"
        else:
            return "MONITOR"
    
    def _generate_pattern_insights(self, trades_df: pd.DataFrame):
        """
        Generate insights about patterns in successful and unsuccessful trades.
        
        Args:
            trades_df: DataFrame containing trade history
        """
        try:
            # Skip if too few trades
            if len(trades_df) < 10:
                return
            
            # Add time-based features
            if 'entry_time' in trades_df.columns:
                trades_df['hour'] = trades_df['entry_time'].dt.hour
                trades_df['day_of_week'] = trades_df['entry_time'].dt.dayofweek
                
                # Group by time features
                hour_performance = trades_df.groupby('hour')['pnl'].mean()
                day_performance = trades_df.groupby('day_of_week')['pnl'].mean()
                
                # Find best and worst times
                best_hour = hour_performance.idxmax()
                worst_hour = hour_performance.idxmin()
                best_day = day_performance.idxmax()
                worst_day = day_performance.idxmin()
                
                # Convert day numbers to names
                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                best_day_name = day_names[best_day]
                worst_day_name = day_names[worst_day]
                
                # Create insights
                time_insights = {
                    "best_hour": int(best_hour),
                    "worst_hour": int(worst_hour),
                    "best_day": best_day_name,
                    "worst_day": worst_day_name,
                    "hour_performance": {str(k): float(v) for k, v in hour_performance.items()},
                    "day_performance": {day_names[k]: float(v) for k, v in day_performance.items()}
                }
                
                # Save insights
                today = datetime.now().strftime("%Y-%m-%d")
                insights_path = self.insights_dir / f"time_pattern_insights_{today}.json"
                with open(insights_path, 'w') as f:
                    json.dump(time_insights, f, indent=2)
            
            # Analyze symbols
            if 'symbol' in trades_df.columns:
                symbol_performance = trades_df.groupby('symbol')['pnl'].agg(['mean', 'count'])
                # Filter to symbols with at least 3 trades
                symbol_performance = symbol_performance[symbol_performance['count'] >= 3]
                
                if not symbol_performance.empty:
                    # Sort by average P&L
                    symbol_performance = symbol_performance.sort_values('mean', ascending=False)
                    
                    # Create insights
                    symbol_insights = {
                        "best_symbols": symbol_performance.head(3).index.tolist(),
                        "worst_symbols": symbol_performance.tail(3).index.tolist(),
                        "symbol_performance": {
                            k: {"avg_pnl": float(v['mean']), "trade_count": int(v['count'])} 
                            for k, v in symbol_performance.iterrows()
                        }
                    }
                    
                    # Save insights
                    symbol_insights_path = self.insights_dir / f"symbol_insights_{today}.json"
                    with open(symbol_insights_path, 'w') as f:
                        json.dump(symbol_insights, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating pattern insights: {str(e)}")
    
    def _generate_ai_analysis(self, trades_df: pd.DataFrame):
        """
        Use AI to analyze trade performance and suggest improvements.
        
        Args:
            trades_df: DataFrame containing trade history
        """
        try:
            if self.ai_model_router is None:
                logger.warning("AI Model Router not available, skipping AI analysis")
                return
            
            # Prepare trade data for AI analysis
            # Get the most recent 50 trades for analysis
            recent_trades = trades_df.sort_values('entry_time', ascending=False).head(50)
            
            # Format trade data for AI
            trade_records = []
            for _, trade in recent_trades.iterrows():
                record = (
                    f"Symbol: {trade.get('symbol', 'Unknown')}, "
                    f"Action: {trade.get('action', 'Unknown')}, "
                    f"Entry: ${trade.get('entry_price', 0):.2f}, "
                    f"Exit: ${trade.get('exit_price', 0):.2f}, "
                    f"P&L: ${trade.get('pnl', 0):.2f}, "
                    f"Strategy: {trade.get('strategy', 'Unknown')}, "
                    f"Confidence: {trade.get('confidence', 0):.2f}"
                )
                trade_records.append(record)
            
            # Prepare performance summary
            performance_summary = "Strategy Performance Summary:\n"
            for strategy, metrics in self.strategy_performance.items():
                if metrics["total_trades"] > 0:
                    performance_summary += (
                        f"- {strategy}: {metrics['total_trades']} trades, "
                        f"Win Rate: {metrics['win_rate']:.2f}, "
                        f"Net P&L: ${metrics['total_pnl']:.2f}\n"
                    )
            
            # Create prompt for AI
            prompt = (
                "Based on the following recent trades and performance metrics, "
                "analyze what's working well and what could be improved. "
                "Focus on patterns in winning vs. losing trades, optimal market conditions, "
                "and recommendations for strategy adjustments. "
                "Provide 3-5 specific, actionable recommendations to improve trading performance.\n\n"
                f"{performance_summary}\n\n"
                "Recent Trades:\n" + "\n".join(trade_records)
            )
            
            # Get AI analysis
            ai_response = self.ai_model_router.generate_text(prompt, max_tokens=1000)
            
            if ai_response:
                # Save AI analysis
                today = datetime.now().strftime("%Y-%m-%d")
                analysis_path = self.insights_dir / f"ai_analysis_{today}.txt"
                with open(analysis_path, 'w') as f:
                    f.write(ai_response)
                
                # Extract recommendations for system use
                recommendations = self._extract_recommendations(ai_response)
                
                # Store recommendations for system use
                self.strategy_improvements.extend(recommendations)
                
                # Save recommendations separately
                recommendations_path = self.insights_dir / f"ai_recommendations_{today}.json"
                with open(recommendations_path, 'w') as f:
                    json.dump(recommendations, f, indent=2)
                
                logger.info(f"AI analysis completed with {len(recommendations)} recommendations")
            else:
                logger.warning("AI did not provide any analysis")
            
        except Exception as e:
            logger.error(f"Error generating AI analysis: {str(e)}")
    
    def _extract_recommendations(self, ai_text: str) -> List[Dict]:
        """
        Extract actionable recommendations from AI text.
        
        Args:
            ai_text: Text generated by AI
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        try:
            # Split by lines and look for numbered items or bullet points
            lines = ai_text.split("\n")
            current_rec = None
            
            for line in lines:
                line = line.strip()
                
                # Check for bullet points or numbered items that might be recommendations
                if (line.startswith("- ") or 
                    line.startswith("• ") or 
                    line.startswith("* ") or
                    (line[0].isdigit() and line[1:3] in [". ", ") "])):
                    
                    # Clean the line
                    rec_text = line.lstrip("- •*0123456789.) ")
                    
                    # Create recommendation object
                    current_rec = {
                        "text": rec_text,
                        "id": hashlib.md5(rec_text.encode()).hexdigest()[:8],
                        "timestamp": datetime.now().isoformat(),
                        "implemented": False,
                        "result": None
                    }
                    recommendations.append(current_rec)
                elif current_rec and line:
                    # Continuation of previous recommendation
                    current_rec["text"] += " " + line
            
            # If we didn't find structured recommendations, try to extract them differently
            if len(recommendations) == 0 and ai_text:
                # Just use paragraphs as recommendations
                paragraphs = [p.strip() for p in ai_text.split("\n\n") if p.strip()]
                for p in paragraphs[:5]:  # Take up to 5 paragraphs
                    if len(p) > 20:  # Only if substantial content
                        recommendations.append({
                            "text": p,
                            "id": hashlib.md5(p.encode()).hexdigest()[:8],
                            "timestamp": datetime.now().isoformat(),
                            "implemented": False,
                            "result": None
                        })
        except Exception as e:
            logger.error(f"Error extracting recommendations: {str(e)}")
        
        return recommendations
    
    def _update_strategies(self):
        """Update strategies based on learned insights"""
        # For now, just publish strategy improvement events
        if self.strategy_improvements:
            for improvement in self.strategy_improvements:
                if not improvement.get("implemented", False):
                    # Create event for strategy improvement
                    event_data = {
                        "event_type": "STRATEGY_IMPROVEMENT",
                        "timestamp": datetime.now().isoformat(),
                        "recommendation": improvement
                    }
                    
                    # Publish event
                    self.event_pool.publish_event("STRATEGY_IMPROVEMENT", event_data)
                    
                    # Mark as implemented
                    improvement["implemented"] = True
                    logger.info(f"Published strategy improvement: {improvement['text']}")
    
    def _prune_learning_data(self):
        """Prune old learning data to avoid using too much memory"""
        # Keep only the most recent 1000 trades
        if len(self.trade_data) > 1000:
            self.trade_data = sorted(
                self.trade_data, 
                key=lambda x: datetime.fromisoformat(x.get('entry_time', datetime.now().isoformat())),
                reverse=True
            )[:1000]
    
    def _save_learning_data(self):
        """Save current learning data"""
        try:
            data = {
                "trade_data": self.trade_data,
                "strategy_performance": self.strategy_performance,
                "last_learning_time": self.last_learning_time.isoformat(),
                "strategy_improvements": self.strategy_improvements
            }
            
            # Save to file
            data_path = self.models_dir / "learning_data.pkl"
            with open(data_path, 'wb') as f:
                pickle.dump(data, f)
                
            logger.debug("Learning data saved")
        except Exception as e:
            logger.error(f"Error saving learning data: {str(e)}")
    
    def _load_learning_data(self):
        """Load existing learning data if available"""
        try:
            data_path = self.models_dir / "learning_data.pkl"
            if data_path.exists():
                with open(data_path, 'rb') as f:
                    data = pickle.load(f)
                
                # Load saved data
                self.trade_data = data.get("trade_data", [])
                self.strategy_performance = data.get("strategy_performance", {})
                last_learning_time_str = data.get("last_learning_time")
                if last_learning_time_str:
                    self.last_learning_time = datetime.fromisoformat(last_learning_time_str)
                self.strategy_improvements = data.get("strategy_improvements", [])
                
                logger.info(f"Loaded existing learning data: {len(self.trade_data)} trades")
        except Exception as e:
            logger.error(f"Error loading learning data: {str(e)}")
    
    def get_strategy_insights(self) -> Dict:
        """
        Get current strategy insights.
        
        Returns:
            Dictionary of strategy insights
        """
        return getattr(self, "strategy_insights", {})
    
    def get_improvement_recommendations(self) -> List[Dict]:
        """
        Get current improvement recommendations.
        
        Returns:
            List of improvement recommendation dictionaries
        """
        return self.strategy_improvements
    
    def stop(self):
        """Stop the AI Feedback Learner"""
        logger.info("Stopping AI Feedback Learner...")
        # Save current learning data
        self._save_learning_data() 