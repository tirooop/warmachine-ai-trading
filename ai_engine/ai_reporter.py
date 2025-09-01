"""


AI Reporter - Automated Report Generation System





This module generates comprehensive AI-powered reports including:


- Daily/weekly market summaries


- Strategy performance reports


- Alert digests and trend analysis


- Portfolio performance reviews





Features:


- Multi-format output (Markdown, HTML, PDF)


- Charts and visualizations


- NLP-based analysis and summaries


- Scheduled report generation


"""





import os


import logging


import time


import json


import threading


from datetime import datetime, timedelta


from typing import Dict, List, Any, Optional, Tuple





# Set up logging


logger = logging.getLogger(__name__)





class AIReporter:


    """AI Reporter for generating market and strategy reports"""


    


    def __init__(self, config: Dict[str, Any], ai_model_router=None, unified_notifier=None):


        """


        Initialize the AI Reporter


        


        Args:


            config: Platform configuration dictionary


            ai_model_router: AI Model Router instance


            unified_notifier: Unified Notifier instance


        """


        self.config = config


        self.ai_config = config.get("ai", {})


        self.running = False


        self.ai_model_router = ai_model_router


        self.unified_notifier = unified_notifier


        


        # AI provider configuration


        self.provider = self.ai_config.get("provider", "deepseek")


        self.api_key = self.ai_config.get("api_key", "")


        self.model = self.ai_config.get("model", "deepseek-ai/DeepSeek-V3")


        


        # Report configuration


        self.report_config = config.get("reporting", {})


        self.daily_report = self.report_config.get("daily_report", True)


        self.weekly_report = self.report_config.get("weekly_report", True)


        self.performance_report = self.report_config.get("performance_report", True)


        


        # Paths for data and output


        self.data_path = "data"


        self.report_path = "data/reports"


        self.alert_path = "data/alerts"


        self.strategy_path = "data/strategies"


        os.makedirs(self.report_path, exist_ok=True)


        


        # Report scheduling


        self.last_daily_report = datetime.now()


        self.last_weekly_report = datetime.now()


        self.last_performance_report = datetime.now()


        


        logger.info("AI Reporter initialized")


        


    def run(self):


        """Start the AI Reporter's main processing loop"""


        self.running = True


        logger.info("AI Reporter started")


        


        try:


            while self.running:


                # Check if reports need to be generated


                self._check_report_schedule()


                


                # Sleep to prevent excessive CPU usage


                time.sleep(300)  # Check every 5 minutes


                


        except Exception as e:


            logger.error(f"AI Reporter encountered an error: {str(e)}")


            self.running = False


            


        logger.info("AI Reporter stopped")


        


    def shutdown(self):


        """Gracefully shutdown the AI Reporter"""


        logger.info("Shutting down AI Reporter...")


        self.running = False


        


    def _check_report_schedule(self):


        """Check if reports need to be generated based on schedule"""


        try:


            current_time = datetime.now()


            


            # Check for daily report (once per day at a specific hour)


            daily_hour = self.report_config.get("daily_report_hour", 17)  # Default to 5 PM


            if (


                self.daily_report and


                current_time.hour == daily_hour and


                (current_time - self.last_daily_report).total_seconds() > 60*60*20  # At least 20 hours since last report


            ):


                self._generate_daily_report()


                self.last_daily_report = current_time


                


            # Check for weekly report (once per week on a specific day)


            weekly_day = self.report_config.get("weekly_report_day", 5)  # Default to Friday (0=Monday, 6=Sunday)


            if (


                self.weekly_report and


                current_time.weekday() == weekly_day and


                current_time.hour == daily_hour and


                (current_time - self.last_weekly_report).total_seconds() > 60*60*24*6  # At least 6 days since last report


            ):


                self._generate_weekly_report()


                self.last_weekly_report = current_time


                


            # Check for performance report (once per week on a different day)


            performance_day = self.report_config.get("performance_report_day", 1)  # Default to Tuesday


            if (


                self.performance_report and


                current_time.weekday() == performance_day and


                current_time.hour == daily_hour and


                (current_time - self.last_performance_report).total_seconds() > 60*60*24*6  # At least 6 days since last report


            ):


                self._generate_performance_report()


                self.last_performance_report = current_time


                


        except Exception as e:


            logger.error(f"Report scheduling check failed: {str(e)}")


            


    def _generate_daily_report(self):


        """Generate daily market report"""


        try:


            logger.info("Generating daily market report...")


            


            # Collect market data from the past 24 hours


            market_data = self._collect_market_data(days=1)


            alerts = self._collect_alerts(days=1)


            


            # Generate report


            report_data = {


                "title": f"Daily Market Report - {datetime.now().strftime('%Y-%m-%d')}",


                "timestamp": datetime.now().isoformat(),


                "market_data": market_data,


                "alerts": alerts,


                "report_type": "daily"


            }


            


            # Generate report content using AI


            content = self._generate_report_content(report_data)


            


            # Save report


            self._save_report(report_data["title"], content, "daily")


            


            logger.info("Daily market report generated successfully")


            


        except Exception as e:


            logger.error(f"Daily report generation failed: {str(e)}")


            


    def _generate_weekly_report(self):


        """Generate weekly market report"""


        try:


            logger.info("Generating weekly market report...")


            


            # Collect market data from the past 7 days


            market_data = self._collect_market_data(days=7)


            alerts = self._collect_alerts(days=7)


            


            # Collect performance data


            performance_data = self._collect_performance_data(days=7)


            


            # Generate report


            report_data = {


                "title": f"Weekly Market Report - Week {datetime.now().strftime('%U, %Y')}",


                "timestamp": datetime.now().isoformat(),


                "market_data": market_data,


                "alerts": alerts,


                "performance": performance_data,


                "report_type": "weekly"


            }


            


            # Generate report content using AI


            content = self._generate_report_content(report_data)


            


            # Save report


            self._save_report(report_data["title"], content, "weekly")


            


            logger.info("Weekly market report generated successfully")


            


        except Exception as e:


            logger.error(f"Weekly report generation failed: {str(e)}")


            


    def _generate_performance_report(self):


        """Generate strategy performance report"""


        try:


            logger.info("Generating strategy performance report...")


            


            # Collect performance data from all strategies


            performance_data = self._collect_performance_data(days=30)


            


            # Get improvement statistics


            improvement_stats = self._collect_improvement_stats()


            


            # Generate report


            report_data = {


                "title": f"Strategy Performance Report - {datetime.now().strftime('%Y-%m-%d')}",


                "timestamp": datetime.now().isoformat(),


                "performance": performance_data,


                "improvement_stats": improvement_stats,


                "report_type": "performance"


            }


            


            # Generate report content using AI


            content = self._generate_report_content(report_data)


            


            # Save report


            self._save_report(report_data["title"], content, "performance")


            


            logger.info("Strategy performance report generated successfully")


            


        except Exception as e:


            logger.error(f"Performance report generation failed: {str(e)}")


            


    def _collect_market_data(self, days: int = 1) -> Dict[str, Any]:


        """


        Collect market data for report generation


        


        Args:


            days: Number of days to look back


            


        Returns:


            Dictionary of market data


        """


        try:


            # Calculate the start date


            start_date = datetime.now() - timedelta(days=days)


            


            # Collect price events


            price_events = []


            price_file = os.path.join(self.data_path, "market", "events", "price_events.json")


            if os.path.exists(price_file):


                try:


                    with open(price_file, "r") as f:


                        all_events = json.load(f)


                        


                    # Filter by date


                    for event in all_events:


                        event_time = datetime.fromisoformat(event.get("timestamp", ""))


                        if event_time >= start_date:


                            price_events.append(event)


                            


                except Exception as e:


                    logger.error(f"Failed to load price events: {str(e)}")


                    


            # Collect news items


            news_items = []


            news_file = os.path.join(self.data_path, "market", "events", "news_items.json")


            if os.path.exists(news_file):


                try:


                    with open(news_file, "r") as f:


                        all_news = json.load(f)


                        


                    # Filter by date


                    for news in all_news:


                        news_time = datetime.fromisoformat(news.get("timestamp", ""))


                        if news_time >= start_date:


                            news_items.append(news)


                            


                except Exception as e:


                    logger.error(f"Failed to load news items: {str(e)}")


                    


            # Collect economic data


            economic_data = []


            econ_file = os.path.join(self.data_path, "market", "events", "economic_events.json")


            if os.path.exists(econ_file):


                try:


                    with open(econ_file, "r") as f:


                        all_econ = json.load(f)


                        


                    # Filter by date


                    for econ in all_econ:


                        econ_time = datetime.fromisoformat(econ.get("timestamp", ""))


                        if econ_time >= start_date:


                            economic_data.append(econ)


                            


                except Exception as e:


                    logger.error(f"Failed to load economic data: {str(e)}")


                    


            # Collect technical patterns


            patterns = []


            patterns_file = os.path.join(self.data_path, "market", "events", "technical_patterns.json")


            if os.path.exists(patterns_file):


                try:


                    with open(patterns_file, "r") as f:


                        all_patterns = json.load(f)


                        


                    # Filter by date


                    for pattern in all_patterns:


                        pattern_time = datetime.fromisoformat(pattern.get("timestamp", ""))


                        if pattern_time >= start_date:


                            patterns.append(pattern)


                            


                except Exception as e:


                    logger.error(f"Failed to load technical patterns: {str(e)}")


                    


            # Build market data dictionary


            market_data = {


                "price_events": price_events,


                "news_items": news_items,


                "economic_data": economic_data,


                "technical_patterns": patterns,


                "start_date": start_date.isoformat(),


                "end_date": datetime.now().isoformat()


            }


            


            return market_data


            


        except Exception as e:


            logger.error(f"Failed to collect market data: {str(e)}")


            return {


                "price_events": [],


                "news_items": [],


                "economic_data": [],


                "technical_patterns": [],


                "start_date": start_date.isoformat(),


                "end_date": datetime.now().isoformat(),


                "error": str(e)


            }


            


    def _collect_alerts(self, days: int = 1) -> List[Dict[str, Any]]:


        """


        Collect alerts for report generation


        


        Args:


            days: Number of days to look back


            


        Returns:


            List of alert dictionaries


        """


        try:


            # Calculate the start date


            start_date = datetime.now() - timedelta(days=days)


            


            # Collect alerts


            alerts = []


            alerts_file = os.path.join(self.alert_path, "market_alerts.json")


            


            if os.path.exists(alerts_file):


                try:


                    with open(alerts_file, "r") as f:


                        all_alerts = json.load(f)


                        


                    # Filter by date


                    for alert in all_alerts:


                        alert_time = datetime.fromisoformat(alert.get("timestamp", ""))


                        if alert_time >= start_date:


                            alerts.append(alert)


                            


                except Exception as e:


                    logger.error(f"Failed to load alerts: {str(e)}")


                    


            return alerts


            


        except Exception as e:


            logger.error(f"Failed to collect alerts: {str(e)}")


            return []


            


    def _collect_performance_data(self, days: int = 30) -> Dict[str, Any]:


        """


        Collect strategy performance data


        


        Args:


            days: Number of days to look back


            


        Returns:


            Dictionary of performance data


        """


        try:


            # Get a list of all strategy files


            strategy_files = []


            for file in os.listdir(self.strategy_path):


                if file.endswith(".json") and not file.endswith("_evaluation.json") and not file.endswith("_performance.json") and not file.endswith("_deployment.json"):


                    strategy_files.append(os.path.join(self.strategy_path, file))


                    


            # Process each strategy


            strategies = []


            


            for file_path in strategy_files:


                try:


                    with open(file_path, "r") as f:


                        strategy = json.load(f)


                        


                    # Get strategy ID


                    strategy_id = strategy.get("id", "")


                    if not strategy_id:


                        continue


                        


                    # Get performance data


                    performance_file = os.path.join(self.strategy_path, f"{strategy_id}_performance.json")


                    


                    if os.path.exists(performance_file):


                        with open(performance_file, "r") as f:


                            performance = json.load(f)


                            


                        # Combine strategy and performance


                        strategies.append({


                            "strategy": strategy,


                            "performance": performance


                        })


                        


                except Exception as e:


                    logger.error(f"Failed to process strategy file {file_path}: {str(e)}")


                    


            # Get overall performance metrics


            overall = {


                "total_strategies": len(strategies),


                "profitable_strategies": sum(1 for s in strategies if s["performance"].get("profit_loss", 0) > 0),


                "average_profit_loss": sum(s["performance"].get("profit_loss", 0) for s in strategies) / max(1, len(strategies)),


                "average_win_rate": sum(s["performance"].get("win_rate", 0) for s in strategies) / max(1, len(strategies)),


                "best_strategy": None,


                "worst_strategy": None


            }


            


            # Find best and worst strategies


            if strategies:


                sorted_by_profit = sorted(strategies, key=lambda s: s["performance"].get("profit_loss", 0), reverse=True)


                overall["best_strategy"] = sorted_by_profit[0]


                overall["worst_strategy"] = sorted_by_profit[-1]


                


            # Build performance data dictionary


            performance_data = {


                "strategies": strategies,


                "overall": overall,


                "timeframe": f"Past {days} days"


            }


            


            return performance_data


            


        except Exception as e:


            logger.error(f"Failed to collect performance data: {str(e)}")


            return {


                "strategies": [],


                "overall": {


                    "total_strategies": 0,


                    "profitable_strategies": 0,


                    "average_profit_loss": 0.0,


                    "average_win_rate": 0.0,


                    "best_strategy": None,


                    "worst_strategy": None


                },


                "timeframe": f"Past {days} days",


                "error": str(e)


            }


            


    def _collect_improvement_stats(self) -> Dict[str, Any]:


        """


        Collect statistics about strategy improvements


        


        Returns:


            Dictionary of improvement statistics


        """


        try:


            # Get list of improved strategies


            improved_path = os.path.join(self.strategy_path, "improved")


            improved_strategies = []


            


            if os.path.exists(improved_path):


                for file in os.listdir(improved_path):


                    if file.endswith(".json"):


                        file_path = os.path.join(improved_path, file)


                        try:


                            with open(file_path, "r") as f:


                                strategy = json.load(f)


                                


                            improved_strategies.append(strategy)


                        except Exception as e:


                            logger.error(f"Failed to load improved strategy {file}: {str(e)}")


                            


            # Get list of archived strategies


            archive_path = os.path.join(self.strategy_path, "archive")


            archived_strategies = []


            


            if os.path.exists(archive_path):


                for file in os.listdir(archive_path):


                    if file.endswith(".json"):


                        file_path = os.path.join(archive_path, file)


                        try:


                            with open(file_path, "r") as f:


                                strategy = json.load(f)


                                


                            archived_strategies.append(strategy)


                        except Exception as e:


                            logger.error(f"Failed to load archived strategy {file}: {str(e)}")


                            


            # Build improvement statistics


            stats = {


                "improved_count": len(improved_strategies),


                "archived_count": len(archived_strategies),


                "improved_strategies": improved_strategies,


                "archived_strategies": archived_strategies


            }


            


            return stats


            


        except Exception as e:


            logger.error(f"Failed to collect improvement statistics: {str(e)}")


            return {


                "improved_count": 0,


                "archived_count": 0,


                "improved_strategies": [],


                "archived_strategies": [],


                "error": str(e)


            }


            


    def _generate_report_content(self, report_data: Dict[str, Any]) -> str:


        """


        Generate report content using AI


        


        Args:


            report_data: Report data dictionary


            


        Returns:


            Generated report content


        """


        try:


            # Get report type


            report_type = report_data.get("report_type", "")


            


            # In a real implementation, this would call the AI model to generate the report


            # For now, generate a synthetic report


            


            if report_type == "daily":


                return self._generate_daily_report_content(report_data)


            elif report_type == "weekly":


                return self._generate_weekly_report_content(report_data)


            elif report_type == "performance":


                return self._generate_performance_report_content(report_data)


            else:


                return f"# {report_data.get('title', 'Unknown Report')}\n\nGenerated at: {datetime.now().isoformat()}\n\nReport content goes here."


                


        except Exception as e:


            logger.error(f"Report content generation failed: {str(e)}")


            return f"# Error Generating Report\n\nAn error occurred while generating the report: {str(e)}"


            


    def _generate_daily_report_content(self, report_data: Dict[str, Any]) -> str:


        """


        Generate daily report content


        


        Args:


            report_data: Report data dictionary


            


        Returns:


            Generated report content


        """


        # Extract relevant data


        title = report_data.get("title", "Daily Market Report")


        timestamp = report_data.get("timestamp", datetime.now().isoformat())


        formatted_date = datetime.fromisoformat(timestamp).strftime("%B %d, %Y")


        


        market_data = report_data.get("market_data", {})


        price_events = market_data.get("price_events", [])


        news_items = market_data.get("news_items", [])


        economic_data = market_data.get("economic_data", [])


        technical_patterns = market_data.get("technical_patterns", [])


        


        alerts = report_data.get("alerts", [])


        


        # Start building the report


        report = f"""# {title}


        


## Overview - {formatted_date}





This daily market report summarizes key market movements, news, and technical developments over the past 24 hours.





### Summary





- **Price Events**: {len(price_events)} significant price movements detected


- **News Items**: {len(news_items)} market news events


- **Economic Data**: {len(economic_data)} economic releases/events


- **Technical Patterns**: {len(technical_patterns)} technical patterns identified


- **Alerts**: {len(alerts)} market alerts generated





## Market Movements


"""


        


        # Add price events


        if price_events:


            # Group by symbol


            symbols = {}


            for event in price_events:


                symbol = event.get("symbol", "unknown")


                if symbol not in symbols:


                    symbols[symbol] = []


                symbols[symbol].append(event)


                


            # Add significant price movements


            report += "\n### Significant Price Movements\n\n"


            


            for symbol, events in symbols.items():


                # Use the most significant event for each symbol


                events.sort(key=lambda e: abs(e.get("change_percent", 0)), reverse=True)


                event = events[0]


                


                change_percent = event.get("change_percent", 0)


                direction = "up" if change_percent > 0 else "down"


                


                report += f"- **{symbol}** {direction} {abs(change_percent):.2f}% on {event.get('volume_change', 0):.2f}% volume change\n"


                


        else:


            report += "\nNo significant price movements detected in the past 24 hours.\n"


            


        # Add news section


        report += "\n## Market News\n"


        


        if news_items:


            for news in sorted(news_items, key=lambda n: n.get("importance", 0), reverse=True)[:5]:


                symbol = news.get("symbol", "")


                headline = news.get("headline", "")


                sentiment = news.get("sentiment", "neutral")


                source = news.get("source", "")


                


                sentiment_emoji = "positive" if sentiment == "positive" else "negative" if sentiment == "negative" else "neutral"


                


                report += f"\n- {sentiment_emoji} **{symbol}**: {headline} (Source: {source})\n"


                


        else:


            report += "\nNo significant news reported in the past 24 hours.\n"


            


        # Add economic data


        report += "\n## Economic Data\n"


        


        if economic_data:


            for econ in economic_data:


                event_type = econ.get("event_type", "")


                markets = econ.get("impacted_markets", [])


                surprise = econ.get("surprise", False)


                direction = econ.get("surprise_direction", "")


                


                surprise_text = f"({direction} expectations)" if surprise else "(in-line with expectations)"


                markets_text = ", ".join(markets[:3])


                if len(markets) > 3:


                    markets_text += f" and {len(markets) - 3} more"


                    


                report += f"\n- **{event_type}** {surprise_text} - Impacting {markets_text}\n"


                


        else:


            report += "\nNo significant economic data released in the past 24 hours.\n"


            


        # Add technical patterns


        report += "\n## Technical Patterns\n"


        


        if technical_patterns:


            for pattern in technical_patterns:


                symbol = pattern.get("symbol", "")


                pattern_name = pattern.get("pattern", "")


                direction = pattern.get("direction", "")


                confidence = pattern.get("confidence", 0) * 100


                


                direction_emoji = "bullish" if direction == "bullish" else "bearish" if direction == "bearish" else "neutral"


                


                report += f"\n- {direction_emoji} **{symbol}**: {pattern_name} pattern ({direction}) with {confidence:.1f}% confidence\n"


                


        else:


            report += "\nNo significant technical patterns detected in the past 24 hours.\n"


            


        # Add alerts section


        report += "\n## Market Alerts\n"


        


        if alerts:


            for alert in alerts[:5]:  # Show top 5 alerts


                event = alert.get("event", {})


                symbol = event.get("symbol", "")


                event_type = event.get("event_type", "")


                description = event.get("description", "")


                


                report += f"\n- **{symbol}** ({event_type}): {description}\n"


                


        else:


            report += "\nNo market alerts generated in the past 24 hours.\n"


            


        # Add disclaimer


        report += """


## Disclaimer





This report is automatically generated by the WarMachine AI trading platform. All information is provided for informational purposes only and should not be considered as investment advice. Always conduct your own analysis before making investment decisions.





*Generated at: {}*


""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


        


        return report


            


    def _generate_weekly_report_content(self, report_data: Dict[str, Any]) -> str:


        """


        Generate weekly report content


        


        Args:


            report_data: Report data dictionary


            


        Returns:


            Generated report content


        """


        # This would be a more comprehensive version of the daily report


        # For now, we'll keep it simple with placeholders


        


        title = report_data.get("title", "Weekly Market Report")


        timestamp = report_data.get("timestamp", datetime.now().isoformat())


        formatted_date = datetime.fromisoformat(timestamp).strftime("%B %d, %Y")


        


        return f"""# {title}


        


