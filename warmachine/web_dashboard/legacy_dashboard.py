"""


Web Dashboard - Streamlit user interface for WarMachine platform





This module provides a web-based user interface for the WarMachine trading platform,





allowing users to visualize data, manage strategies, and interact with the system.


"""





import os


import logging


import json


import time


import asyncio


import threading


import requests


import pandas as pd


import numpy as np


import plotly.graph_objects as go


import plotly.express as px


from datetime import datetime, timedelta


from typing import Dict, Any, Optional, List, Union


from pathlib import Path





import streamlit as st


import extra_streamlit_components as stx


from streamlit_autorefresh import st_autorefresh


from streamlit_option_menu import option_menu





# Set up logging


logger = logging.getLogger(__name__)





class WebDashboard:


    """Streamlit web dashboard for the WarMachine platform"""


    


    def __init__(self, config: Dict[str, Any]):


        """


        Initialize the Web Dashboard


        


        Args:


            config: Configuration dictionary


        """


        self.config = config


        self.web_config = config.get("web_dashboard", {})


        self.thread = None


        self.running = False


        self._shutdown_event = threading.Event()


        


        # API configuration


        self.api_host = self.web_config.get("api_host", "localhost")


        self.api_port = self.web_config.get("api_port", 8000)


        self.api_url = f"http://{self.api_host}:{self.api_port}/api"


        


        # Dashboard configuration


        self.dashboard_host = self.web_config.get("dashboard_host", "localhost")


        self.dashboard_port = self.web_config.get("dashboard_port", 8501)


        


        # Theme configuration


        self.theme = self.web_config.get("theme", {})


        self.colors = {


            "primary": self.theme.get("primary_color", "#1E88E5"),


            "secondary": self.theme.get("secondary_color", "#FF5722"),


            "background": self.theme.get("background_color", "#FFFFFF"),


            "text": self.theme.get("text_color", "#212121"),


            "success": self.theme.get("success_color", "#4CAF50"),


            "danger": self.theme.get("danger_color", "#F44336"),


            "warning": self.theme.get("warning_color", "#FFC107"),


            "info": self.theme.get("info_color", "#2196F3")


        }


        


        logger.info(f"Web Dashboard initialized on {self.dashboard_host}:{self.dashboard_port}")


        


    async def start(self):


        """Start the Web Dashboard in non-blocking mode"""


        if not self.thread:


            self.running = True


            self._shutdown_event.clear()


            


            self.thread = threading.Thread(


                target=self._run_dashboard,


                daemon=True,


                name="WebDashboardThread"


            )


            self.thread.start()


            logger.info("Web Dashboard started in background thread")


            return True


        return False





    async def shutdown(self):


        """Gracefully shutdown the Web Dashboard"""


        logger.info("Shutting down Web Dashboard...")


        self.running = False


        self._shutdown_event.set()


        


        if self.thread and self.thread.is_alive():


            # Wait for thread to finish


            self.thread.join(timeout=5.0)


            if self.thread.is_alive():


                logger.warning("Web Dashboard thread did not stop gracefully")


        


        logger.info("Web Dashboard shutdown complete")


        


    def _run_dashboard(self):


        """Run the Streamlit dashboard"""


        try:


            # Set environment variables for Streamlit


            os.environ["STREAMLIT_SERVER_PORT"] = str(self.dashboard_port)


            os.environ["STREAMLIT_SERVER_ADDRESS"] = self.dashboard_host


            


            # Import streamlit here to avoid circular imports


            import streamlit.web.cli as stcli


            


            # Run Streamlit


            sys.argv = ["streamlit", "run", __file__, "--server.port", str(self.dashboard_port)]


            stcli.main()


            


        except Exception as e:


            logger.error(f"Failed to start Web Dashboard: {str(e)}")


            self.running = False


            


    def get_api_url(self, endpoint: str) -> str:


        """


        Get full API URL for endpoint


        


        Args:


            endpoint: API endpoint path


            


        Returns:


            Full API URL


        """


        # Ensure endpoint starts with /


        if not endpoint.startswith("/"):


            endpoint = f"/{endpoint}"


            


        return f"{self.api_url}{endpoint}"





    async def is_running(self) -> bool:


        """Check if the dashboard is running"""


        return self.running and self.thread and self.thread.is_alive()





    async def get_status(self) -> Dict[str, Any]:


        """Get dashboard status"""


        return {


            "running": self.running,


            "thread_alive": self.thread and self.thread.is_alive(),


            "host": self.dashboard_host,


            "port": self.dashboard_port,


            "api_url": self.api_url


        }





