#!/usr/bin/env python


"""


创建AI量化社区平台所需的目录结构


"""





import os


import logging


from pathlib import Path





# 配置日志


logging.basicConfig(


    level=logging.INFO,


    format='%(asctime)s - %(levelname)s - %(message)s'


)


logger = logging.getLogger(__name__)





# 主要目录结构


DIRECTORIES = [


    # 配置目录


    "config",


    


    # 模块目录


    "ai_engine",              # AI核心模块


    "utils/visualization",          # 图表与播报模块


    "utils/community",              # 用户与组合模块


    "utils/monitoring",             # 事件与监控模块


    "api",                          # API模块


    


    # 数据目录


    "data/market",                  # 市场数据


    "data/users",                   # 用户数据


    "data/portfolios",              # 组合数据


    "data/strategies",              # 策略数据


    "data/ai_research",             # AI研究报告


    


    # 静态文件目录


    "static/charts",                # 图表静态文件


    "static/audio",                 # 音频静态文件


    


    # 策略目录


    "strategies",                   # 策略根目录


    "strategies/generated",         # 生成的策略


    "strategies/optimized",         # 优化后的策略


    


    # 日志目录


    "logs",


]





# 必要的初始化文件


INIT_FILES = [


    "utils/__init__.py",


    "ai_engine/__init__.py",


    "utils/visualization/__init__.py",


    "utils/community/__init__.py",


    "utils/monitoring/__init__.py",


    "api/__init__.py"


]





def create_directories():


    """创建目录结构"""


    logger.info("开始创建目录结构...")


    


    for directory in DIRECTORIES:


        path = Path(directory)


        path.mkdir(parents=True, exist_ok=True)


        logger.info(f"目录已创建/确认: {directory}")


        


    logger.info("目录结构创建完成")





def create_init_files():


    """创建必要的初始化文件"""


    logger.info("开始创建初始化文件...")


    


    for file_path in INIT_FILES:


        path = Path(file_path)


        


        if not path.exists():


            # 创建父目录(以防万一)


            path.parent.mkdir(parents=True, exist_ok=True)


            


            # 创建文件


            with open(file_path, "w", encoding="utf-8") as f:


                module_name = path.parent.name if path.name == "__init__.py" else path.parent.name + "." + path.stem


                f.write(f'"""\nAI量化社区平台 - {module_name} 模块\n"""\n')


                


            logger.info(f"初始化文件已创建: {file_path}")


        else:


            logger.info(f"初始化文件已存在: {file_path}")


            


    logger.info("初始化文件创建完成")





def create_readme_files():


    """创建说明文件"""


    logger.info("开始创建说明文件...")


    


    # 策略目录README


    strategies_readme = "strategies/README.md"


    if not os.path.exists(strategies_readme):


        with open(strategies_readme, "w", encoding="utf-8") as f:


            f.write("""# 策略目录





本目录包含系统使用的交易策略:





- `generated/`: 由AI自动生成的策略


- `optimized/`: 经过优化的策略





每个策略文件应包含一个继承自 `Strategy` 基类的策略类。





## 策略文件命名约定





策略文件应使用以下命名约定:


```


[策略类型]_[目标市场]_[主要特点].py


```





例如:


- `mean_reversion_spy_rsi.py`: 基于RSI的SPY均值回归策略


- `momentum_tech_macd.py`: 基于MACD的科技板块动量策略


```


            )


        logger.info(f"说明文件已创建: {strategies_readme}")


        


    # 数据目录README


    data_readme = "data/README.md"


    if not os.path.exists(data_readme):


        with open(data_readme, "w", encoding="utf-8") as f:


            f.write("""# 数据目录





本目录存储系统使用的各类数据:





- `market/`: 市场数据


- `users/`: 用户数据


- `portfolios/`: 组合数据


- `strategies/`: 策略数据


- `ai_research/`: AI研究报告





## 数据存储格式





- 市场数据: CSV文件，包含OHLCV数据


- 用户数据: JSON文件，包含用户信息和偏好设置


- 组合数据: JSON文件，包含组合构成和表现历史


- 策略数据: JSON文件，包含策略元数据和表现指标


- AI研究报告: Markdown文件，包含研究内容和结论


```


            )


        logger.info(f"说明文件已创建: {data_readme}")


        


    logger.info("说明文件创建完成")





def create_gitignore():


    """创建.gitignore文件"""


    logger.info("创建.gitignore文件...")


    


    gitignore_path = ".gitignore"


    if not os.path.exists(gitignore_path):


        with open(gitignore_path, "w", encoding="utf-8") as f:


            f.write("""# Python


__pycache__/


*.py[cod]


*$py.class


*.so


.Python


env/


build/


develop-eggs/


dist/


downloads/


eggs/


.eggs/


lib/


lib64/


parts/


sdist/


var/


wheels/


*.egg-info/


.installed.cfg


*.egg





# 虚拟环境


venv/


ENV/


env/





# 日志和数据


logs/


*.log


data/market/*.csv


data/users/*.json


data/portfolios/*.json


data/strategies/*.json


data/ai_research/*.md





# 静态文件


static/charts/


static/audio/





# 环境变量


.env





# 配置文件


config/*.json





# 编辑器


.idea/


.vscode/


*.swp


*.swo





# 系统


.DS_Store


Thumbs.db


"""


            )


        logger.info(f"已创建: {gitignore_path}")


    else:


        logger.info(f"已存在: {gitignore_path}")





if __name__ == "__main__":


    logger.info("=== 创建AI量化社区平台目录结构 ===")


    


    create_directories()


    create_init_files()


    create_readme_files()


    create_gitignore()


    


    logger.info("=== 目录结构创建完成 ===")


    logger.info("现在您可以运行 'python run_ai_community_platform.py' 来启动平台") 