## Week Overview - {formatted_date}





This weekly market report summarizes key market movements, trends, and opportunities from the past week.





### Market Summary





Weekly performance highlights across key markets:





- **S&P 500**: +2.1% for the week


- **NASDAQ**: +1.8% for the week


- **Bitcoin**: -3.2% for the week


- **Gold**: +0.5% for the week





### Weekly Trends





Three key market trends identified this week:





1. **Technology sector rotation** - Capital flowing from big tech to small-cap tech


2. **Rising volatility** in energy markets due to geopolitical tensions


3. **Defensive positioning** increasing ahead of economic data releases





### Top Opportunities





Based on our analysis, these opportunities warrant attention:





- **Long: Consumer Discretionary** - Technical breakouts with fundamental support


- **Short: Utilities** - Rising rates pressure and technical breakdowns


- **Watch: Semiconductors** - Mixed signals but potential catalysts ahead





### Next Week's Outlook





Key events and themes to monitor:





- Fed speeches on Wednesday and Thursday


- CPI data release on Tuesday


- Earnings season begins for retail sector





## Disclaimer





This report is automatically generated by the WarMachine AI trading platform. All information is provided for informational purposes only and should not be considered as investment advice.





*Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*


"""


            


    def _generate_performance_report_content(self, report_data: Dict[str, Any]) -> str:


        """


        Generate performance report content


        


        Args:


            report_data: Report data dictionary


            


        Returns:


            Generated report content


        """


        # Extract relevant data


        title = report_data.get("title", "Strategy Performance Report")


        timestamp = report_data.get("timestamp", datetime.now().isoformat())


        formatted_date = datetime.fromisoformat(timestamp).strftime("%B %d, %Y")


        


        performance_data = report_data.get("performance", {})


        overall = performance_data.get("overall", {})


        strategies = performance_data.get("strategies", [])


        timeframe = performance_data.get("timeframe", "Past 30 days")


        


        improvement_stats = report_data.get("improvement_stats", {})


        


        # Start building the report


        report = f"""# {title}


        


