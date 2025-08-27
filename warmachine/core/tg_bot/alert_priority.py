"""
Alert Priority Manager

Handles dynamic adjustment of alert priorities based on various factors.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from ai_event_pool import EventCategory, EventPriority

logger = logging.getLogger(__name__)

class PriorityRule:
    """Rule for adjusting alert priority"""
    
    def __init__(self, name: str, condition: str, adjustment: int, cooldown: int = 0):
        """
        Initialize priority rule
        
        Args:
            name: Rule name
            condition: Condition string (e.g. "volume > 1000")
            adjustment: Priority adjustment (-2 to +2)
            cooldown: Cooldown period in seconds
        """
        self.name = name
        self.condition = condition
        self.adjustment = max(-2, min(2, adjustment))  # Clamp between -2 and +2
        self.cooldown = cooldown
        self.last_triggered = None
    
    def evaluate(self, event: Any) -> bool:
        """
        Evaluate rule condition
        
        Args:
            event: Event to evaluate
            
        Returns:
            True if condition is met
        """
        try:
            # Check cooldown
            if self.cooldown and self.last_triggered:
                if (datetime.now() - self.last_triggered).total_seconds() < self.cooldown:
                    return False
            
            # Evaluate condition
            # This is a simple implementation - in practice you'd want to use a proper expression evaluator
            if ">" in self.condition:
                field, value = self.condition.split(">")
                field = field.strip()
                value = float(value.strip())
                return float(event.metadata.get(field, 0)) > value
            elif "<" in self.condition:
                field, value = self.condition.split("<")
                field = field.strip()
                value = float(value.strip())
                return float(event.metadata.get(field, 0)) < value
            elif "==" in self.condition:
                field, value = self.condition.split("==")
                field = field.strip()
                value = value.strip()
                return event.metadata.get(field) == value
            elif "!=" in self.condition:
                field, value = self.condition.split("!=")
                field = field.strip()
                value = value.strip()
                return event.metadata.get(field) != value
            else:
                logger.warning(f"Unknown condition operator in rule {self.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating rule {self.name}: {str(e)}")
            return False
    
    def apply(self, priority: EventPriority) -> EventPriority:
        """
        Apply priority adjustment
        
        Args:
            priority: Current priority
            
        Returns:
            Adjusted priority
        """
        try:
            # Get priority value
            current_value = priority.value
            
            # Apply adjustment
            new_value = current_value + self.adjustment
            
            # Clamp to valid range
            new_value = max(0, min(len(EventPriority) - 1, new_value))
            
            # Update last triggered time
            self.last_triggered = datetime.now()
            
            # Return new priority
            return EventPriority(new_value)
            
        except Exception as e:
            logger.error(f"Error applying rule {self.name}: {str(e)}")
            return priority

class AlertPriority:
    """告警优先级管理类（占位实现）"""
    def __init__(self):
        pass

    def get_all_priorities(self):
        return []

    def set_priority(self, alert_id, priority):
        return {"success": True}
    
class PriorityManager:
    """Manager for alert priorities"""
    
    def __init__(self):
        """Initialize priority manager"""
        self.rules: List[PriorityRule] = []
        self.history: Dict[str, List[Dict[str, Any]]] = {}  # event_id -> list of adjustments
    
    def add_rule(self, name: str, condition: str, adjustment: int, cooldown: int = 0) -> PriorityRule:
        """
        Add a priority rule
        
        Args:
            name: Rule name
            condition: Condition string
            adjustment: Priority adjustment
            cooldown: Cooldown period in seconds
            
        Returns:
            New rule object
        """
        rule = PriorityRule(name, condition, adjustment, cooldown)
        self.rules.append(rule)
        logger.info(f"Added priority rule: {name}")
        return rule
    
    def remove_rule(self, name: str) -> bool:
        """
        Remove a priority rule
        
        Args:
            name: Rule name
            
        Returns:
            True if rule was removed successfully
        """
        try:
            for i, rule in enumerate(self.rules):
                if rule.name == name:
                    del self.rules[i]
                    logger.info(f"Removed priority rule: {name}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing rule {name}: {str(e)}")
            return False
    
    def adjust_priority(self, event: Any) -> EventPriority:
        """
        Adjust event priority based on rules
        
        Args:
            event: Event to adjust
            
        Returns:
            Adjusted priority
        """
        try:
            original_priority = event.priority
            adjusted_priority = original_priority
            
            # Apply each rule
            for rule in self.rules:
                if rule.evaluate(event):
                    adjusted_priority = rule.apply(adjusted_priority)
            
            # Record adjustment if changed
            if adjusted_priority != original_priority:
                if event.id not in self.history:
                    self.history[event.id] = []
                
                self.history[event.id].append({
                    "timestamp": datetime.now().isoformat(),
                    "original_priority": original_priority.name,
                    "adjusted_priority": adjusted_priority.name,
                    "rules_applied": [
                        rule.name for rule in self.rules
                        if rule.evaluate(event)
                    ]
                })
                
                logger.info(
                    f"Adjusted priority for event {event.id}: "
                    f"{original_priority.name} -> {adjusted_priority.name}"
                )
            
            return adjusted_priority
            
        except Exception as e:
            logger.error(f"Error adjusting priority for event {event.id}: {str(e)}")
            return event.priority
    
    def get_adjustment_history(self, event_id: str) -> List[Dict[str, Any]]:
        """
        Get priority adjustment history for an event
        
        Args:
            event_id: ID of the event
            
        Returns:
            List of adjustment records
        """
        return self.history.get(event_id, [])
    
    def clear_history(self, event_id: Optional[str] = None) -> None:
        """
        Clear adjustment history
        
        Args:
            event_id: Optional event ID to clear history for
        """
        if event_id:
            if event_id in self.history:
                del self.history[event_id]
                logger.info(f"Cleared priority history for event {event_id}")
        else:
            self.history.clear()
            logger.info("Cleared all priority history")
    
    def list_rules(self) -> List[Dict[str, Any]]:
        """
        List all priority rules
        
        Returns:
            List of rule information dictionaries
        """
        return [
            {
                "name": rule.name,
                "condition": rule.condition,
                "adjustment": rule.adjustment,
                "cooldown": rule.cooldown,
                "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None
            }
            for rule in self.rules
        ] 