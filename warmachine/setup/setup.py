from setuptools import setup, find_packages

setup(
    name="rl_option_trader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Data Sources
        "polygon-api-client>=1.12.0",
        "alpaca-py>=0.8.0",
        "alpaca-trade-api>=3.0.0",
        
        # Data Processing
        "pandas>=1.5.0",
        "numpy>=1.23.0",
        
        # Technical Analysis
        "pandas-ta>=0.3.14b",
        "scipy>=1.7.0",  # Required for some technical indicators
        
        # Scheduling
        "schedule>=1.1.0",
        
        # Dashboard
        "streamlit>=1.22.0",
        "plotly>=5.13.0",
        
        # Configuration
        "pyyaml>=6.0.0",
        "python-dotenv>=0.19.0",
        
        # Network
        "requests>=2.28.0",
        "websockets>=10.3",
        
        # Testing
        "pytest>=7.3.0",
        "pytest-asyncio>=0.20.0",
        
        # Notifications
        "python-telegram-bot>=13.7"
    ],
    python_requires=">=3.8",
    package_data={
        "rl_option_trader": [
            "config/*.yaml",
            "pages/*.py"
        ]
    },
    include_package_data=True
) 