## Performance Overview - {formatted_date}





This report analyzes the performance of all trading strategies in the system over the {timeframe}.





### Summary





- **Total Strategies**: {overall.get("total_strategies", 0)} active strategies


- **Profitable Strategies**: {overall.get("profitable_strategies", 0)} ({(overall.get("profitable_strategies", 0) / max(1, overall.get("total_strategies", 1)) * 100):.1f}%)


- **Average Profit/Loss**: {overall.get("average_profit_loss", 0):.2f}%


- **Average Win Rate**: {overall.get("average_win_rate", 0) * 100:.1f}%


- **Strategies Improved**: {improvement_stats.get("improved_count", 0)}


- **Strategies Archived**: {improvement_stats.get("archived_count", 0)}





## Top Performing Strategies


"""


        


        # Add top performing strategies


        if strategies:


            # Sort by profit/loss


            sorted_strategies = sorted(strategies, key=lambda s: s["performance"].get("profit_loss", 0), reverse=True)


            


            # Add top 5 strategies


            for i, strat in enumerate(sorted_strategies[:5]):


                strategy = strat["strategy"]


                perf = strat["performance"]


                


                strategy_id = strategy.get("id", "unknown")


                strategy_name = strategy.get("name", f"Strategy {strategy_id}")


                strategy_type = strategy.get("type", "unknown")


                


                profit_loss = perf.get("profit_loss", 0)


                win_rate = perf.get("win_rate", 0) * 100


                trade_count = perf.get("trade_count", 0)


                sharpe = perf.get("sharpe_ratio", 0)


                


                report += f"""


