"""
Move all modules to warmachine directory
"""

import os
import shutil
from pathlib import Path

def move_module(src_dir: str, dest_dir: str):
    """Move a module directory to the warmachine directory"""
    src_path = Path(src_dir)
    dest_path = Path(dest_dir) / src_dir
    
    if src_path.exists():
        print(f"Moving {src_dir} to {dest_path}")
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.move(src_path, dest_path)

def main():
    """Main function to move all modules"""
    modules = [
        'tg_bot',
        'core',
        'utils',
        'notifiers',
        'connectors',
        'trading',
        'web_dashboard',
        'visualization',
        'monitoring',
        'analysis',
        'datafeeds',
        'community'
    ]
    
    for module in modules:
        move_module(module, 'warmachine')

if __name__ == '__main__':
    main() 