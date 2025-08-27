"""
运行策略进化系统测试的脚本
"""

import pytest
import sys
import os

def main():
    """运行测试的主函数"""
    # 添加项目根目录到Python路径
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # 运行测试
    pytest.main([
        'tests/test_strategy_evolution.py',
        '-v',  # 详细输出
        '--asyncio-mode=auto',  # 自动处理异步测试
        '--cov=core.strategy',  # 生成覆盖率报告
        '--cov-report=term-missing',  # 显示未覆盖的代码行
        '--cov-report=html:coverage_report'  # 生成HTML格式的覆盖率报告
    ])

if __name__ == '__main__':
    main() 