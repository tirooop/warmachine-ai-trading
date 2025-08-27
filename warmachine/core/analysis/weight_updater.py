"""
Weight Updater for WarMachine Trading System

This module implements a weight updater that uses a sliding window algorithm
to dynamically adjust model weights based on performance.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WeightUpdater:
    """Weight updater for model ensemble"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize weight updater
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize window parameters
        self.window_size = config.get("window_size", 100)
        self.min_window_size = config.get("min_window_size", 10)
        self.window_type = config.get("window_type", "time")  # "time" or "samples"
        
        # Initialize weight parameters
        self.min_weight = config.get("min_weight", 0.1)
        self.max_weight = config.get("max_weight", 1.0)
        self.weight_decay = config.get("weight_decay", 0.95)
        
        # Initialize performance windows
        self.performance_windows = {}
        
    def update_weights(
        self,
        current_weights: Dict[str, float],
        performance_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """Update model weights based on performance
        
        Args:
            current_weights: Current model weights
            performance_metrics: Performance metrics for each model
            
        Returns:
            Updated weights
        """
        try:
            # Initialize new weights
            new_weights = {}
            
            # Update performance windows
            self._update_performance_windows(performance_metrics)
            
            # Calculate weight adjustments
            weight_adjustments = self._calculate_weight_adjustments(performance_metrics)
            
            # Apply adjustments to current weights
            for model_id in current_weights.keys():
                if model_id in weight_adjustments:
                    # Calculate new weight
                    new_weight = current_weights[model_id] * weight_adjustments[model_id]
                    
                    # Apply weight bounds
                    new_weight = max(min(new_weight, self.max_weight), self.min_weight)
                    
                    # Apply weight decay
                    new_weight *= self.weight_decay
                    
                    new_weights[model_id] = new_weight
                else:
                    # Keep current weight with decay
                    new_weights[model_id] = current_weights[model_id] * self.weight_decay
                    
            # Normalize weights
            total_weight = sum(new_weights.values())
            if total_weight > 0:
                new_weights = {k: v/total_weight for k, v in new_weights.items()}
                
            return new_weights
            
        except Exception as e:
            logger.error(f"Error updating weights: {str(e)}")
            raise
            
    def _update_performance_windows(self, performance_metrics: Dict[str, Dict[str, float]]):
        """Update performance windows with new metrics
        
        Args:
            performance_metrics: Performance metrics for each model
        """
        try:
            now = datetime.now()
            
            for model_id, metrics in performance_metrics.items():
                # Initialize window if needed
                if model_id not in self.performance_windows:
                    self.performance_windows[model_id] = {
                        "mae": deque(maxlen=self.window_size),
                        "rmse": deque(maxlen=self.window_size),
                        "recent_mae": deque(maxlen=self.window_size),
                        "timestamps": deque(maxlen=self.window_size)
                    }
                    
                # Add new metrics
                window = self.performance_windows[model_id]
                window["mae"].append(metrics["mae"])
                window["rmse"].append(metrics["rmse"])
                window["recent_mae"].append(metrics["recent_mae"])
                window["timestamps"].append(now)
                
        except Exception as e:
            logger.error(f"Error updating performance windows: {str(e)}")
            raise
            
    def _calculate_weight_adjustments(
        self,
        performance_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """Calculate weight adjustments based on performance
        
        Args:
            performance_metrics: Performance metrics for each model
            
        Returns:
            Dictionary of weight adjustments
        """
        try:
            adjustments = {}
            
            for model_id, metrics in performance_metrics.items():
                if model_id not in self.performance_windows:
                    continue
                    
                window = self.performance_windows[model_id]
                
                # Skip if window is too small
                if len(window["mae"]) < self.min_window_size:
                    continue
                    
                # Calculate performance scores
                mae_score = self._calculate_mae_score(window["mae"])
                rmse_score = self._calculate_rmse_score(window["rmse"])
                recent_score = self._calculate_recent_score(window["recent_mae"])
                
                # Combine scores
                performance_score = (
                    0.4 * mae_score +
                    0.4 * rmse_score +
                    0.2 * recent_score
                )
                
                # Calculate adjustment
                adjustment = 1.0 + (performance_score - 0.5) * 2.0
                adjustments[model_id] = adjustment
                
            return adjustments
            
        except Exception as e:
            logger.error(f"Error calculating weight adjustments: {str(e)}")
            raise
            
    def _calculate_mae_score(self, mae_window: deque) -> float:
        """Calculate score based on MAE
        
        Args:
            mae_window: Window of MAE values
            
        Returns:
            MAE score between 0 and 1
        """
        try:
            if not mae_window:
                return 0.5
                
            # Calculate relative MAE
            mae_values = list(mae_window)
            min_mae = min(mae_values)
            max_mae = max(mae_values)
            
            if max_mae == min_mae:
                return 0.5
                
            # Calculate score (lower MAE is better)
            latest_mae = mae_values[-1]
            score = 1.0 - (latest_mae - min_mae) / (max_mae - min_mae)
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating MAE score: {str(e)}")
            return 0.5
            
    def _calculate_rmse_score(self, rmse_window: deque) -> float:
        """Calculate score based on RMSE
        
        Args:
            rmse_window: Window of RMSE values
            
        Returns:
            RMSE score between 0 and 1
        """
        try:
            if not rmse_window:
                return 0.5
                
            # Calculate relative RMSE
            rmse_values = list(rmse_window)
            min_rmse = min(rmse_values)
            max_rmse = max(rmse_values)
            
            if max_rmse == min_rmse:
                return 0.5
                
            # Calculate score (lower RMSE is better)
            latest_rmse = rmse_values[-1]
            score = 1.0 - (latest_rmse - min_rmse) / (max_rmse - min_rmse)
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating RMSE score: {str(e)}")
            return 0.5
            
    def _calculate_recent_score(self, recent_window: deque) -> float:
        """Calculate score based on recent performance
        
        Args:
            recent_window: Window of recent MAE values
            
        Returns:
            Recent performance score between 0 and 1
        """
        try:
            if not recent_window:
                return 0.5
                
            # Calculate trend
            recent_values = list(recent_window)
            if len(recent_values) < 2:
                return 0.5
                
            # Calculate moving average
            window_size = min(5, len(recent_values))
            recent_avg = np.mean(recent_values[-window_size:])
            older_avg = np.mean(recent_values[-2*window_size:-window_size])
            
            # Calculate trend score
            if older_avg == 0:
                return 0.5
                
            trend = (older_avg - recent_avg) / older_avg
            score = 0.5 + trend * 0.5
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating recent score: {str(e)}")
            return 0.5
            
    def get_window_stats(self, model_id: str) -> Dict[str, Any]:
        """Get statistics for model's performance window
        
        Args:
            model_id: ID of model
            
        Returns:
            Dictionary containing window statistics
        """
        try:
            if model_id not in self.performance_windows:
                return {}
                
            window = self.performance_windows[model_id]
            
            return {
                "window_size": len(window["mae"]),
                "mae_stats": {
                    "mean": np.mean(window["mae"]),
                    "std": np.std(window["mae"]),
                    "min": min(window["mae"]),
                    "max": max(window["mae"])
                },
                "rmse_stats": {
                    "mean": np.mean(window["rmse"]),
                    "std": np.std(window["rmse"]),
                    "min": min(window["rmse"]),
                    "max": max(window["rmse"])
                },
                "recent_stats": {
                    "mean": np.mean(window["recent_mae"]),
                    "std": np.std(window["recent_mae"]),
                    "min": min(window["recent_mae"]),
                    "max": max(window["recent_mae"])
                },
                "time_span": {
                    "start": window["timestamps"][0].isoformat(),
                    "end": window["timestamps"][-1].isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting window stats: {str(e)}")
            raise 