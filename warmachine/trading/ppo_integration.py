"""
PPO Integration Module for WarMachine Trading System

This module implements Proximal Policy Optimization (PPO) for trading decisions,
integrating with the existing WarMachine system.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Dict, Any, List, Tuple
import logging

from trading.base_trainer import BaseTrainer
from core.data.market_data_hub import MarketDataHub

logger = logging.getLogger(__name__)

class PPONetwork(nn.Module):
    """Policy network for PPO"""
    
    def __init__(self, obs_shape: Tuple[int, ...], action_dim: int):
        super().__init__()
        
        # Feature extraction layers
        self.feature_net = nn.Sequential(
            nn.Linear(np.prod(obs_shape), 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU()
        )
        
        # Policy head
        self.policy_head = nn.Sequential(
            nn.Linear(128, action_dim),
            nn.Softmax(dim=-1)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.feature_net(x)
        return self.policy_head(features)

class ValueNetwork(nn.Module):
    """Value network for PPO"""
    
    def __init__(self, obs_shape: Tuple[int, ...]):
        super().__init__()
        
        self.value_net = nn.Sequential(
            nn.Linear(np.prod(obs_shape), 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.value_net(x)

class PPOTrainer(BaseTrainer):
    """PPO Trainer for trading decisions"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        
        # Initialize networks
        obs_shape = config["observation_shape"]
        action_dim = config["action_dim"]
        self.policy_net = PPONetwork(obs_shape, action_dim)
        self.value_net = ValueNetwork(obs_shape)
        
        # Initialize optimizers
        self.policy_optimizer = optim.Adam(
            self.policy_net.parameters(),
            lr=config.get("learning_rate", 3e-4)
        )
        self.value_optimizer = optim.Adam(
            self.value_net.parameters(),
            lr=config.get("learning_rate", 3e-4)
        )
        
        # Training parameters
        self.gamma = config.get("gamma", 0.99)
        self.gae_lambda = config.get("gae_lambda", 0.95)
        self.clip_ratio = config.get("clip_ratio", 0.2)
        self.value_coef = config.get("value_coef", 0.5)
        self.entropy_coef = config.get("entropy_coef", 0.01)
        
        # Initialize market data hub
        self.market_data = MarketDataHub(config.get("market_data", {}))
        
    def _compute_gae(
        self,
        rewards: List[float],
        values: List[float],
        next_value: float,
        dones: List[bool]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute Generalized Advantage Estimation
        
        Args:
            rewards: List of rewards
            values: List of value predictions
            next_value: Value prediction for next state
            dones: List of done flags
            
        Returns:
            Tuple of (advantages, returns)
        """
        advantages = []
        returns = []
        gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value_t = next_value
            else:
                next_value_t = values[t + 1]
                
            delta = rewards[t] + self.gamma * next_value_t * (1 - dones[t]) - values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * gae
            
            advantages.insert(0, gae)
            returns.insert(0, gae + values[t])
            
        return np.array(advantages), np.array(returns)
        
    def update_weights(self, batch: Dict[str, Any]):
        """Update network weights using PPO
        
        Args:
            batch: Dictionary containing training batch data
        """
        try:
            # Extract batch data
            states = torch.FloatTensor(batch["states"])
            actions = torch.LongTensor(batch["actions"])
            old_probs = torch.FloatTensor(batch["action_probs"])
            rewards = torch.FloatTensor(batch["rewards"])
            dones = torch.FloatTensor(batch["dones"])
            
            # Compute advantages and returns
            with torch.no_grad():
                values = self.value_net(states).squeeze()
                next_value = self.value_net(batch["next_state"]).item()
                
            advantages, returns = self._compute_gae(
                rewards.numpy(),
                values.numpy(),
                next_value,
                dones.numpy()
            )
            
            advantages = torch.FloatTensor(advantages)
            returns = torch.FloatTensor(returns)
            
            # Normalize advantages
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
            
            # Update policy
            for _ in range(self.config.get("policy_epochs", 10)):
                # Get action probabilities
                action_probs = self.policy_net(states)
                dist = torch.distributions.Categorical(action_probs)
                
                # Compute policy loss
                ratio = torch.exp(dist.log_prob(actions) - torch.log(old_probs))
                policy_loss = -torch.min(
                    ratio * advantages,
                    torch.clamp(ratio, 1 - self.clip_ratio, 1 + self.clip_ratio) * advantages
                ).mean()
                
                # Compute value loss
                value_pred = self.value_net(states).squeeze()
                value_loss = nn.MSELoss()(value_pred, returns)
                
                # Compute entropy loss
                entropy_loss = -dist.entropy().mean()
                
                # Total loss
                loss = (
                    policy_loss +
                    self.value_coef * value_loss -
                    self.entropy_coef * entropy_loss
                )
                
                # Update networks
                self.policy_optimizer.zero_grad()
                self.value_optimizer.zero_grad()
                loss.backward()
                self.policy_optimizer.step()
                self.value_optimizer.step()
                
            return {
                "policy_loss": policy_loss.item(),
                "value_loss": value_loss.item(),
                "entropy_loss": entropy_loss.item()
            }
            
        except Exception as e:
            logger.error(f"Error updating weights: {str(e)}")
            raise
            
    def get_action(self, state: np.ndarray) -> Tuple[int, float]:
        """Get action from policy network
        
        Args:
            state: Current state
            
        Returns:
            Tuple of (action, action_probability)
        """
        try:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state)
                action_probs = self.policy_net(state_tensor)
                dist = torch.distributions.Categorical(action_probs)
                action = dist.sample()
                action_prob = action_probs[action].item()
                
            return action.item(), action_prob
            
        except Exception as e:
            logger.error(f"Error getting action: {str(e)}")
            raise
            
    def save_model(self, path: str):
        """Save model weights
        
        Args:
            path: Path to save model
        """
        try:
            torch.save({
                "policy_net": self.policy_net.state_dict(),
                "value_net": self.value_net.state_dict(),
                "policy_optimizer": self.policy_optimizer.state_dict(),
                "value_optimizer": self.value_optimizer.state_dict()
            }, path)
            
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise
            
    def load_model(self, path: str):
        """Load model weights
        
        Args:
            path: Path to load model from
        """
        try:
            checkpoint = torch.load(path)
            self.policy_net.load_state_dict(checkpoint["policy_net"])
            self.value_net.load_state_dict(checkpoint["value_net"])
            self.policy_optimizer.load_state_dict(checkpoint["policy_optimizer"])
            self.value_optimizer.load_state_dict(checkpoint["value_optimizer"])
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise 