"""
Sentiment Adapter for WarMachine Trading System

This module implements sentiment analysis and news processing capabilities,
converting raw text data into structured sentiment signals.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime
import json

from transformers import pipeline
from textblob import TextBlob

from core.tg_bot.super_commander import SuperCommander

logger = logging.getLogger(__name__)

class SentimentAdapter:
    """Adapter for sentiment analysis and news processing"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize sentiment adapter
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize sentiment analyzer
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model=config.get("sentiment_model", "distilbert-base-uncased-finetuned-sst-2-english"),
            device=config.get("device", -1)
        )
        
        # Initialize keyword lists
        self.market_keywords = set(config.get("market_keywords", []))
        self.sector_keywords = set(config.get("sector_keywords", []))
        
        # Initialize sentiment thresholds
        self.sentiment_thresholds = config.get("sentiment_thresholds", {
            "strong_positive": 0.8,
            "positive": 0.6,
            "neutral": 0.4,
            "negative": 0.2,
            "strong_negative": 0.0
        })
        
    def process_news(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process news article
        
        Args:
            news_data: News article data
            
        Returns:
            Processed sentiment data
        """
        try:
            # Extract text
            title = news_data.get("title", "")
            content = news_data.get("content", "")
            source = news_data.get("source", "")
            timestamp = news_data.get("timestamp", datetime.now().isoformat())
            
            # Combine title and content
            text = f"{title} {content}"
            
            # Get sentiment scores
            sentiment_scores = self._analyze_sentiment(text)
            
            # Extract keywords
            keywords = self._extract_keywords(text)
            
            # Get market impact
            market_impact = self._calculate_market_impact(sentiment_scores, keywords)
            
            return {
                "timestamp": timestamp,
                "source": source,
                "sentiment_scores": sentiment_scores,
                "keywords": keywords,
                "market_impact": market_impact,
                "raw_text": text
            }
            
        except Exception as e:
            logger.error(f"Error processing news: {str(e)}")
            raise
            
    def process_social_media(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process social media post
        
        Args:
            post_data: Social media post data
            
        Returns:
            Processed sentiment data
        """
        try:
            # Extract text
            text = post_data.get("text", "")
            platform = post_data.get("platform", "")
            timestamp = post_data.get("timestamp", datetime.now().isoformat())
            
            # Get sentiment scores
            sentiment_scores = self._analyze_sentiment(text)
            
            # Extract keywords
            keywords = self._extract_keywords(text)
            
            # Get market impact
            market_impact = self._calculate_market_impact(sentiment_scores, keywords)
            
            return {
                "timestamp": timestamp,
                "platform": platform,
                "sentiment_scores": sentiment_scores,
                "keywords": keywords,
                "market_impact": market_impact,
                "raw_text": text
            }
            
        except Exception as e:
            logger.error(f"Error processing social media: {str(e)}")
            raise
            
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of sentiment scores
        """
        try:
            # Get transformer sentiment
            transformer_result = self.sentiment_analyzer(text)[0]
            
            # Get TextBlob sentiment
            blob = TextBlob(text)
            textblob_sentiment = blob.sentiment
            
            return {
                "transformer_score": transformer_result["score"],
                "transformer_label": transformer_result["label"],
                "textblob_polarity": textblob_sentiment.polarity,
                "textblob_subjectivity": textblob_sentiment.subjectivity
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            raise
            
    def _extract_keywords(self, text: str) -> Dict[str, List[str]]:
        """Extract keywords from text
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            Dictionary of keyword categories
        """
        try:
            # Convert text to lowercase
            text_lower = text.lower()
            
            # Find market keywords
            market_matches = [k for k in self.market_keywords if k.lower() in text_lower]
            
            # Find sector keywords
            sector_matches = [k for k in self.sector_keywords if k.lower() in text_lower]
            
            return {
                "market_keywords": market_matches,
                "sector_keywords": sector_matches
            }
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            raise
            
    def _calculate_market_impact(
        self,
        sentiment_scores: Dict[str, float],
        keywords: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Calculate market impact of sentiment
        
        Args:
            sentiment_scores: Sentiment analysis scores
            keywords: Extracted keywords
            
        Returns:
            Market impact assessment
        """
        try:
            # Calculate base impact
            transformer_score = sentiment_scores["transformer_score"]
            textblob_polarity = sentiment_scores["textblob_polarity"]
            
            # Weight the scores
            weighted_score = (
                0.7 * transformer_score +
                0.3 * textblob_polarity
            )
            
            # Determine sentiment category
            sentiment_category = "neutral"
            for category, threshold in self.sentiment_thresholds.items():
                if weighted_score >= threshold:
                    sentiment_category = category
                    break
                    
            # Calculate keyword impact
            keyword_impact = len(keywords["market_keywords"]) * 0.1 + len(keywords["sector_keywords"]) * 0.05
            
            # Calculate final impact
            impact_score = weighted_score * (1 + keyword_impact)
            
            return {
                "impact_score": impact_score,
                "sentiment_category": sentiment_category,
                "keyword_impact": keyword_impact,
                "weighted_score": weighted_score
            }
            
        except Exception as e:
            logger.error(f"Error calculating market impact: {str(e)}")
            raise
            
    def save_processed_data(self, data: Dict[str, Any], filepath: str):
        """Save processed sentiment data
        
        Args:
            data: Processed sentiment data
            filepath: Path to save data
        """
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving processed data: {str(e)}")
            raise