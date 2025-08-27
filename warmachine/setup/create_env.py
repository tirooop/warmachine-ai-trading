#!/usr/bin/env python3
"""
创建.env配置文件
"""
import os

# 检查.env文件是否已存在
if os.path.exists('.env'):
    overwrite = input('.env文件已存在，是否覆盖? (y/n): ')
    if overwrite.lower() != 'y':
        print('操作已取消')
        exit()

# 创建.env文件
with open('.env', 'w', encoding='utf-8') as f:
    # AI API密钥
    f.write('# AI API密钥 (至少需要一个)\n')
    f.write('DEEPSEEK_API_KEY=your_api_key_here\n')
    f.write('QWEN_API_KEY=your_qwen_api_key_here\n')
    f.write('SILICON_API_KEY=your_silicon_api_key_here\n\n')
    
    # 通知设置
    f.write('# 通知设置\n')
    f.write('# 飞书 (至少需要一个通知渠道)\n')
    f.write('FEISHU_WEBHOOK=your_webhook_here\n')
    f.write('FEISHU_ENABLED=true\n\n')
    
    f.write('# Telegram (可选)\n')
    f.write('TELEGRAM_TOKEN=your_telegram_token\n')
    f.write('TELEGRAM_CHAT_ID=your_chat_id\n')
    f.write('TELEGRAM_ENABLED=false\n\n')
    
    # 信号设置
    f.write('# 信号设置\n')
    f.write('MIN_CONFIDENCE=0.7\n')
    f.write('MIN_PUT_CONFIDENCE=0.8\n')
    f.write('DEFAULT_SYMBOLS=SPY,QQQ,AAPL,MSFT,NVDA,META,TSLA\n\n')
    
    # 市场数据API
    f.write('# 市场数据API (可选)\n')
    f.write('DATABENTO_API_KEY=your_databento_key\n')
    f.write('ALPHAVANTAGE_API_KEY=your_alphavantage_key\n\n')
    
    # 系统设置
    f.write('# 系统设置\n')
    f.write('LOG_LEVEL=INFO\n')
    f.write('TIMEZONE=America/New_York\n')
    f.write('DATA_DIR=data\n')
    f.write('KNOWLEDGE_BASE_DIR=data/knowledge_base\n')

print('成功创建.env文件！请编辑该文件，填入您的API密钥和其他配置。')
print('\n基本使用指南:')
print('1. 安装依赖: pip install -r requirements.txt')
print('2. 启动主调度中心: python main_strategy_hub.py')
print('3. 启动Streamlit仪表盘: streamlit run pages/ai_strategy_summary.py') 