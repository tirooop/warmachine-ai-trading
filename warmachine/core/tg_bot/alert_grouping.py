"""
Alert Grouping System

Handles grouping and tagging of alerts for better organization and filtering.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from ai_event_pool import EventCategory, EventPriority

logger = logging.getLogger(__name__)

class AlertGrouping:
    """告警分组管理类（占位实现）"""
    def __init__(self):
        pass

    def get_all_groups(self):
        return []

    def create_group(self, name, description):
        return {"success": True}

    def add_to_group(self, group_name, alert_id):
        return {"success": True}

    def remove_from_group(self, group_name, alert_id):
        return {"success": True}

class AlertGroup:
    """Group of related alerts"""
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize alert group
        
        Args:
            name: Group name
            description: Group description
        """
        self.name = name
        self.description = description
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        
        # Group settings
        self.tags: Set[str] = set()
        self.categories: Set[EventCategory] = set()
        self.min_priority = EventPriority.LOW
        self.max_alerts = 100  # Maximum number of alerts in group
        self.auto_close = False  # Whether to automatically close group when max alerts reached
        self.notify_on_close = True  # Whether to notify when group is closed
        
        # Group state
        self.alerts: List[Dict[str, Any]] = []
        self.is_closed = False
        self.closed_at = None
        self.closed_by = None
        self.closed_reason = None
    
    def add_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Add alert to group
        
        Args:
            alert: Alert to add
            
        Returns:
            True if alert was added successfully
        """
        try:
            if self.is_closed:
                logger.warning(f"Cannot add alert to closed group {self.name}")
                return False
            
            if len(self.alerts) >= self.max_alerts:
                if self.auto_close:
                    self.close("Maximum alerts reached")
                logger.warning(f"Group {self.name} has reached maximum alerts")
                return False
            
            self.alerts.append(alert)
            self.updated_at = datetime.now().isoformat()
            logger.info(f"Added alert to group {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding alert to group {self.name}: {str(e)}")
            return False
    
    def remove_alert(self, alert_id: str) -> bool:
        """
        Remove alert from group
        
        Args:
            alert_id: ID of alert to remove
            
        Returns:
            True if alert was removed successfully
        """
        try:
            for i, alert in enumerate(self.alerts):
                if alert["id"] == alert_id:
                    del self.alerts[i]
                    self.updated_at = datetime.now().isoformat()
                    logger.info(f"Removed alert from group {self.name}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing alert from group {self.name}: {str(e)}")
            return False
    
    def close(self, reason: str, closed_by: Optional[str] = None) -> bool:
        """
        Close the group
        
        Args:
            reason: Reason for closing
            closed_by: Optional user ID who closed the group
            
        Returns:
            True if group was closed successfully
        """
        try:
            if self.is_closed:
                return False
            
            self.is_closed = True
            self.closed_at = datetime.now().isoformat()
            self.closed_by = closed_by
            self.closed_reason = reason
            self.updated_at = self.closed_at
            
            logger.info(f"Closed group {self.name}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error closing group {self.name}: {str(e)}")
            return False
    
    def reopen(self) -> bool:
        """
        Reopen the group
        
        Returns:
            True if group was reopened successfully
        """
        try:
            if not self.is_closed:
                return False
            
            self.is_closed = False
            self.closed_at = None
            self.closed_by = None
            self.closed_reason = None
            self.updated_at = datetime.now().isoformat()
            
            logger.info(f"Reopened group {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error reopening group {self.name}: {str(e)}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert group to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": list(self.tags),
            "categories": [cat.value for cat in self.categories],
            "min_priority": self.min_priority.name,
            "max_alerts": self.max_alerts,
            "auto_close": self.auto_close,
            "notify_on_close": self.notify_on_close,
            "alert_count": len(self.alerts),
            "is_closed": self.is_closed,
            "closed_at": self.closed_at,
            "closed_by": self.closed_by,
            "closed_reason": self.closed_reason
        }

class AlertGroupManager:
    """Manager for alert groups"""
    
    def __init__(self):
        """Initialize group manager"""
        self.groups: Dict[str, AlertGroup] = {}
    
    def create_group(self, name: str, description: str = "") -> AlertGroup:
        """
        Create a new group
        
        Args:
            name: Group name
            description: Group description
            
        Returns:
            New group object
        """
        group = AlertGroup(name, description)
        self.groups[name] = group
        logger.info(f"Created group: {name}")
        return group
    
    def get_group(self, name: str) -> Optional[AlertGroup]:
        """
        Get group by name
        
        Args:
            name: Group name
            
        Returns:
            Group object or None if not found
        """
        return self.groups.get(name)
    
    def remove_group(self, name: str) -> bool:
        """
        Remove a group
        
        Args:
            name: Group name
            
        Returns:
            True if group was removed successfully
        """
        try:
            if name in self.groups:
                del self.groups[name]
                logger.info(f"Removed group: {name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing group {name}: {str(e)}")
            return False
    
    def update_group(self, name: str, updates: Dict[str, Any]) -> bool:
        """
        Update group settings
        
        Args:
            name: Group name
            updates: Dictionary of settings to update
            
        Returns:
            True if group was updated successfully
        """
        try:
            group = self.get_group(name)
            if not group:
                return False
            
            # Update basic settings
            if "description" in updates:
                group.description = updates["description"]
            
            # Update tags
            if "tags" in updates:
                group.tags = set(updates["tags"])
            
            # Update categories
            if "categories" in updates:
                group.categories = {
                    EventCategory(cat) for cat in updates["categories"]
                }
            
            # Update priority
            if "min_priority" in updates:
                group.min_priority = EventPriority[updates["min_priority"]]
            
            # Update limits
            if "max_alerts" in updates:
                group.max_alerts = updates["max_alerts"]
            if "auto_close" in updates:
                group.auto_close = updates["auto_close"]
            if "notify_on_close" in updates:
                group.notify_on_close = updates["notify_on_close"]
            
            group.updated_at = datetime.now().isoformat()
            logger.info(f"Updated group: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating group {name}: {str(e)}")
            return False
    
    def add_alert_to_group(self, group_name: str, alert: Dict[str, Any]) -> bool:
        """
        Add alert to group
        
        Args:
            group_name: Group name
            alert: Alert to add
            
        Returns:
            True if alert was added successfully
        """
        try:
            group = self.get_group(group_name)
            if not group:
                return False
            
            return group.add_alert(alert)
            
        except Exception as e:
            logger.error(f"Error adding alert to group {group_name}: {str(e)}")
            return False
    
    def remove_alert_from_group(self, group_name: str, alert_id: str) -> bool:
        """
        Remove alert from group
        
        Args:
            group_name: Group name
            alert_id: ID of alert to remove
            
        Returns:
            True if alert was removed successfully
        """
        try:
            group = self.get_group(group_name)
            if not group:
                return False
            
            return group.remove_alert(alert_id)
            
        except Exception as e:
            logger.error(f"Error removing alert from group {group_name}: {str(e)}")
            return False
    
    def close_group(self, name: str, reason: str, closed_by: Optional[str] = None) -> bool:
        """
        Close a group
        
        Args:
            name: Group name
            reason: Reason for closing
            closed_by: Optional user ID who closed the group
            
        Returns:
            True if group was closed successfully
        """
        try:
            group = self.get_group(name)
            if not group:
                return False
            
            return group.close(reason, closed_by)
            
        except Exception as e:
            logger.error(f"Error closing group {name}: {str(e)}")
            return False
    
    def reopen_group(self, name: str) -> bool:
        """
        Reopen a group
        
        Args:
            name: Group name
            
        Returns:
            True if group was reopened successfully
        """
        try:
            group = self.get_group(name)
            if not group:
                return False
            
            return group.reopen()
            
        except Exception as e:
            logger.error(f"Error reopening group {name}: {str(e)}")
            return False
    
    def list_groups(self) -> List[Dict[str, Any]]:
        """
        List all groups
        
        Returns:
            List of group information dictionaries
        """
        return [group.to_dict() for group in self.groups.values()]
    
    def get_groups_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Get groups with a specific tag
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of matching group information dictionaries
        """
        return [
            group.to_dict() for group in self.groups.values()
            if tag in group.tags
        ]
    
    def get_groups_by_category(self, category: EventCategory) -> List[Dict[str, Any]]:
        """
        Get groups for a specific category
        
        Args:
            category: Category to search for
            
        Returns:
            List of matching group information dictionaries
        """
        return [
            group.to_dict() for group in self.groups.values()
            if category in group.categories
        ]
    
    def get_active_groups(self) -> List[Dict[str, Any]]:
        """
        Get all active (non-closed) groups
        
        Returns:
            List of active group information dictionaries
        """
        return [
            group.to_dict() for group in self.groups.values()
            if not group.is_closed
        ]
    
    def get_closed_groups(self) -> List[Dict[str, Any]]:
        """
        Get all closed groups
        
        Returns:
            List of closed group information dictionaries
        """
        return [
            group.to_dict() for group in self.groups.values()
            if group.is_closed
        ] 