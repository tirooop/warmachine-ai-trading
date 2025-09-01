"""
File reorganization script for WarMachine system
This script will reorganize the file structure according to the new architecture
"""

import os
import shutil
import json
from pathlib import Path

def create_directory_structure():
    """Create the new directory structure"""
    directories = [
        'core',
        'datafeeds',
        'strategies',
        'ai',
        'config',
        'reports',
        'setup',
        'connectors',
        'notifiers',
        'monitoring',
        'web',
        'community',
        'visualization',
        'trading',
        'scripts',
        'utils',
        'docs',
        'templates',
        'static',
        'examples',
        'tests',
        'logs',
        'cache',
        'data/market/order_flow',
        'data/market/historical',
        'data/market/realtime',
        'data/strategies/backtest',
        'data/strategies/live',
        'data/ai/models',
        'data/ai/training',
        'scripts/legacy',  # For old version scripts
        'scripts/new',     # For new version scripts
        'utils/patches',   # For compatibility patches
        'utils/fixes',     # For system fixes
        'docs/api',        # For API documentation
        'docs/guides',     # For user guides
        'docs/examples',   # For example documentation
        'tests/unit',      # For unit tests
        'tests/integration', # For integration tests
        'tests/performance'  # For performance tests
    ]
    
    for directory in directories:
        os.makedirs(f'warmachine/{directory}', exist_ok=True)
        # Create __init__.py in each directory
        with open(f'warmachine/{directory}/__init__.py', 'w') as f:
            f.write('"""WarMachine {} module"""\n'.format(directory))

