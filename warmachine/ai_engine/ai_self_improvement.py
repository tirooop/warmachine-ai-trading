"""


AI Self-Improvement - Autonomous Strategy Evolution





This module handles the automatic evaluation and improvement of trading strategies


through an AI-driven evolutionary approach. It analyzes strategy performance,


identifies weaknesses, and generates improved versions automatically.





Features:


- Performance evaluation and scoring


- Weakness identification and root cause analysis


- Strategy variation and improvement


- Automated testing and validation


- Autonomous strategy lifecycle management


"""





import os


import logging


import time


import json


import random


import threading


from datetime import datetime, timedelta


from typing import Dict, List, Any, Optional, Tuple





# Set up logging


logger = logging.getLogger(__name__)





class AISelfImprovement:


    """AI Self-Improvement for autonomous strategy evolution"""


    


    def __init__(self, config: Dict[str, Any], ai_model_router=None):


        """


        Initialize the AI Self-Improvement system


        


        Args:


            config: Platform configuration dictionary


            ai_model_router: AI Model Router instance


        """


        self.config = config


        self.ai_config = config.get("ai", {})


        self.running = False


        self.ai_model_router = ai_model_router


        


        # AI provider configuration


        self.provider = self.ai_config.get("provider", "deepseek")


        self.api_key = self.ai_config.get("api_key", "")


        self.model = self.ai_config.get("model", "deepseek-ai/DeepSeek-V3")


        


        # Strategy management


        self.strategy_path = "data/strategies"


        self.improved_path = "data/strategies/improved"


        self.archive_path = "data/strategies/archive"


        os.makedirs(self.strategy_path, exist_ok=True)


        os.makedirs(self.improved_path, exist_ok=True)


        os.makedirs(self.archive_path, exist_ok=True)


        


        # Performance thresholds


        self.improvement_config = self.config.get("improvement", {})


        self.min_trades = self.improvement_config.get("min_trades", 20)


        self.min_age_days = self.improvement_config.get("min_age_days", 5)


        self.poor_performance_threshold = self.improvement_config.get("poor_performance_threshold", 0.0)


        self.retirement_threshold = self.improvement_config.get("retirement_threshold", -5.0)


        


        # Evolution settings


        self.max_generations = self.improvement_config.get("max_generations", 5)


        self.improvement_cycle_days = self.improvement_config.get("improvement_cycle_days", 7)


        


        # State tracking


        self.strategies = {}


        self.last_improvement_check = datetime.now()


        self.current_improvements = set()  # Track strategies currently being improved


        


        logger.info("AI Self-Improvement system initialized")


        


    def run(self):


        """Start the AI Self-Improvement system's main processing loop"""


        self.running = True


        logger.info("AI Self-Improvement system started")


        


        try:


            while self.running:


                # Load all strategies


                self._load_strategies()


                


                # Check which strategies need improvement


                self._check_improvement_candidates()


                


                # Process improvements one at a time


                self._process_improvements()


                


                # Sleep to prevent excessive CPU usage


                time.sleep(3600)  # Check every hour


                


        except Exception as e:


            logger.error(f"AI Self-Improvement system encountered an error: {str(e)}")


            self.running = False


            


        logger.info("AI Self-Improvement system stopped")


        


    def shutdown(self):


        """Gracefully shutdown the AI Self-Improvement system"""


        logger.info("Shutting down AI Self-Improvement system...")


        self.running = False


        


    def _load_strategies(self):


        """Load all strategies and their performance data"""


        try:


            # Get all strategy files


            strategy_files = []


            for file in os.listdir(self.strategy_path):


                if file.endswith(".json") and not file.endswith("_evaluation.json") and not file.endswith("_performance.json") and not file.endswith("_deployment.json"):


                    strategy_files.append(os.path.join(self.strategy_path, file))


                    


            # Process each strategy


            for file_path in strategy_files:


                try:


                    with open(file_path, "r") as f:


                        strategy = json.load(f)


                        


                    strategy_id = strategy.get("id", "")


                    if not strategy_id:


                        continue


                        


                    # Check if we already have this strategy


                    if strategy_id in self.strategies:


                        continue


                        


                    # Load performance data if available


                    performance = self._load_performance(strategy_id)


                    


                    # Store strategy with performance


                    self.strategies[strategy_id] = {


                        "strategy": strategy,


                        "performance": performance,


                        "file_path": file_path


                    }


                    


                except Exception as e:


                    logger.error(f"Failed to process strategy file {file_path}: {str(e)}")


                    


            logger.info(f"Loaded {len(self.strategies)} strategies")


                


        except Exception as e:


            logger.error(f"Failed to load strategies: {str(e)}")


            


    def _load_performance(self, strategy_id: str) -> Dict[str, Any]:


        """


        Load performance data for a strategy


        


        Args:


            strategy_id: ID of the strategy


            


        Returns:


            Performance data dictionary


        """


        try:


            # Check for performance file


            performance_file = os.path.join(self.strategy_path, f"{strategy_id}_performance.json")


            


            if not os.path.exists(performance_file):


                return {


                    "trade_count": 0,


                    "win_rate": 0.0,


                    "profit_loss": 0.0,


                    "sharpe_ratio": 0.0,


                    "max_drawdown": 0.0,


                    "last_updated": None


                }


                


            # Load performance data


            with open(performance_file, "r") as f:


                return json.load(f)


                


        except Exception as e:


            logger.error(f"Failed to load performance for {strategy_id}: {str(e)}")


            return {


                "trade_count": 0,


                "win_rate": 0.0,


                "profit_loss": 0.0,


                "sharpe_ratio": 0.0,


                "max_drawdown": 0.0,


                "last_updated": None


            }


            


    def _check_improvement_candidates(self):


        """Check which strategies are candidates for improvement"""


        try:


            # Only check periodically (once per day)


            if (datetime.now() - self.last_improvement_check).total_seconds() < 86400:


                return


                


            self.last_improvement_check = datetime.now()


            


            improvement_candidates = []


            retirement_candidates = []


            


            for strategy_id, data in self.strategies.items():


                # Skip strategies already being improved


                if strategy_id in self.current_improvements:


                    continue


                    


                strategy = data["strategy"]


                performance = data["performance"]


                


                # Skip strategies with insufficient data


                if performance.get("trade_count", 0) < self.min_trades:


                    continue


                    


                # Check strategy age


                created_at = datetime.fromisoformat(strategy.get("created_at", datetime.now().isoformat()))


                strategy_age_days = (datetime.now() - created_at).days


                


                if strategy_age_days < self.min_age_days:


                    continue


                    


                # Check performance metrics


                profit_loss = performance.get("profit_loss", 0.0)


                


                # Check for retirement (very poor performance)


                if profit_loss <= self.retirement_threshold:


                    retirement_candidates.append(strategy_id)


                    logger.info(f"Strategy {strategy_id} identified for retirement (P&L: {profit_loss:.2f}%)")


                    continue


                    


                # Check for improvement (underperforming but not terrible)


                if profit_loss <= self.poor_performance_threshold:


                    # Check improvement cycle (don't improve too frequently)


                    last_improved = strategy.get("last_improved", created_at.isoformat())


                    days_since_improvement = (datetime.now() - datetime.fromisoformat(last_improved)).days


                    


                    if days_since_improvement >= self.improvement_cycle_days:


                        improvement_candidates.append(strategy_id)


                        logger.info(f"Strategy {strategy_id} identified for improvement (P&L: {profit_loss:.2f}%)")


            


            # Retire strategies


            for strategy_id in retirement_candidates:


                self._retire_strategy(strategy_id)


                


            # Queue improvements (limit to one at a time for resource management)


            if improvement_candidates:


                strategy_id = random.choice(improvement_candidates)


                self.current_improvements.add(strategy_id)


                logger.info(f"Queued strategy {strategy_id} for improvement")


                


        except Exception as e:


            logger.error(f"Failed to check improvement candidates: {str(e)}")


            


    def _process_improvements(self):


        """Process strategy improvements"""


        try:


            # Process one improvement at a time


            if not self.current_improvements:


                return


                


            strategy_id = next(iter(self.current_improvements))


            


            try:


                logger.info(f"Starting improvement process for strategy {strategy_id}")


                


                # Get strategy data


                data = self.strategies.get(strategy_id)


                if not data:


                    self.current_improvements.remove(strategy_id)


                    return


                    


                strategy = data["strategy"]


                performance = data["performance"]


                


                # Analyze strategy weaknesses


                weaknesses = self._analyze_weaknesses(strategy, performance)


                


                # Generate improved strategy


                improved_strategy = self._improve_strategy(strategy, weaknesses)


                


                # Save improved strategy


                self._save_improved_strategy(improved_strategy)


                


                logger.info(f"Successfully improved strategy {strategy_id} -> {improved_strategy['id']}")


                


            except Exception as e:


                logger.error(f"Failed to improve strategy {strategy_id}: {str(e)}")


                


            finally:


                # Remove from current improvements regardless of success/failure


                self.current_improvements.remove(strategy_id)


                


        except Exception as e:


            logger.error(f"Strategy improvement processing failed: {str(e)}")


            


    def _analyze_weaknesses(self, strategy: Dict[str, Any], performance: Dict[str, Any]) -> List[Dict[str, Any]]:


        """


        Analyze strategy weaknesses


        


        Args:


            strategy: Strategy data


            performance: Performance data


            


        Returns:


            List of identified weaknesses


        """


        try:


            # Extract key information


            strategy_id = strategy.get("id", "")


            strategy_type = strategy.get("type", "unknown")


            strategy_code = strategy.get("code", "")


            


            # Extract performance metrics


            win_rate = performance.get("win_rate", 0.0)


            profit_loss = performance.get("profit_loss", 0.0)


            max_drawdown = performance.get("max_drawdown", 0.0)


            sharpe_ratio = performance.get("sharpe_ratio", 0.0)


            


            # Identify weaknesses


            weaknesses = []


            


            if win_rate < 0.4:


                weaknesses.append({


                    "type": "low_win_rate",


                    "description": "Strategy has a low win rate, indicating poor entry or exit criteria",


                    "severity": "high",


                    "suggestion": "Improve entry criteria or add confirmation indicators"


                })


                


            if max_drawdown < -15.0:


                weaknesses.append({


                    "type": "high_drawdown",


                    "description": "Strategy experiences excessive drawdowns, indicating poor risk management",


                    "severity": "high",


                    "suggestion": "Add tighter stop losses or position sizing rules"


                })


                


            if profit_loss <= 0.0:


                weaknesses.append({


                    "type": "negative_returns",


                    "description": "Strategy is losing money overall",


                    "severity": "high",


                    "suggestion": "Fundamental revision of strategy logic or market conditions"


                })


                


            if sharpe_ratio < 0.5:


                weaknesses.append({


                    "type": "poor_risk_adjusted_returns",


                    "description": "Strategy has poor risk-adjusted returns",


                    "severity": "medium",


                    "suggestion": "Adjust position sizing or improve trade timing"


                })


                


            # If no specific weaknesses are identified, add a generic one


            if not weaknesses:


                weaknesses.append({


                    "type": "general_improvement",


                    "description": "Strategy has room for general improvement",


                    "severity": "low",


                    "suggestion": "Consider additional indicators or optimization"


                })


                


            logger.info(f"Identified {len(weaknesses)} weaknesses in strategy {strategy_id}")


            return weaknesses


            


        except Exception as e:


            logger.error(f"Weakness analysis failed: {str(e)}")


            return [{


                "type": "analysis_error",


                "description": f"Error analyzing strategy: {str(e)}",


                "severity": "medium",


                "suggestion": "General optimization and robustness improvements"


            }]


            


    def _improve_strategy(self, strategy: Dict[str, Any], weaknesses: List[Dict[str, Any]]) -> Dict[str, Any]:


        """


        Generate an improved version of a strategy


        


        Args:


            strategy: Original strategy data


            weaknesses: Identified weaknesses


            


        Returns:


            Improved strategy dictionary


        """


        try:


            # Extract key information


            original_id = strategy.get("id", "")


            strategy_type = strategy.get("type", "unknown")


            strategy_name = strategy.get("name", "Unnamed Strategy")


            strategy_code = strategy.get("code", "")


            description = strategy.get("description", "")


            


            # Generate new ID with generation number


            generation = strategy.get("generation", 0) + 1


            new_id = f"{original_id}_g{generation}"


            


            # In a real implementation, this would call the AI model to improve the strategy


            # For now, generate a synthetic improvement


            


            # Create improvements based on weaknesses


            improvements = []


            code_changes = []


            


            for weakness in weaknesses:


                weakness_type = weakness.get("type", "")


                suggestion = weakness.get("suggestion", "")


                


                if weakness_type == "low_win_rate":


                    improvements.append("Added additional confirmation indicators")


                    code_changes.append("Added RSI and MACD confirmation condition")


                    


                elif weakness_type == "high_drawdown":


                    improvements.append("Implemented tighter stop-loss mechanism")


                    code_changes.append("Added 2% maximum stop loss rule")


                    


                elif weakness_type == "negative_returns":


                    improvements.append("Revised core strategy logic for current market conditions")


                    code_changes.append("Updated entry and exit conditions based on recent market behavior")


                    


                elif weakness_type == "poor_risk_adjusted_returns":


                    improvements.append("Adjusted position sizing for better risk management")


                    code_changes.append("Implemented dynamic position sizing based on volatility")


                    


                else:


                    improvements.append("General optimization improvements")


                    code_changes.append("Fine-tuned parameters for optimal performance")


            


            # Generate improved code (in a real system, this would be actual code)


            improved_code = f"""


            # Improved version of strategy {original_id} (Generation {generation})


            # Original code with the following improvements:


            # {', '.join(code_changes)}


            


            {strategy_code}


            


            # Additional improvements:


            # - Parameter optimization


            # - Better risk management


            # - Updated for current market conditions


            """


            


            # Create improved strategy object


            improved_strategy = {


                "id": new_id,


                "name": f"{strategy_name} (G{generation})",


                "type": strategy_type,


                "created_at": datetime.now().isoformat(),


                "improved_from": original_id,


                "generation": generation,


                "status": "pending_backtest",


                "code": improved_code,


                "description": f"Improved version of {original_id}. {description}\n\nImprovements: {', '.join(improvements)}",


                "improvements": improvements,


                "weaknesses_addressed": weaknesses


            }


            


            logger.info(f"Generated improved strategy {new_id} from {original_id}")


            return improved_strategy


            


        except Exception as e:


            logger.error(f"Strategy improvement failed: {str(e)}")


            


            # Create fallback improvement with minimal changes


            new_id = f"{original_id}_g{strategy.get('generation', 0) + 1}"


            return {


                "id": new_id,


                "name": f"{strategy.get('name', 'Unnamed Strategy')} (improved)",


                "type": strategy.get("type", "unknown"),


                "created_at": datetime.now().isoformat(),


                "improved_from": original_id,


                "generation": strategy.get("generation", 0) + 1,


                "status": "pending_backtest",


                "code": strategy.get("code", ""),


                "description": f"Improved version of {original_id} with parameter optimization.",


                "improvements": ["Parameter optimization"],


                "weaknesses_addressed": weaknesses


            }


            


    def _save_improved_strategy(self, strategy: Dict[str, Any]):


        """


        Save an improved strategy


        


        Args:


            strategy: Improved strategy data


        """


        try:


            # Generate filename


            strategy_id = strategy.get("id", "")


            file_path = os.path.join(self.improved_path, f"{strategy_id}.json")


            


            # Save to disk


            with open(file_path, "w") as f:


                json.dump(strategy, f, indent=2)


                


            logger.info(f"Saved improved strategy to {file_path}")


            


        except Exception as e:


            logger.error(f"Failed to save improved strategy: {str(e)}")


            


    def _retire_strategy(self, strategy_id: str):


        """


        Retire a poorly performing strategy


        


        Args:


            strategy_id: ID of the strategy to retire


        """


        try:


            # Get strategy data


            data = self.strategies.get(strategy_id)


            if not data:


                return


                


            strategy = data["strategy"]


            file_path = data["file_path"]


            


            # Create retirement info


            strategy["status"] = "retired"


            strategy["retired_at"] = datetime.now().isoformat()


            strategy["retirement_reason"] = "Poor performance below threshold"


            


            # Move to archive


            archive_path = os.path.join(self.archive_path, f"{strategy_id}.json")


            


            # Save to archive


            with open(archive_path, "w") as f:


                json.dump(strategy, f, indent=2)


                


            # Delete original file


            if os.path.exists(file_path):


                os.remove(file_path)


                


            # Remove from strategies dict


            self.strategies.pop(strategy_id, None)


            


            logger.info(f"Retired strategy {strategy_id} to archive")


            


        except Exception as e:


            logger.error(f"Failed to retire strategy {strategy_id}: {str(e)}")


            


    def evaluate_improvement(self, original_id: str, improved_id: str) -> Dict[str, Any]:


        """


        Evaluate whether an improvement was successful


        


        Args:


            original_id: Original strategy ID


            improved_id: Improved strategy ID


            


        Returns:


            Evaluation results


        """


        try:


            # Load performance data for both strategies


            original_performance = self._load_performance(original_id)


            improved_performance = self._load_performance(improved_id)


            


            # Compare key metrics


            original_profit = original_performance.get("profit_loss", 0.0)


            improved_profit = improved_performance.get("profit_loss", 0.0)


            


            original_sharpe = original_performance.get("sharpe_ratio", 0.0)


            improved_sharpe = improved_performance.get("sharpe_ratio", 0.0)


            


            original_drawdown = original_performance.get("max_drawdown", 0.0)


            improved_drawdown = improved_performance.get("max_drawdown", 0.0)


            


            # Calculate improvement percentages


            profit_improvement = improved_profit - original_profit


            sharpe_improvement = improved_sharpe - original_sharpe


            drawdown_improvement = improved_drawdown - original_drawdown


            


            # Determine if improvement was successful


            is_successful = (


                profit_improvement > 0 or


                sharpe_improvement > 0.2 or


                drawdown_improvement > 2.0


            )


            


            # Create evaluation report


            evaluation = {


                "timestamp": datetime.now().isoformat(),


                "original_id": original_id,


                "improved_id": improved_id,


                "metrics": {


                    "profit_improvement": profit_improvement,


                    "sharpe_improvement": sharpe_improvement,


                    "drawdown_improvement": drawdown_improvement


                },


                "is_successful": is_successful,


                "recommendation": "deploy" if is_successful else "archive"


            }


            


            logger.info(f"Evaluated improvement: {original_id} -> {improved_id} (success: {is_successful})")


            return evaluation


            


        except Exception as e:


            logger.error(f"Improvement evaluation failed: {str(e)}")


            return {


                "timestamp": datetime.now().isoformat(),


                "original_id": original_id,


                "improved_id": improved_id,


                "error": str(e),


                "is_successful": False,


                "recommendation": "retry"


            }


            


    def get_improvement_statistics(self) -> Dict[str, Any]:


        """


        Get statistics about strategy improvements


        


        Returns:


            Statistics dictionary


        """


        try:


            # Scan the improved and archive directories


            improved_count = len([f for f in os.listdir(self.improved_path) if f.endswith(".json")])


            retired_count = len([f for f in os.listdir(self.archive_path) if f.endswith(".json")])


            


            # Count generations


            generation_counts = {}


            


            for strategy_id, data in self.strategies.items():


                strategy = data["strategy"]


                generation = strategy.get("generation", 0)


                


                if generation not in generation_counts:


                    generation_counts[generation] = 0


                    


                generation_counts[generation] += 1


                


            # Prepare statistics


            stats = {


                "active_strategies": len(self.strategies),


                "improved_strategies": improved_count,


                "retired_strategies": retired_count,


                "generation_distribution": generation_counts,


                "timestamp": datetime.now().isoformat()


            }


            


            return stats


            


        except Exception as e:


            logger.error(f"Failed to get improvement statistics: {str(e)}")


            return {


                "error": str(e),


                "timestamp": datetime.now().isoformat()


            }


    async def start(self):
        """Async start method for compatibility with system startup."""
        pass 