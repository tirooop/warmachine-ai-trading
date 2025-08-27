"""
Model Ensemble Service for WarMachine Trading System

This module implements an ensemble service that combines predictions from multiple models
to generate more robust trading signals.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from datetime import datetime
import json

from core.analysis.weight_updater import WeightUpdater

logger = logging.getLogger(__name__)

class ModelEnsembleService:
    """Service for combining model predictions"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize ensemble service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize weight updater
        self.weight_updater = WeightUpdater(config.get("weight_updater", {}))
        
        # Initialize model registry
        self.models = {}
        self.model_weights = {}
        self.model_performance = {}
        
        # Initialize ensemble parameters
        self.min_models = config.get("min_models", 3)
        self.max_models = config.get("max_models", 10)
        self.weight_update_interval = config.get("weight_update_interval", 3600)
        self.last_weight_update = datetime.now()
        
    def register_model(self, model_id: str, model: Any, initial_weight: float = 1.0):
        """Register model with ensemble
        
        Args:
            model_id: Unique identifier for model
            model: Model instance
            initial_weight: Initial weight for model
        """
        try:
            if len(self.models) >= self.max_models:
                raise ValueError(f"Maximum number of models ({self.max_models}) reached")
                
            self.models[model_id] = model
            self.model_weights[model_id] = initial_weight
            self.model_performance[model_id] = {
                "predictions": [],
                "actuals": [],
                "errors": [],
                "last_update": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error registering model: {str(e)}")
            raise
            
    def unregister_model(self, model_id: str):
        """Unregister model from ensemble
        
        Args:
            model_id: ID of model to unregister
        """
        try:
            if model_id in self.models:
                del self.models[model_id]
                del self.model_weights[model_id]
                del self.model_performance[model_id]
                
        except Exception as e:
            logger.error(f"Error unregistering model: {str(e)}")
            raise
            
    def get_prediction(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get ensemble prediction
        
        Args:
            input_data: Input data for prediction
            
        Returns:
            Ensemble prediction
        """
        try:
            if len(self.models) < self.min_models:
                raise ValueError(f"Not enough models registered (minimum: {self.min_models})")
                
            # Get predictions from all models
            predictions = {}
            for model_id, model in self.models.items():
                try:
                    pred = model.predict(input_data)
                    predictions[model_id] = pred
                except Exception as e:
                    logger.warning(f"Error getting prediction from model {model_id}: {str(e)}")
                    continue
                    
            # Check if we have enough predictions
            if len(predictions) < self.min_models:
                raise ValueError("Not enough valid predictions")
                
            # Combine predictions
            ensemble_pred = self._combine_predictions(predictions)
            
            # Update weights if needed
            self._update_weights_if_needed()
            
            return ensemble_pred
            
        except Exception as e:
            logger.error(f"Error getting ensemble prediction: {str(e)}")
            raise
            
    def update_performance(self, model_id: str, prediction: float, actual: float):
        """Update model performance metrics
        
        Args:
            model_id: ID of model to update
            prediction: Model prediction
            actual: Actual value
        """
        try:
            if model_id not in self.model_performance:
                return
                
            # Calculate error
            error = abs(prediction - actual)
            
            # Update performance metrics
            perf = self.model_performance[model_id]
            perf["predictions"].append(prediction)
            perf["actuals"].append(actual)
            perf["errors"].append(error)
            perf["last_update"] = datetime.now()
            
            # Keep only recent history
            max_history = self.config.get("max_performance_history", 1000)
            if len(perf["predictions"]) > max_history:
                perf["predictions"] = perf["predictions"][-max_history:]
                perf["actuals"] = perf["actuals"][-max_history:]
                perf["errors"] = perf["errors"][-max_history:]
                
        except Exception as e:
            logger.error(f"Error updating performance: {str(e)}")
            raise
            
    def _combine_predictions(self, predictions: Dict[str, float]) -> Dict[str, Any]:
        """Combine model predictions
        
        Args:
            predictions: Dictionary of model predictions
            
        Returns:
            Combined prediction
        """
        try:
            # Get weights for models with predictions
            weights = {
                model_id: self.model_weights[model_id]
                for model_id in predictions.keys()
            }
            
            # Normalize weights
            total_weight = sum(weights.values())
            weights = {k: v/total_weight for k, v in weights.items()}
            
            # Calculate weighted prediction
            weighted_pred = sum(
                predictions[model_id] * weights[model_id]
                for model_id in predictions.keys()
            )
            
            # Calculate prediction confidence
            pred_std = np.std(list(predictions.values()))
            confidence = 1.0 / (1.0 + pred_std)
            
            return {
                "prediction": weighted_pred,
                "confidence": confidence,
                "model_predictions": predictions,
                "model_weights": weights
            }
            
        except Exception as e:
            logger.error(f"Error combining predictions: {str(e)}")
            raise
            
    def _update_weights_if_needed(self):
        """Update model weights if update interval has passed"""
        try:
            now = datetime.now()
            if (now - self.last_weight_update).total_seconds() >= self.weight_update_interval:
                self._update_weights()
                self.last_weight_update = now
                
        except Exception as e:
            logger.error(f"Error updating weights: {str(e)}")
            raise
            
    def _update_weights(self):
        """Update model weights based on performance"""
        try:
            # Calculate performance metrics
            performance_metrics = {}
            for model_id, perf in self.model_performance.items():
                if not perf["errors"]:
                    continue
                    
                # Calculate metrics
                mae = np.mean(perf["errors"])
                rmse = np.sqrt(np.mean(np.square(perf["errors"])))
                recent_mae = np.mean(perf["errors"][-100:]) if len(perf["errors"]) >= 100 else mae
                
                performance_metrics[model_id] = {
                    "mae": mae,
                    "rmse": rmse,
                    "recent_mae": recent_mae
                }
                
            # Update weights
            new_weights = self.weight_updater.update_weights(
                self.model_weights,
                performance_metrics
            )
            
            # Apply new weights
            self.model_weights.update(new_weights)
            
        except Exception as e:
            logger.error(f"Error updating weights: {str(e)}")
            raise
            
    def get_ensemble_state(self) -> Dict[str, Any]:
        """Get current ensemble state
        
        Returns:
            Dictionary containing ensemble state
        """
        return {
            "models": list(self.models.keys()),
            "weights": self.model_weights,
            "performance": self.model_performance,
            "last_weight_update": self.last_weight_update.isoformat()
        }
        
    def save_state(self, filepath: str):
        """Save ensemble state to file
        
        Args:
            filepath: Path to save state
        """
        try:
            state = self.get_ensemble_state()
            with open(filepath, "w") as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
            raise
            
    def load_state(self, filepath: str):
        """Load ensemble state from file
        
        Args:
            filepath: Path to load state from
        """
        try:
            with open(filepath, "r") as f:
                state = json.load(f)
                
            # Update state
            self.model_weights = state["weights"]
            self.model_performance = state["performance"]
            self.last_weight_update = datetime.fromisoformat(state["last_weight_update"])
            
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            raise 