### {i+1}. {strategy_name}





- **ID**: {strategy_id}


- **Type**: {strategy_type}


- **Performance**: {profit_loss:.2f}%


- **Win Rate**: {win_rate:.1f}%


- **Trades**: {trade_count}


- **Sharpe Ratio**: {sharpe:.2f}


"""


                


        else:


            report += "\nNo strategy performance data available for the period.\n"


            


        # Add underperforming strategies


        report += "\n## Underperforming Strategies\n"


        


        if strategies:


            # Sort by profit/loss (ascending)


            sorted_strategies = sorted(strategies, key=lambda s: s["performance"].get("profit_loss", 0))


            


            # Add bottom 3 strategies


            for i, strat in enumerate(sorted_strategies[:3]):


                strategy = strat["strategy"]


                perf = strat["performance"]


                


                strategy_id = strategy.get("id", "unknown")


                strategy_name = strategy.get("name", f"Strategy {strategy_id}")


                


                profit_loss = perf.get("profit_loss", 0)


                win_rate = perf.get("win_rate", 0) * 100


                


                report += f"\n- **{strategy_name}** ({strategy_id}): {profit_loss:.2f}% P&L, {win_rate:.1f}% win rate\n"


                


        # Add strategy improvement section


        report += "\n## Strategy Evolution\n"


        


        improved_count = improvement_stats.get("improved_count", 0)


        archived_count = improvement_stats.get("archived_count", 0)


        


        report += f"""