# Dashboard pages


def login_page():


    """Login page"""


    st.title("WarMachine Trading Platform")


    


    with st.container():


        st.subheader("Login")


        


        # Login form


        with st.form("login_form"):


            email = st.text_input("Email")


            password = st.text_input("Password", type="password")


            submitted = st.form_submit_button("Login")


            


            if submitted:


                try:


                    # This would call the API for authentication


                    # For now, just simulate successful login


                    if email and password:


                        st.session_state["authenticated"] = True


                        st.session_state["user"] = {


                            "id": "user_123",


                            "username": "demo_user",


                            "email": email,


                            "level": "trader"


                        }


                        st.session_state["token"] = "dummy_token"


                        st.experimental_rerun()


                    else:


                        st.error("Please enter email and password")


                except Exception as e:


                    st.error(f"Login failed: {str(e)}")


                    


        # Registration link


        st.markdown("---")


        st.markdown("Don't have an account? [Register here](#register)")





def register_page():


    """Registration page"""


    st.title("WarMachine Trading Platform")


    


    with st.container():


        st.subheader("Create an Account")


        


        # Registration form


        with st.form("register_form"):


            username = st.text_input("Username")


            email = st.text_input("Email")


            password = st.text_input("Password", type="password")


            confirm_password = st.text_input("Confirm Password", type="password")


            submitted = st.form_submit_button("Register")


            


            if submitted:


                try:


                    # Validate inputs


                    if not username or not email or not password:


                        st.error("Please fill in all fields")


                    elif password != confirm_password:


                        st.error("Passwords do not match")


                    else:


                        # This would call the API for registration


                        # For now, just simulate successful registration


                        st.success("Registration successful! Please login.")


                except Exception as e:


                    st.error(f"Registration failed: {str(e)}")


                    


        # Login link


        st.markdown("---")


        st.markdown("Already have an account? [Login here](#login)")





