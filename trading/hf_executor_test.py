#!/usr/bin/env python
"""
Test script for the high-frequency execution module
Tests performance and reliability of the microsecond-level order execution
"""

import asyncio
import time
import random
import logging
import sys
from hf_executor import HighFrequencyExecutor, OrderPriority

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

async def test_hf_performance():
    """Test high-frequency executor performance"""
    # Configuration for test
    config = {
        "hf_execution": {
            "enabled": True,
            "uvloop": True,
            "batch_size": 5,
            "timeout_ms": 10,
            "max_concurrent_orders": 50,
        }
    }
    
    # Create executor
    executor = HighFrequencyExecutor(config)
    await executor.start()
    
    # Prepare test orders
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
    sides = ["BUY", "SELL"]
    types = ["MARKET", "LIMIT"]
    
    test_orders = []
    for i in range(1000):  # 1000 test orders
        test_orders.append({
            "exchange": "binance",
            "symbol": random.choice(symbols),
            "side": random.choice(sides),
            "type": random.choice(types),
            "quantity": round(random.uniform(0.01, 1.0), 3),
            "price": round(random.uniform(10000, 60000), 2) if random.choice(types) == "LIMIT" else None
        })
    
    # Execute test
    print(f"Submitting {len(test_orders)} orders for performance testing...")
    start_time = time.time()
    
    # Batch submit orders
    order_ids = []
    for order in test_orders:
        # Randomly assign priority
        priority = random.choice([
            OrderPriority.HIGH, 
            OrderPriority.MEDIUM, 
            OrderPriority.MEDIUM, 
            OrderPriority.LOW
        ])
        order_id = await executor.submit_order(order, priority)
        order_ids.append(order_id)
    
    # Wait for all orders to be processed
    while executor.order_queue.qsize() > 0 or len(executor.active_orders) > 0:
        await asyncio.sleep(0.1)
        print(f"In queue: {executor.order_queue.qsize()}, Active orders: {len(executor.active_orders)}", end="\r")
    
    # Calculate performance metrics
    end_time = time.time()
    elapsed = end_time - start_time
    orders_per_sec = len(test_orders) / elapsed
    
    print(f"\nTest complete: {len(test_orders)} orders processed in {elapsed:.3f} seconds")
    print(f"Throughput: {orders_per_sec:.2f} orders/second")
    
    # Get detailed metrics
    metrics = executor.get_metrics()
    print(f"Latency metrics (microseconds):")
    print(f"  Min: {metrics.get('min_latency_us', 0):.2f} µs")
    print(f"  Avg: {metrics.get('avg_latency_us', 0):.2f} µs")
    print(f"  P50: {metrics.get('p50_latency_us', 0):.2f} µs")
    print(f"  P95: {metrics.get('p95_latency_us', 0):.2f} µs")
    print(f"  P99: {metrics.get('p99_latency_us', 0):.2f} µs")
    print(f"  Max: {metrics.get('max_latency_us', 0):.2f} µs")
    
    # Stop executor
    await executor.stop()

async def test_hf_reliability():
    """Test executor reliability under various conditions"""
    # Configuration for test
    config = {
        "hf_execution": {
            "enabled": True,
            "uvloop": True,
            "batch_size": 5,
            "timeout_ms": 10,
            "max_concurrent_orders": 50,
        }
    }
    
    # Create executor
    executor = HighFrequencyExecutor(config)
    await executor.start()
    
    # Test 1: Reliability with mixed order types
    print("\nTest 1: Reliability with mixed order types")
    test_mixed_orders = []
    
    # Create a mix of order types with various exchanges
    exchanges = ["binance", "okx", "bybit"]
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
    sides = ["BUY", "SELL"]
    types = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
    
    for i in range(100):
        test_mixed_orders.append({
            "exchange": random.choice(exchanges),
            "symbol": random.choice(symbols),
            "side": random.choice(sides),
            "type": random.choice(types),
            "quantity": round(random.uniform(0.01, 1.0), 3),
            "price": round(random.uniform(10000, 60000), 2) if "LIMIT" in random.choice(types) else None
        })
    
    # Submit mixed orders
    for order in test_mixed_orders:
        order_id = await executor.submit_order(order)
    
    # Wait for processing to complete
    await asyncio.sleep(3)
    
    # Check results
    success_count = 0
    error_count = 0
    rejected_count = 0
    
    for order_id, order in executor.order_history.items():
        if order["status"] == "SUBMITTED":
            success_count += 1
        elif order["status"] == "ERROR":
            error_count += 1
        elif order["status"] == "REJECTED":
            rejected_count += 1
    
    print(f"Mixed orders results:")
    print(f"  Success: {success_count}")
    print(f"  Rejected: {rejected_count}")
    print(f"  Errors: {error_count}")
    
    # Test 2: Cancel order functionality
    print("\nTest 2: Order cancellation")
    
    # Create and submit a cancellable order
    cancel_order = {
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": 0.1,
        "price": 40000
    }
    
    order_id = await executor.submit_order(cancel_order, OrderPriority.LOW)
    print(f"Submitted order {order_id} for cancellation test")
    
    # Wait a moment before cancelling
    await asyncio.sleep(0.5)
    
    # Cancel the order
    cancelled = await executor.cancel_order(order_id)
    print(f"Order cancellation result: {cancelled}")
    
    # Stop executor
    await executor.stop()

# Main function to run both tests
async def run_all_tests():
    print("=== HIGH FREQUENCY EXECUTOR TESTS ===")
    print("\n1. PERFORMANCE TEST")
    await test_hf_performance()
    
    print("\n2. RELIABILITY TEST")
    await test_hf_reliability()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 