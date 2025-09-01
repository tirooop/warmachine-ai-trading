#!/usr/bin/env python
"""
将DeepSeek API工具集成到Docker项目中的部署脚本
"""
import os
import sys
import shutil
import argparse
from datetime import datetime

def create_directory_if_not_exists(directory):
    """创建目录（如果不存在）"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录: {directory}")

def deploy_deepseek_api():
    """部署DeepSeek API工具到Docker项目中"""
    print("\n" + "=" * 50)
    print("DeepSeek API工具集成部署")
    print("=" * 50)
    
    # 确保utils目录存在
    utils_dir = os.path.join(os.getcwd(), "utils")
    create_directory_if_not_exists(utils_dir)
    
    # 部署deepseek_api.py
    deepseek_api_path = os.path.join(utils_dir, "deepseek_api.py")
    if os.path.exists(deepseek_api_path):
        backup_file(deepseek_api_path)
    
    # 复制文件
    try:
        shutil.copy("utils/deepseek_api.py", deepseek_api_path)
        print(f"已部署 deepseek_api.py 到 {deepseek_api_path}")
    except FileNotFoundError:
        print("错误: utils/deepseek_api.py 文件未找到")
        return False
    
    # 部署ai_market_analyzer.py
    analyzer_path = os.path.join(utils_dir, "ai_market_analyzer.py")
    if os.path.exists(analyzer_path):
        backup_file(analyzer_path)
        
    try:
        shutil.copy("utils/ai_market_analyzer.py", analyzer_path)
        print(f"已部署 ai_market_analyzer.py 到 {analyzer_path}")
    except FileNotFoundError:
        print("错误: utils/ai_market_analyzer.py 文件未找到")
    
    # 部署ai_smart_strategy.py
    strategy_path = os.path.join(utils_dir, "ai_smart_strategy.py")
    if os.path.exists(strategy_path):
        backup_file(strategy_path)
        
    try:
        shutil.copy("utils/ai_smart_strategy.py", strategy_path)
        print(f"已部署 ai_smart_strategy.py 到 {strategy_path}")
    except FileNotFoundError:
        print("错误: utils/ai_smart_strategy.py 文件未找到")
    
    # 部署测试脚本
    test_path = os.path.join(os.getcwd(), "test_deepseek_api.py")
    if os.path.exists(test_path):
        backup_file(test_path)
        
    try:
        shutil.copy("test_deepseek_api.py", test_path)
        print(f"已部署 test_deepseek_api.py 到 {test_path}")
    except FileNotFoundError:
        print("错误: test_deepseek_api.py 文件未找到")
    
    # 创建简单测试脚本
    simple_test_path = os.path.join(os.getcwd(), "simple_deepseek_test.py")
    if os.path.exists(simple_test_path):
        backup_file(simple_test_path)
        
    try:
        shutil.copy("simple_deepseek_test.py", simple_test_path)
        print(f"已部署 simple_deepseek_test.py 到 {simple_test_path}")
    except FileNotFoundError:
        print("错误: simple_deepseek_test.py 文件未找到")
    
    # 更新Docker环境
    update_docker_environment()
    
    print("\n部署完成！DeepSeek API工具已成功集成到项目中。")
    print("\n使用方法:")
    print("1. 重新构建并启动Docker容器: docker-compose up -d --build")
    print("2. 测试DeepSeek API: python simple_deepseek_test.py")
    print("3. 在代码中导入API工具: from utils.deepseek_api import get_deepseek_response")
    
    return True

def backup_file(file_path):
    """备份文件"""
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.bak_{timestamp}"
        shutil.copy(file_path, backup_path)
        print(f"已备份 {file_path} 到 {backup_path}")

def update_docker_environment():
    """更新Docker环境文件"""
    docker_compose_path = os.path.join(os.getcwd(), "docker-compose.yml")
    
    if not os.path.exists(docker_compose_path):
        print("警告: docker-compose.yml 文件未找到，无法更新Docker环境")
        return
    
    # 检查docker-compose.yml中是否已包含DeepSeek API密钥
    with open(docker_compose_path, "r") as f:
        content = f.read()
    
    if "DEEPSEEK_API_KEY" in content:
        print("Docker环境中已包含DeepSeek API配置")
    else:
        print("需要在docker-compose.yml中添加DeepSeek API配置")
        print("请手动添加以下环境变量到docker-compose.yml的environment部分:")
        print("      - DEEPSEEK_API_KEY=your_api_key_here")

def main():
    parser = argparse.ArgumentParser(description='DeepSeek API工具集成部署脚本')
    parser.add_argument('--force', action='store_true', help='强制部署，覆盖现有文件')
    
    args = parser.parse_args()
    
    if args.force:
        print("警告: 强制部署模式，将覆盖现有文件")
    
    deploy_deepseek_api()

if __name__ == "__main__":
    main() 