def dashboard_page():


    """Main dashboard page"""


    st.title(f"Welcome, {st.session_state['user']['username']}!")


    


    # Auto-refresh every 5 minutes


    st_autorefresh(interval=300000, key="dashboard_refresh")


    


    # System status card


    with st.container():


        st.subheader("System Status")


        


        col1, col2, col3, col4 = st.columns(4)


        


        with col1:


            st.metric("Active Strategies", "7", "+2")


            


        with col2:


            st.metric("Signals Today", "15", "+3")


            


        with col3:


            st.metric("Portfolio Value", "$105,243.78", "+0.75%")


            


        with col4:


            st.metric("Market Trend", "Bullish", "SPY +0.6%")


            


    # Recent signals


    with st.container():


        st.subheader("Recent Signals")


        


        signals = [


            {"symbol": "SPY", "action": "BUY", "time": "10:15 AM", "reason": "Upward momentum detected"},


            {"symbol": "QQQ", "action": "SELL", "time": "10:30 AM", "reason": "Downward trend confirmed"},


            {"symbol": "AAPL", "action": "BUY", "time": "11:45 AM", "reason": "Oversold condition"}


        ]


        


        # Create a DataFrame for the signals


        df = pd.DataFrame(signals)


        


        # Style the table


        def color_action(val):


            color = "green" if val == "BUY" else "red" if val == "SELL" else "gray"


            return f"color: {color}; font-weight: bold"


            


        styled_df = df.style.applymap(color_action, subset=["action"])


        


        st.dataframe(styled_df, use_container_width=True)


        


    # Market overview chart


    with st.container():


        st.subheader("Market Overview")


        


        # Sample data for demonstration


        dates = pd.date_range(start="2023-01-01", end="2023-07-01", freq="D")


        spy_values = np.random.normal(loc=1.0, scale=0.01, size=len(dates)).cumsum() + 100


        qqq_values = np.random.normal(loc=1.001, scale=0.015, size=len(dates)).cumsum() + 100


        


        # Create DataFrame


        df = pd.DataFrame({


            "date": dates,


            "SPY": spy_values,


            "QQQ": qqq_values


        })


        


        # Create and display the chart


        fig = go.Figure()


        


        fig.add_trace(go.Scatter(


            x=df["date"],


            y=df["SPY"],


            mode="lines",


            name="SPY",


            line=dict(color="#1E88E5", width=2)


        ))


        


        fig.add_trace(go.Scatter(


            x=df["date"],


            y=df["QQQ"],


            mode="lines",


            name="QQQ",


            line=dict(color="#FF5722", width=2)


        ))


        


        fig.update_layout(


            height=400,


            margin=dict(l=0, r=0, t=0, b=0),


            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),


            xaxis=dict(


                showgrid=False,


                zeroline=False


            ),


            yaxis=dict(


                showgrid=True,


                gridcolor="rgba(0,0,0,0.1)"


            ),


            plot_bgcolor="rgba(0,0,0,0)",


            paper_bgcolor="rgba(0,0,0,0)"


        )


        


        st.plotly_chart(fig, use_container_width=True)


        


    # AI Market Analysis


    with st.container():


        st.subheader("AI Market Analysis")


        


        # Placeholder for AI analysis


        analysis = """


        ## Current Market Conditions


        


        The market is showing resilience despite mixed economic data. Tech sector leading gains while crypto faces pressure.


        


        ### Key Observations:


        - SPY is trending higher with strong momentum


        - AAPL's earnings beat expectations, driving tech sector


        - Recent inflation data suggests the Fed may pause rate hikes


        


        ### Actions to Consider:


        - Consider adding exposure to technology and AI-related sectors


        - Maintain a balanced portfolio with some defensive positions


        - Watch for short-term pullbacks as potential entry points


        """


        


        st.markdown(analysis)





def strategies_page():


    """Strategies page"""


    st.title("Trading Strategies")


    


    # Strategy filter and search


    col1, col2 = st.columns([3, 1])


    


    with col1:


        search = st.text_input("Search strategies", placeholder="Enter keywords...")


        


    with col2:


        filter_option = st.selectbox("Filter by", ["All", "Public", "Subscribed", "AI-Generated"])


        


    # Strategy cards


    strategies = [


        {


            "id": "strategy_123456",


            "name": "Momentum ETF v2",


            "description": "Momentum-based ETF rotation strategy with weekly rebalancing",


            "type": "momentum",


            "is_public": True,


            "return": 12.3,


            "sharpe": 1.85,


            "subscribed": True


        },


        {


            "id": "strategy_234567",


            "name": "Tech Sector Rotation",


            "description": "Sector rotation focusing on technology stocks",


            "type": "sector",


            "is_public": True,


            "return": 9.8,


            "sharpe": 1.62,


            "subscribed": False


        },


        {


            "id": "strategy_345678",


            "name": "MACD Crossover v3",


            "description": "Technical trading using MACD crossovers",


            "type": "technical",


            "is_public": False,


            "return": 15.4,


            "sharpe": 1.95,


            "subscribed": True


        }


    ]


    


    # Filter strategies based on selection


    if filter_option == "Public":


        strategies = [s for s in strategies if s["is_public"]]


    elif filter_option == "Subscribed":


        strategies = [s for s in strategies if s["subscribed"]]


        


    # Filter by search term


    if search:


        search = search.lower()


        strategies = [s for s in strategies if search in s["name"].lower() or search in s["description"].lower()]


        


    # Create strategy cards


    for i, strategy in enumerate(strategies):


        with st.container():


            col1, col2 = st.columns([3, 1])


            


            with col1:


                st.subheader(strategy["name"])


                st.write(strategy["description"])


                st.caption(f"Type: {strategy['type'].capitalize()}")


                


            with col2:


                st.metric("Return", f"{strategy['return']}%")


                st.metric("Sharpe", f"{strategy['sharpe']}")


                


                if strategy["subscribed"]:


                    st.button("Unsubscribe", key=f"unsub_{i}")


                else:


                    st.button("Subscribe", key=f"sub_{i}")


                    


            st.markdown("---")


            


    # Create new strategy button


    st.button("Create New Strategy", type="primary")