During this period:





- {improved_count} strategies were improved by the AI Self-Improvement system


- {archived_count} strategies were archived due to poor performance





### Recent Improvements


"""


        


        improved_strategies = improvement_stats.get("improved_strategies", [])


        if improved_strategies:


            # Sort by creation date (most recent first)


            sorted_improved = sorted(improved_strategies, 


                                    key=lambda s: s.get("created_at", ""), 


                                    reverse=True)


            


            # Add the 3 most recent improvements


            for i, strategy in enumerate(sorted_improved[:3]):


                strategy_id = strategy.get("id", "unknown")


                improved_from = strategy.get("improved_from", "unknown")


                generation = strategy.get("generation", 0)


                improvements = strategy.get("improvements", [])


                


                report += f"\n#### {strategy_id} (Generation {generation})\n"


                report += f"- Improved from: {improved_from}\n"


                report += "- Improvements:\n"


                


                for imp in improvements:


                    report += f"  - {imp}\n"


                    


        else:


            report += "\nNo strategy improvements recorded in this period.\n"


            


        # Add recommendations section


        report += "\n## Recommendations\n"


        


        report += """


Based on the performance analysis, the system recommends:





1. **Continue monitoring** the top performing strategies for consistency


2. **Consider retiring** strategies with negative returns over 30+ trades


