#!/usr/bin/env python
"""
WarMachine AI Option Trader - 带兼容性预加载的启动脚本

首先加载兼容性模块，然后启动主系统。
"""
import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/launch.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("启动带兼容性的WarMachine AI Option Trader")

    # 步骤1：加载兼容性预处理
    logger.info("加载兼容性模块...")
    try:
        import preload_compatibility
        logger.info("兼容性模块加载成功")
    except Exception as e:
        logger.error(f"加载兼容性模块失败: {e}")
        return False

    # 步骤2：安装imghdr模块（如果需要）
    try:
        import imghdr
        logger.info(f"imghdr可用状态: {hasattr(imghdr, 'what')}")
    except Exception as e:
        logger.error(f"imghdr模块不可用: {e}")
        return False

    # 步骤3：启动主系统
    logger.info("开始启动主系统...")
    try:
        from run_warmachine import main as run_main
        run_main()
        return True
    except ImportError:
        logger.error("未找到run_warmachine.py，尝试直接导入WarMachine...")
        try:
            from run_warmachine import WarMachine
            machine = WarMachine()
            machine.start()
            return True
        except Exception as e:
            logger.error(f"启动主系统失败: {e}")
            return False

if __name__ == "__main__":
    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)
    
    # 运行主函数
    success = main()
    
    if success:
        logger.info("WarMachine启动成功！")
    else:
        logger.error("WarMachine启动失败，请检查日志获取详细信息")
        print("\n❌ 启动失败！请检查logs/launch.log获取详细信息。")
        sys.exit(1) 