def portfolios_page():


    """Portfolios page"""


    st.title("Portfolios")


    


    # Create new portfolio


    with st.expander("Create New Portfolio"):


        with st.form("create_portfolio"):


            name = st.text_input("Portfolio Name")


            description = st.text_area("Description")


            initial_balance = st.number_input("Initial Balance", min_value=1000.0, value=10000.0, step=1000.0)


            submitted = st.form_submit_button("Create Portfolio")


            


            if submitted:


                if name:


                    st.success(f"Portfolio '{name}' created successfully!")


                else:


                    st.error("Please enter a portfolio name")


                    


    # Portfolio list


    portfolios = [


        {


            "id": "portfolio_123456",


            "name": "Tech Growth",


            "description": "High-growth technology stocks",


            "balance": 105243.78,


            "return": 5.24,


            "positions": 5


        },


        {


            "id": "portfolio_234567",


            "name": "Dividend Income",


            "description": "Stable dividend-paying stocks",


            "balance": 95125.45,


            "return": 3.82,


            "positions": 7


        }


    ]


    


    # Display portfolio cards


    for i, portfolio in enumerate(portfolios):


        with st.container():


            col1, col2, col3 = st.columns([3, 1, 1])


            


            with col1:


                st.subheader(portfolio["name"])


                st.write(portfolio["description"])


                


            with col2:


                st.metric("Balance", f"${portfolio['balance']:,.2f}")


                st.metric("Return", f"{portfolio['return']}%")


                


            with col3:


                st.metric("Positions", portfolio["positions"])


                st.button("View Details", key=f"view_{i}")


                


            st.markdown("---")





