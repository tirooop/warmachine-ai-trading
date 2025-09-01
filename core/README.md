# Core System Components

This directory contains the core components of the WarMachine trading system.

## Directory Structure

```
core/
├── controller/           # System control and coordination
│   ├── main.py             # Main system entry point
│   ├── routine_scheduler.py # Task scheduling
│   └── run_warmachine.py   # System runner
├── data/                # Data management
│   └── market_data_hub.py  # Market data integration
├── execution/           # Trade execution
│   └── [Placeholder]       # Trade execution components
├── analysis/           # Market analysis
│   └── [Placeholder]       # Analysis components
└── notification/       # System notifications
    └── [Placeholder]       # Notification components
```

## Component Descriptions

### Controller
- System initialization and coordination
- Task scheduling and management
- System state management
- Configuration handling

### Data
- Market data integration
- Data normalization
- Real-time data processing
- Historical data management

### Execution
- Order execution
- Position management
- Risk control
- Trade monitoring

### Analysis
- Market analysis tools
- Technical indicators
- Pattern recognition
- Signal generation

### Notification
- Alert management
- Status updates
- Error reporting
- System monitoring

## Integration Points

The core components integrate with other system modules:
- Trading strategies
- AI engine
- Web dashboard
- External connectors
- Community features

## Development Status

Current development priorities:
1. Enhanced risk management
2. Advanced execution algorithms
3. Real-time analysis improvements
4. System monitoring enhancements

## AI Scheduler

The AI Scheduler (`ai_scheduler.py`) provides centralized management of all AI-related components in the system. It coordinates the initialization, execution, and monitoring of:

- Market analysis engines
- Prediction models
- Signal generation
- Strategy evolution
- Performance monitoring
- Self-improvement processes

### Configuration

The AI Scheduler is configured through `config/ai_scheduler_config.json`. Key configuration sections include:

```json
{
    "ai_scheduler": {
        "enabled": true,
        "components": {
            "model_router": { ... },
            "analyzer": { ... },
            "alert_generator": { ... },
            "trading_manager": { ... },
            "feedback_learner": { ... }
        }
    }
}
```

### Usage

To use the AI Scheduler in your code:

```python
from warmachine.core.ai_scheduler import AIScheduler

# Initialize scheduler
scheduler = AIScheduler(config)

# Start all components
await scheduler.start()

# Perform market analysis
analysis = await scheduler.analyze_market(market_data)

# Execute trades
await scheduler.execute_trades(signals)

# Process feedback
await scheduler.process_feedback(trading_results)

# Generate system report
report = await scheduler.generate_report()

# Stop all components
await scheduler.stop()
```

### Components

1. **Model Router**
   - Manages AI model selection and execution
   - Handles model versioning and updates
   - Provides unified interface for all AI operations

2. **Market Analyzer**
   - Performs technical and fundamental analysis
   - Generates trading signals
   - Monitors market conditions

3. **Alert Generator**
   - Creates real-time alerts based on analysis
   - Manages notification priorities
   - Handles alert distribution

4. **Trading Manager**
   - Executes trading decisions
   - Manages position sizing
   - Implements risk management

5. **Feedback Learner**
   - Processes trading results
   - Updates AI models
   - Improves strategy performance

### Integration

The AI Scheduler integrates with other system components through:

1. **Event Pool**
   - Handles asynchronous communication
   - Manages event queues
   - Provides pub/sub functionality

2. **Data Hub**
   - Centralizes market data access
   - Manages data caching
   - Handles real-time updates

3. **Notification System**
   - Distributes alerts and reports
   - Manages communication channels
   - Handles message formatting

### Monitoring

The scheduler provides built-in monitoring capabilities:

1. **Health Checks**
   - Component status monitoring
   - Error detection and reporting
   - Automatic recovery attempts

2. **Performance Metrics**
   - Component-level metrics
   - System-wide statistics
   - Resource utilization tracking

3. **Logging**
   - Detailed operation logs
   - Error tracking
   - Performance monitoring

### Error Handling

The scheduler implements comprehensive error handling:

1. **Component Failures**
   - Automatic restart attempts
   - Graceful degradation
   - Alert generation

2. **System Warnings**
   - Early warning detection
   - Preventive measures
   - Administrator notifications

3. **Recovery Procedures**
   - Automatic recovery
   - Manual intervention options
   - Data consistency checks

## Contributing

When contributing to the AI Scheduler:

1. Follow the existing code structure
2. Add comprehensive documentation
3. Include unit tests
4. Update the configuration schema
5. Test all component interactions

## License

This component is part of the WarMachine trading system and is subject to the same license terms as the main project. 