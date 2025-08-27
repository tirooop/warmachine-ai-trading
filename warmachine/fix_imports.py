import os
import sys
import re

def fix_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix imports
    content = content.replace('from ai_model_router import AIModelRouter', 'from ai_engine.ai_model_router import AIModelRouter')
    content = content.replace('from community_manager import CommunityManager', 'from community.community_manager import CommunityManager')
    content = content.replace('from unified_notifier import UnifiedNotifier', 'from notifiers.unified_notifier import UnifiedNotifier')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    # Fix web_api.py
    web_api_path = os.path.join('web_dashboard', 'web_api.py')
    if os.path.exists(web_api_path):
        fix_imports(web_api_path)
        print(f"Fixed imports in {web_api_path}")
    
    # Fix run_warmachine.py
    run_warmachine_path = 'run_warmachine.py'
    if os.path.exists(run_warmachine_path):
        fix_imports(run_warmachine_path)
        print(f"Fixed imports in {run_warmachine_path}")

if __name__ == '__main__':
    main() 