def move_files():
    """Move files to their new locations"""
    file_mappings = {
        # Core components
        'run_warmachine.py': 'core/',
        'hf_executor.py': 'core/',
        'run_realtime_monitor.py': 'core/',
        'run_ai_trading_system.py': 'core/',
        'main.py': 'core/',
        
        # Market data components
        'market_data_hub.py': 'datafeeds/',
        'google_finance_data.py': 'datafeeds/',
        'ibkr_historical_data.py': 'datafeeds/',
        'real_market_connector.py': 'datafeeds/',
        'test_market_data_connection.py': 'datafeeds/tests/',
        'test_realtime_data.py': 'datafeeds/tests/',
        'googlefinance-master.zip': 'datafeeds/',
        
        # Strategy components
        'enhanced_liquidity_sniper.py': 'strategies/',
        'order_flow_monitor.py': 'strategies/',
        'liquidity_sniper.py': 'strategies/deprecated/',
        'strategy_prompt_engine.py': 'strategies/',
        'option_backtester.py': 'strategies/',
        'starG.py': 'strategies/',
        'test_strategy_prompt.py': 'strategies/tests/',
        'backtest_strategy.py': 'strategies/tests/',
        
        # AI components
        'ai_analyzer.py': 'ai/',
        'ai_commander.py': 'ai/',
        'ai_model_router.py': 'ai/',
        'ai_reporter.py': 'ai/',
        'ai_self_improvement.py': 'ai/',
        'ai_alert_factory.py': 'ai/',
        'ai_event_pool.py': 'ai/',
        'ai_intelligence_dispatcher.py': 'ai/',
        'ai_analyst_v2.py': 'ai/',
        'ai_market_analyzer.py': 'ai/',
        'deepseek_agent.py': 'ai/',
        'llm_prompt_builder.py': 'ai/',
        
        # Notification components
        'unified_notifier.py': 'notifiers/',
        'telegram_bot.py': 'notifiers/',
        'voice_manager.py': 'notifiers/',
        'test_telegram_unified.py': 'notifiers/tests/',
        'test_telegram_simple.py': 'notifiers/tests/',
        'test_telegram_setup.py': 'notifiers/tests/',
        'test_telegram.py': 'notifiers/tests/',
        'test_strategy_telegram.py': 'notifiers/tests/',
        
        # Web components
        'web_dashboard.py': 'web/',
        'web_api.py': 'web/',
        'webhook_server.py': 'web/',
        'simple_dashboard.py': 'web/',
        
        # Monitoring components
        'market_watcher.py': 'monitoring/',
        'routine_scheduler.py': 'monitoring/',
        
        # Community components
        'community_manager.py': 'community/',
        
        # Utility components
        'analyze_market_data.py': 'utils/',
        'verify_environment.py': 'utils/',
        'fix_imghdr_and_encoding.py': 'utils/fixes/',
        'preload_compatibility.py': 'utils/patches/',
        'fix_numpy_error.ps1': 'utils/fixes/',
        'fix_telegram_discord_bots.py': 'utils/fixes/',
        'imghdr_patch.py': 'utils/patches/',
        'imghdr_patch_direct.py': 'utils/patches/',
        'fix_imghdr_windows.py': 'utils/patches/',
        'fix_imghdr_pillow_global.py': 'utils/patches/',
        'auto_fix_imghdr.py': 'utils/patches/',
        'standalone_imghdr_fix.py': 'utils/patches/',
        'simple_fix.py': 'utils/fixes/',
        
        # Configuration files
        'warmachine_config.json': 'config/',
        'module_status.json': 'config/',
        'requirements.txt': 'config/',
        
        # Documentation
        'README.md': 'docs/',
        'SYSTEM_OVERVIEW.md': 'docs/',
        'DATA_SHARING_TABLE.md': 'docs/',
        'PROJECT_ORGANIZATION.md': 'docs/',
        'REALTIME_TEST_README.md': 'docs/',
        'README_AI_INTEGRATION.md': 'docs/',
        'COMPATIBILITY_FIXES.md': 'docs/',
        'IMGHDR_PATCH_README.txt': 'docs/',
        'IBKR_HISTORICAL_DATA_README.md': 'docs/',
        
        # Scripts (new versions)
        'new_trading_system_controller.ps1': 'scripts/new/',
        'new_analyze_logs.ps1': 'scripts/new/',
        'new_collect_daily_data.ps1': 'scripts/new/',
        'new_monitor_google_finance.ps1': 'scripts/new/',
        'new_notification.ps1': 'scripts/new/',
        'new_setup_scheduled_tasks.ps1': 'scripts/new/',
        'new_deploy_google_finance.ps1': 'scripts/new/',
        
        # Scripts (legacy versions)
        'send_market_data.ps1': 'scripts/legacy/',
        'test_ai_notification.ps1': 'scripts/legacy/',
        'start_ai_analysis_system.ps1': 'scripts/legacy/',
        'deploy_system.ps1': 'scripts/legacy/',
        'fix_google_finance.ps1': 'scripts/legacy/',
        'start_trading_system.ps1': 'scripts/legacy/',
        'reorganize_system.ps1': 'scripts/legacy/',
        'deploy_google_finance_tools.ps1': 'scripts/legacy/',
        'setup_scheduled_tasks.ps1': 'scripts/legacy/',
        'monitor_google_finance.ps1': 'scripts/legacy/',
        'collect_daily_data.ps1': 'scripts/legacy/',
        'deploy_ibkr_tools.ps1': 'scripts/legacy/',
        'analyze_logs.ps1': 'scripts/legacy/',
        'monitor_ibkr.ps1': 'scripts/legacy/',
        'notification.ps1': 'scripts/legacy/',
        'telegram_notify.ps1': 'scripts/legacy/',
        'run_standalone_ibkr.ps1': 'scripts/legacy/',
        'run_ibkr_historical.ps1': 'scripts/legacy/',
        'start_warmachine_option.sh': 'scripts/legacy/',
        'start_warmachine_option.bat': 'scripts/legacy/',
        'start_realtime_test.ps1': 'scripts/legacy/',
        'setup_ai_trading_system.ps1': 'scripts/legacy/',
        'start_ai_system.ps1': 'scripts/legacy/',
        'setup_warmachine_ai.ps1': 'scripts/legacy/',
        'setup_real_market_data.ps1': 'scripts/legacy/',
        'temp_deploy.ps1': 'scripts/legacy/',
        
        # Example files
        'usage_example.py': 'examples/',
        'example_usage.py': 'examples/',
        
        # Test files
        'test_hf_executor.py': 'tests/unit/',
        'start_test_patched.py': 'tests/unit/',
        
        # Standalone files
        'standalone_google_finance.py': 'datafeeds/standalone/',
        'standalone_ibkr_historical.py': 'datafeeds/standalone/',
        'check_ibkr_connection.py': 'datafeeds/standalone/',
    }
    
    for source, target_dir in file_mappings.items():
        source_path = f'warmachine/{source}'
        target_path = f'warmachine/{target_dir}{source}'
        
        if os.path.exists(source_path):
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.move(source_path, target_path)
            print(f'Moved {source} to {target_dir}')

def update_imports():
    """Update import statements in all Python files"""
    import_updates = {
        'from warmachine.': 'from warmachine.',
        'import warmachine.': 'import warmachine.',
    }
    
    python_files = []
    for root, _, files in os.walk('warmachine'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        for old, new in import_updates.items():
            if old in content:
                content = content.replace(old, new)
                modified = True
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Updated imports in {file_path}')

def main():
    """Main function to run the reorganization"""
    print("Starting WarMachine system reorganization...")
    
    # Create new directory structure
    create_directory_structure()
    print("Created directory structure")
    
    # Move files to new locations
    move_files()
    print("Moved files to new locations")
    
    # Update import statements
    update_imports()
    print("Updated import statements")
    
    print("WarMachine system reorganization complete!")

if __name__ == '__main__':
    main() 