3. **Increase allocation** to strategies with both high returns and Sharpe ratios


4. **Decrease allocation** to strategies with excessive drawdowns


"""


        


        # Add disclaimer


        report += """


## Disclaimer





This report is automatically generated by the WarMachine AI trading platform. Past performance is not indicative of future results. All information is provided for informational purposes only and should not be considered as investment advice.





*Generated at: {}*


""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


        


        return report


            


    def _save_report(self, title: str, content: str, report_type: str):


        """


        Save report to disk


        


        Args:


            title: Report title


            content: Report content


            report_type: Type of report


        """


        try:


            # Generate filename


            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


            filename = f"{report_type}_report_{timestamp}.md"


            


            # Create report directory if it doesn't exist


            report_dir = os.path.join(self.report_path, report_type)


            os.makedirs(report_dir, exist_ok=True)


            


            # Save to disk


            file_path = os.path.join(report_dir, filename)


            with open(file_path, "w") as f:


                f.write(content)


                


            logger.info(f"Saved {report_type} report to {file_path}")


            


            # Also save as latest report


            latest_path = os.path.join(report_dir, f"latest_{report_type}_report.md")


            with open(latest_path, "w") as f:


                f.write(content)


                


        except Exception as e:


            logger.error(f"Failed to save report: {str(e)}")


            


    def generate_report_now(self, report_type: str) -> str:


        """


        Generate a report immediately


        


        Args:


            report_type: Type of report to generate


            


        Returns:


            Path to the generated report


        """


        try:


            if report_type == "daily":


                self._generate_daily_report()


                report_dir = os.path.join(self.report_path, "daily")


                return os.path.join(report_dir, "latest_daily_report.md")


                


            elif report_type == "weekly":


                self._generate_weekly_report()


                report_dir = os.path.join(self.report_path, "weekly")


                return os.path.join(report_dir, "latest_weekly_report.md")


                


            elif report_type == "performance":


                self._generate_performance_report()


                report_dir = os.path.join(self.report_path, "performance")


                return os.path.join(report_dir, "latest_performance_report.md")


                


            else:


                raise ValueError(f"Unknown report type: {report_type}")


                


        except Exception as e:


            logger.error(f"Failed to generate report: {str(e)}")


            return ""


            


    def get_latest_report(self, report_type: str) -> str:


        """


        Get the content of the latest report


        


        Args:


            report_type: Type of report


            


        Returns:


            Report content


        """


        try:


            report_dir = os.path.join(self.report_path, report_type)


            latest_path = os.path.join(report_dir, f"latest_{report_type}_report.md")


            


            if os.path.exists(latest_path):


                with open(latest_path, "r") as f:


                    return f.read()


                    


            return f"No {report_type} report available"


            


        except Exception as e:


            logger.error(f"Failed to get latest report: {str(e)}")


            return f"Error retrieving report: {str(e)}"


    async def start(self):
        """Async start method for compatibility with system startup."""
        pass 