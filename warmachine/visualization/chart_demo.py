"""
Standalone Chart Demo - Generates technical analysis charts with AI commentary
"""

import os
import sys
import argparse
from PIL import Image  # Using Pillow instead of imghdr

# Add the current directory to path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate technical analysis charts with AI commentary")
    parser.add_argument("symbols", nargs="+", help="Stock ticker symbols to analyze")
    parser.add_argument("--days", type=int, default=30, help="Number of days to include in the chart")
    parser.add_argument("--output-dir", default="./temp_charts", help="Directory to save charts")
    args = parser.parse_args()
    
    # Ensure output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Import modules here to avoid import errors from __init__.py
    from utils.chart_renderer import ChartRenderer
    from utils.technical_indicator_lib import TechnicalIndicatorLib
    from utils.market_data_provider import MarketDataProvider

    # Create a simple version of AIChartAnalyzer to avoid dependencies
    class SimpleAnalyzer:
        def analyze(self, symbol, days=30):
            return f"Technical analysis for {symbol} (Simple version without AI)"
    
    # Initialize components
    chart_renderer = ChartRenderer()
    analyzer = SimpleAnalyzer()
    
    # Process each symbol
    for symbol in args.symbols:
        try:
            print(f"Generating chart for {symbol}...")
            
            # Generate chart
            chart_path = chart_renderer.render(symbol, days=args.days)
            print(f"Chart saved to: {chart_path}")
            
            # Verify image was created successfully using PIL
            try:
                with Image.open(chart_path) as img:
                    width, height = img.size
                    print(f"Image dimensions: {width}x{height}")
            except Exception as e:
                print(f"Error validating image: {str(e)}")
            
            # Get simple analysis
            analysis = analyzer.analyze(symbol, days=args.days)
            
            # Print analysis
            print("\n" + "="*50)
            print(f"ðŸ“Š {symbol} Technical Analysis")
            print("="*50)
            print(analysis)
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 