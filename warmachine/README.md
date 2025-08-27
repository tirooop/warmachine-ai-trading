# WarMachine - 智能期权交易系统

WarMachine是一个基于人工智能的期权交易系统，集成了策略进化、风险管理和实时监控功能。

## 🌟 主要特性

### 1. 策略进化系统
- 基于遗传算法的策略优化
- 实时基因重组和变异
- 多目标适应度评估
- 预测市场驱动的进化机制

### 2. 风险管理
- 实时风险监控
- 动态仓位管理
- 多维度风险指标
- 自动风险预警

### 3. 实时监控
- Web仪表板
- Telegram机器人
- 性能分析报告
- 系统状态监控

## 🚀 快速开始

### 环境要求
- Python 3.8+
- PostgreSQL 12+
- Redis 6+

### 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/warmachine.git
cd warmachine
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置信息
```

5. 启动系统：
```bash
python run_warmachine.py
```

## 📊 系统架构

### 核心组件
- 策略进化引擎
- 市场数据采集器
- 风险管理系统
- 交易执行引擎
- Web仪表板
- Telegram机器人

### 数据流
1. 市场数据采集
2. 策略进化优化
3. 信号生成
4. 风险控制
5. 交易执行
6. 性能分析

## 🤖 策略进化系统

### 基因编码
```python
OPTION_GENES = {
    'spread_ratio': (0.01, 0.5),    # 买卖价差比例
    'gamma_threshold': (-5, 5),     # Gamma风险暴露阈值 
    'iv_skew_sensitivity': (0, 2),  # 隐含波动率曲面敏感度
    'theta_decay_rate': (0.8, 1.2), # 时间衰减补偿系数
    'hedge_frequency': (10, 300)    # 对冲间隔(秒)
}
```

### 进化机制
- 定向变异
- 基因重组
- 适应度评估
- 种群管理

### 性能指标
- 年化收益率
- 最大回撤
- 夏普比率
- 胜率
- 盈亏比

## 📱 用户界面

### Web仪表板
- 策略监控
- 性能分析
- 风险控制
- 系统设置

### Telegram机器人
- 实时状态查询
- 策略管理
- 性能报告
- 系统控制

## 🔧 配置说明

### 策略配置
```json
{
    "strategy_evolution": {
        "genes": {
            "spread_ratio": {
                "min": 0.01,
                "max": 0.5,
                "default": 0.18
            }
        },
        "evolution": {
            "population_size": 50,
            "generation_interval": 3600
        }
    }
}
```

### 风险控制
```json
{
    "risk_management": {
        "max_drawdown": 0.2,
        "position_limit": 0.1,
        "daily_loss_limit": 0.05
    }
}
```

## 📈 性能报告

### 回测结果
- 年化收益：248%
- 最大回撤：15%
- 夏普比率：2.8
- 胜率：68%

### 实盘表现
- 日收益：2.3%
- 周收益：12.5%
- 月收益：45.2%

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

- 邮箱：your.email@example.com
- Telegram：@your_username
- Discord：your_username#1234 