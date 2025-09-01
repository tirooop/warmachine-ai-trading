"""
修复所有导入问题
"""

import os
import re
from pathlib import Path

def fix_imports(file_path: str):
    """修复单个文件的导入语句"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 获取文件相对于 warmachine 目录的路径
    rel_path = os.path.relpath(file_path, 'warmachine')
    depth = len(rel_path.split(os.sep)) - 1
    
    # 构建相对导入前缀
    relative_prefix = '.' * depth if depth > 0 else '.'
    
    # 替换导入语句
    patterns = [
        (r'from core\.', f'from {relative_prefix}core.'),
        (r'import core\.', f'import {relative_prefix}core.'),
        (r'from utils\.', f'from {relative_prefix}utils.'),
        (r'import utils\.', f'import {relative_prefix}utils.'),
        (r'from tg_bot\.', f'from {relative_prefix}tg_bot.'),
        (r'import tg_bot\.', f'import {relative_prefix}tg_bot.'),
        (r'from notifiers\.', f'from {relative_prefix}notifiers.'),
        (r'import notifiers\.', f'import {relative_prefix}notifiers.'),
        (r'from connectors\.', f'from {relative_prefix}connectors.'),
        (r'import connectors\.', f'import {relative_prefix}connectors.'),
        (r'from trading\.', f'from {relative_prefix}trading.'),
        (r'import trading\.', f'import {relative_prefix}trading.'),
        (r'from web_dashboard\.', f'from {relative_prefix}web_dashboard.'),
        (r'import web_dashboard\.', f'import {relative_prefix}web_dashboard.'),
        (r'from visualization\.', f'from {relative_prefix}visualization.'),
        (r'import visualization\.', f'import {relative_prefix}visualization.'),
        (r'from monitoring\.', f'from {relative_prefix}monitoring.'),
        (r'import monitoring\.', f'import {relative_prefix}monitoring.'),
        (r'from analysis\.', f'from {relative_prefix}analysis.'),
        (r'import analysis\.', f'import {relative_prefix}analysis.'),
        (r'from datafeeds\.', f'from {relative_prefix}datafeeds.'),
        (r'import datafeeds\.', f'import {relative_prefix}datafeeds.'),
        (r'from community\.', f'from {relative_prefix}community.'),
        (r'import community\.', f'import {relative_prefix}community.')
    ]
    
    modified = False
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Fixed imports in {file_path}')

def main():
    """主函数"""
    # 遍历 warmachine 目录下的所有 Python 文件
    for root, _, files in os.walk('warmachine'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                fix_imports(file_path)

if __name__ == '__main__':
    main() 