def analysis_page():


    """Analysis page"""


    st.title("Market Analysis")


    


    # Symbol input and timeframe selection


    col1, col2, col3 = st.columns([2, 1, 1])


    


    with col1:


        symbol = st.text_input("Symbol", value="SPY")


        


    with col2:


        timeframe = st.selectbox("Timeframe", ["Daily", "Weekly", "Monthly"])


        


    with col3:


        with_prediction = st.checkbox("Include Prediction")


        analyze_button = st.button("Analyze")


        


    if analyze_button or "last_analysis" in st.session_state:


        # Display analysis


        if "last_analysis" not in st.session_state:


            st.session_state["last_analysis"] = {


                "symbol": symbol,


                "timeframe": timeframe,


                "with_prediction": with_prediction


            }


            


        # Chart


        with st.container():


            # Sample data for demonstration


            dates = pd.date_range(start="2023-01-01", end="2023-07-01", freq="D")


            values = np.random.normal(loc=1.0, scale=0.01, size=len(dates)).cumsum() + 100


            


            # Create DataFrame


            df = pd.DataFrame({


                "date": dates,


                "price": values


            })


            


            # Add prediction if requested


            if with_prediction:


                future_dates = pd.date_range(start="2023-07-02", end="2023-07-15", freq="D")


                future_values = np.random.normal(loc=1.001, scale=0.005, size=len(future_dates)).cumsum() + values[-1]


                


            # Create and display the chart


            fig = go.Figure()


            


            fig.add_trace(go.Scatter(


                x=df["date"],


                y=df["price"],


                mode="lines",


                name=symbol,


                line=dict(color="#1E88E5", width=2)


            ))


            


            if with_prediction:


                fig.add_trace(go.Scatter(


                    x=future_dates,


                    y=future_values,


                    mode="lines",


                    name="Prediction",


                    line=dict(color="#FF5722", width=2, dash="dash")


                ))


                


            fig.update_layout(


                height=400,


                margin=dict(l=0, r=0, t=0, b=0),


                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),


                xaxis=dict(


                    showgrid=False,


                    zeroline=False


                ),


                yaxis=dict(


                    showgrid=True,


                    gridcolor="rgba(0,0,0,0.1)"


                ),


                plot_bgcolor="rgba(0,0,0,0)",


                paper_bgcolor="rgba(0,0,0,0)"


            )


            


            st.plotly_chart(fig, use_container_width=True)


            


        # AI Analysis


        with st.container():


            st.subheader("AI Analysis")


            


            # Generate sample data for analysis


            current_price = values[-1]


            change_24h = np.random.normal(0.5, 0.2)


            volume = np.random.randint(1000000, 10000000)


            market_cap = volume * current_price


            rsi = np.random.normal(55, 5)


            macd = np.random.normal(0.2, 0.1)


            ma_50 = np.mean(values[-50:])


            volatility = np.random.normal(1.5, 0.3)


            risk_level = "Medium" if volatility < 1.8 else "High"


            support = current_price * 0.95


            resistance = current_price * 1.05


            price_range = [current_price * 0.98, current_price * 1.02]


            upside_prob = np.random.randint(40, 80)


            


            # 先生成预测文本，避免 f-string 表达式里有反斜杠


            prediction_text = ""


            if with_prediction:


                prediction_text = (


                    f"### Price Prediction:\n"


                    f"- Expected range for next week: ${price_range[0]:.2f} - ${price_range[1]:.2f}\n"


                    f"- Probability of upside move: {upside_prob}%"


                )


            


            # Placeholder for AI analysis


            analysis = f"""
            ### Market Analysis
            - Current Price: ${current_price:.2f}
            - 24h Change: {change_24h:+.2f}%
            - Volume: {volume:,.0f}
            - Market Cap: ${market_cap:,.0f}
            
            ### Technical Indicators:
            - RSI: {rsi:.2f}
            - MACD: {macd:.2f}
            - Moving Average (50d): ${ma_50:.2f}
            
            ### Risk Analysis:
            - Volatility: {volatility:.2f}%
            - Risk Level: {risk_level}
            - Support: ${support:.2f}
            - Resistance: ${resistance:.2f}
            
            {prediction_text}
            """


            


            st.markdown(analysis)





def reports_page():


    """Reports page"""


    st.title("Reports")


    


    # Report type filter


    report_type = st.selectbox("Report Type", ["All", "Daily", "Weekly", "Performance"])


    


    # Reports list


    reports = [


        {


            "id": "report_123456",


            "type": "daily",


            "title": "Daily Market Report",


            "date": "2023-07-01",


            "has_audio": True


        },


        {


            "id": "report_234567",


            "type": "weekly",


            "title": "Weekly Market Review",


            "date": "2023-06-30",


            "has_audio": True


        },


        {


            "id": "report_345678",


            "type": "performance",


            "title": "Strategy Performance Report",


            "date": "2023-06-30",


            "has_audio": False


        }


    ]


    


    # Filter reports


    if report_type != "All":


        reports = [r for r in reports if r["type"].lower() == report_type.lower()]


        


    # Display reports


    for i, report in enumerate(reports):


        with st.container():


            col1, col2 = st.columns([3, 1])


            


            with col1:


                st.subheader(report["title"])


                st.caption(f"Date: {report['date']}")


                st.caption(f"Type: {report['type'].capitalize()}")


                


            with col2:


                st.button("View Report", key=f"view_report_{i}")


                if report["has_audio"]:


                    st.button("Play Audio", key=f"play_audio_{i}")


                    


            st.markdown("---")





