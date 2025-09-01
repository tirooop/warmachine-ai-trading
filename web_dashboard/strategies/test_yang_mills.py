"""
测试杨-米尔斯策略模块
"""

import unittest
import asyncio
from datetime import datetime
from yang_mills_strategy import OrderBookSnapshot, YangMillsStrategy

class TestYangMillsStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = YangMillsStrategy()
        self.test_order_book = OrderBookSnapshot(
            timestamp=datetime.now(),
            bids=[(100.0, 1000), (99.9, 2000)],
            asks=[(100.1, 1000), (100.2, 2000)],
            last_price=100.0,
            volume=5000
        )
        self.test_position = {
            "AAPL": 100.0,
            "GOOGL": 50.0,
            "META": 75.0,
            "AMZN": 25.0,
            "NFLX": 30.0
        }

    async def test_strategy_execution(self):
        """测试策略执行"""
        signals = []
        async for signal in self.strategy.run_strategy(
            self.test_position, self.test_order_book
        ):
            signals.append(signal)
            if len(signals) >= 2:  # 只测试前两个信号
                break
        
        self.assertEqual(len(signals), 2)
        self.assertIn(signals[0]["type"], ["trade_signal", "risk_control"])
        self.assertIn(signals[1]["type"], ["trade_signal", "risk_control"])

    def test_anomaly_detection(self):
        """测试反常流检测"""
        test_currents = [1.0, 1.1, 1.2, 5.0, 1.3, 1.4]  # 包含一个异常值
        anomalies = self.strategy.detect_anomaly(test_currents)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0], 3)  # 异常值在索引3处

    def test_gauge_field(self):
        """测试规范场变换"""
        initial_position = self.test_position.copy()
        transformed_position = self.strategy.gauge_field.gauge_transform(initial_position)
        
        # 验证变换后的仓位
        self.assertEqual(len(transformed_position), len(initial_position))
        for ticker in initial_position:
            self.assertIn(ticker, transformed_position)
            self.assertIsInstance(transformed_position[ticker], float)

def run_tests():
    """运行所有测试"""
    unittest.main()

if __name__ == "__main__":
    run_tests() 