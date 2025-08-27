"""
Alert Feedback System

Handles alert feedback and confirmation from users.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from ai_event_pool import EventCategory, EventPriority

logger = logging.getLogger(__name__)

class AlertFeedback:
    """Alert feedback from a user"""
    
    def __init__(self, event_id: str, user_id: str, feedback_type: str):
        """
        Initialize alert feedback
        
        Args:
            event_id: ID of the event
            user_id: Telegram user ID
            feedback_type: Type of feedback (e.g. "confirm", "dismiss", "report")
        """
        self.event_id = event_id
        self.user_id = user_id
        self.feedback_type = feedback_type
        self.timestamp = datetime.now().isoformat()
        self.comment = None
    
    def add_comment(self, comment: str) -> None:
        """
        Add a comment to the feedback
        
        Args:
            comment: User's comment
        """
        self.comment = comment
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feedback to dictionary"""
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "feedback_type": self.feedback_type,
            "timestamp": self.timestamp,
            "comment": self.comment
        }

class AlertFeedbackManager:
    """Manager for alert feedback"""
    
    def __init__(self):
        """Initialize feedback manager"""
        self.feedback: Dict[str, List[AlertFeedback]] = {}  # event_id -> list of feedback
        self.user_feedback: Dict[str, List[AlertFeedback]] = {}  # user_id -> list of feedback
    
    def add_feedback(self, event_id: str, user_id: str, feedback_type: str, comment: Optional[str] = None) -> AlertFeedback:
        """
        Add feedback for an event
        
        Args:
            event_id: ID of the event
            user_id: Telegram user ID
            feedback_type: Type of feedback
            comment: Optional comment
            
        Returns:
            New feedback object
        """
        feedback = AlertFeedback(event_id, user_id, feedback_type)
        if comment:
            feedback.add_comment(comment)
        
        # Add to event feedback
        if event_id not in self.feedback:
            self.feedback[event_id] = []
        self.feedback[event_id].append(feedback)
        
        # Add to user feedback
        if user_id not in self.user_feedback:
            self.user_feedback[user_id] = []
        self.user_feedback[user_id].append(feedback)
        
        logger.info(f"Added {feedback_type} feedback for event {event_id} from user {user_id}")
        return feedback
    
    def get_event_feedback(self, event_id: str) -> List[AlertFeedback]:
        """
        Get feedback for an event
        
        Args:
            event_id: ID of the event
            
        Returns:
            List of feedback objects
        """
        return self.feedback.get(event_id, [])
    
    def get_user_feedback(self, user_id: str) -> List[AlertFeedback]:
        """
        Get feedback from a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of feedback objects
        """
        return self.user_feedback.get(user_id, [])
    
    def get_feedback_summary(self, event_id: str) -> Dict[str, Any]:
        """
        Get feedback summary for an event
        
        Args:
            event_id: ID of the event
            
        Returns:
            Dictionary with feedback summary
        """
        feedback_list = self.get_event_feedback(event_id)
        if not feedback_list:
            return {
                "total": 0,
                "by_type": {},
                "latest": None
            }
        
        # Count by type
        by_type = {}
        for feedback in feedback_list:
            by_type[feedback.feedback_type] = by_type.get(feedback.feedback_type, 0) + 1
        
        # Get latest feedback
        latest = max(feedback_list, key=lambda f: f.timestamp)
        
        return {
            "total": len(feedback_list),
            "by_type": by_type,
            "latest": latest.to_dict()
        }
    
    def clear_event_feedback(self, event_id: str) -> bool:
        """
        Clear feedback for an event
        
        Args:
            event_id: ID of the event
            
        Returns:
            True if feedback was cleared successfully
        """
        try:
            if event_id in self.feedback:
                # Remove from user feedback
                for feedback in self.feedback[event_id]:
                    if feedback.user_id in self.user_feedback:
                        self.user_feedback[feedback.user_id] = [
                            f for f in self.user_feedback[feedback.user_id]
                            if f.event_id != event_id
                        ]
                
                # Remove from event feedback
                del self.feedback[event_id]
                logger.info(f"Cleared feedback for event {event_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error clearing feedback for event {event_id}: {str(e)}")
            return False
    
    def clear_user_feedback(self, user_id: str) -> bool:
        """
        Clear feedback from a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if feedback was cleared successfully
        """
        try:
            if user_id in self.user_feedback:
                # Remove from event feedback
                for feedback in self.user_feedback[user_id]:
                    if feedback.event_id in self.feedback:
                        self.feedback[feedback.event_id] = [
                            f for f in self.feedback[feedback.event_id]
                            if f.user_id != user_id
                        ]
                
                # Remove from user feedback
                del self.user_feedback[user_id]
                logger.info(f"Cleared feedback for user {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error clearing feedback for user {user_id}: {str(e)}")
            return False 