def settings_page():


    """Settings page"""


    st.title("Settings")


    


    # User profile


    with st.container():


        st.subheader("User Profile")


        


        col1, col2 = st.columns(2)


        


        with col1:


            username = st.text_input("Username", value=st.session_state["user"]["username"])


            email = st.text_input("Email", value=st.session_state["user"]["email"])


            


        with col2:


            level = st.text_input("Subscription Level", value=st.session_state["user"]["level"].capitalize(), disabled=True)


            joined_date = st.text_input("Joined Date", value="June 15, 2023", disabled=True)


            


        st.button("Update Profile")


        


    # Subscription


    with st.container():


        st.subheader("Subscription")


        


        if st.session_state["user"]["level"] == "free":


            st.info("You are currently on the Free plan. Upgrade to access more features!")


            


            col1, col2, col3 = st.columns(3)


            


            with col1:


                st.markdown("### Trader")


                st.markdown("- 5 strategy subscriptions")


                st.markdown("- Portfolio tracking")


                st.markdown("- Basic alerts")


                st.markdown("#### $19.99/month")


                st.button("Upgrade to Trader", key="upgrade_trader")


                


            with col2:


                st.markdown("### Pro Trader")


                st.markdown("- 10 strategy subscriptions")


                st.markdown("- Portfolio tracking")


                st.markdown("- Advanced alerts")


                st.markdown("- AI backtests")


                st.markdown("#### $39.99/month")


                st.button("Upgrade to Pro", key="upgrade_pro")


                


            with col3:


                st.markdown("### VIP Trader")


                st.markdown("- Unlimited strategies")


                st.markdown("- Portfolio tracking")


                st.markdown("- Advanced alerts")


                st.markdown("- AI backtests")


                st.markdown("- Custom strategies")


                st.markdown("- Voice reports")


                st.markdown("#### $99.99/month")


                st.button("Upgrade to VIP", key="upgrade_vip")


        else:


            st.success(f"You are currently on the {st.session_state['user']['level'].capitalize()} plan.")


            


            # Show subscription details


            col1, col2 = st.columns(2)


            


            with col1:


                st.metric("Billing Cycle", "Monthly")


                st.metric("Next Billing Date", "July 15, 2023")


                


            with col2:


                if st.session_state["user"]["level"] == "trader":


                    st.metric("Monthly Cost", "$19.99")


                elif st.session_state["user"]["level"] == "pro_trader":


                    st.metric("Monthly Cost", "$39.99")


                elif st.session_state["user"]["level"] == "vip":


                    st.metric("Monthly Cost", "$99.99")


                    


                st.button("Manage Subscription")


                


    # Application settings


    with st.container():


        st.subheader("Application Settings")


        


        col1, col2 = st.columns(2)


        


        with col1:


            st.selectbox("Theme", ["Light", "Dark", "System"])


            st.selectbox("Default Timeframe", ["Daily", "Weekly", "Monthly"])


            


        with col2:


            st.checkbox("Auto-refresh Dashboard", value=True)


            st.checkbox("Enable Notifications", value=True)


            


        st.button("Save Settings")


        


    # Logout button


    st.button("Logout", on_click=lambda: st.session_state.clear())





def main():


    """Main Streamlit application"""


    # Set page config


    st.set_page_config(


        page_title="WarMachine Trading Platform",


        page_icon="ðŸ“ˆ",


        layout="wide",


        initial_sidebar_state="expanded"


    )


    


    # Initialize session state


    if "user" not in st.session_state:


        st.session_state["user"] = {


            "username": "Guest",


            "level": "free"


        }


        


    # Sidebar navigation


    with st.sidebar:


        selected = option_menu(


            "WarMachine",


            ["Dashboard", "Strategies", "Portfolios", "Analysis", "Reports", "Settings"],


            icons=["house", "gear", "briefcase", "graph-up", "file-text", "gear"],


            menu_icon="cast",


            default_index=0


        )


        


        # Display user info


        st.markdown("---")


        st.markdown(f"**User:** {st.session_state['user']['username']}")


        st.markdown(f"**Plan:** {st.session_state['user']['level'].capitalize()}")


        


    # Display selected page


    if selected == "Dashboard":


        dashboard_page()


    elif selected == "Strategies":


        strategies_page()


    elif selected == "Portfolios":


        portfolios_page()


    elif selected == "Analysis":


        analysis_page()


    elif selected == "Reports":


        reports_page()


    elif selected == "Settings":


        settings_page()





if __name__ == "__main__":


    main() 