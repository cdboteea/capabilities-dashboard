# Portfolio Analytics Service

Advanced portfolio performance and risk analytics service for the Real-Time Intel platform.

## Overview

The Portfolio Analytics service provides comprehensive financial analysis capabilities including:

- **Performance Analytics**: Returns, volatility, risk-adjusted metrics (Sharpe, Sortino, Calmar ratios)
- **Risk Management**: VaR, CVaR, maximum drawdown, stress testing, scenario analysis
- **Attribution Analysis**: Sector and asset class performance attribution
- **Correlation Analysis**: Asset correlation matrices and diversification metrics
- **Portfolio Optimization**: Modern Portfolio Theory-based optimization
- **Comparative Analysis**: Multi-portfolio performance comparison
- **Historical Tracking**: Time-series analytics and trend analysis

## Features

### Core Analytics
- **Performance Metrics**: Total return, annualized return, volatility, Sharpe ratio, Sortino ratio, Calmar ratio
- **Risk Metrics**: Value at Risk (95%, 99%), Conditional VaR, maximum drawdown, skewness, kurtosis
- **Benchmark Comparison**: Alpha, beta, information ratio, tracking error vs benchmark
- **Attribution**: Allocation effect, selection effect, sector/asset class attribution

### Advanced Analytics
- **Correlation Analysis**: Asset correlation matrices, diversification ratios, cluster analysis
- **Portfolio Optimization**: Mean-variance optimization, efficient frontier calculation
- **Scenario Analysis**: Stress testing, Monte Carlo simulation, tail risk analysis
- **Factor Analysis**: Multi-factor risk decomposition (when factor data available)

### Performance Features
- **Caching**: Redis-based caching for improved response times
- **Batch Processing**: Concurrent calculation for multiple portfolios
- **Real-time Updates**: Configurable update frequencies
- **Data Quality**: Comprehensive data validation and quality scoring

## API Endpoints

### Core Analytics
- `POST /analytics/calculate` - Comprehensive portfolio analytics
- `POST /analytics/risk` - Detailed risk analysis
- `POST /analytics/optimize` - Portfolio optimization
- `POST /analytics/correlation` - Correlation analysis

### Quick Access
- `GET /analytics/{portfolio_id}/summary` - Portfolio summary
- `GET /analytics/{portfolio_id}/performance` - Performance metrics only
- `GET /analytics/{portfolio_id}/risk` - Risk metrics only

### Comparison & History
- `POST /analytics/compare` - Multi-portfolio comparison
- `POST /analytics/history` - Historical analytics data

### Administration
- `GET /admin/portfolios` - List all portfolios
- `DELETE /admin/cache/{portfolio_id}` - Clear portfolio cache
- `GET /health` - Service health check
- `GET /metrics` - Prometheus metrics

## Configuration

### Environment Variables
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_research_platform
DB_USER=postgres
DB_PASSWORD=your_password

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Service Configuration
ANALYTICS_HOST=0.0.0.0
ANALYTICS_PORT=8308
LOG_LEVEL=INFO
```

### Configuration File
See `config/config.yml` for detailed configuration options including:
- Risk calculation parameters
- Performance thresholds
- Cache settings
- External service URLs
- Monitoring configuration

## Data Models

### Core Models
- **PortfolioAnalytics**: Complete analytics package
- **PerformanceMetrics**: Performance calculations
- **RiskMetrics**: Risk measurements
- **AttributionMetrics**: Performance attribution
- **CorrelationMatrix**: Correlation analysis results

### Request Models
- **AnalyticsRequest**: Main analytics calculation request
- **RiskAnalysisRequest**: Risk analysis parameters
- **OptimizationRequest**: Portfolio optimization parameters
- **CorrelationRequest**: Correlation analysis parameters

## Calculations

### Performance Metrics

#### Returns
- **Total Return**: `(1 + returns).prod() - 1`
- **Annualized Return**: `(1 + total_return)^(252/days) - 1`
- **Cumulative Return**: `(1 + returns).cumprod()[-1] - 1`

#### Risk-Adjusted Returns
- **Sharpe Ratio**: `(annual_return - risk_free_rate) / volatility`
- **Sortino Ratio**: `(annual_return - risk_free_rate) / downside_deviation`
- **Calmar Ratio**: `annual_return / abs(max_drawdown)`

#### Volatility
- **Historical Volatility**: `returns.std() * sqrt(252)`
- **Downside Deviation**: `sqrt(mean((returns[returns < 0])^2)) * sqrt(252)`

### Risk Metrics

#### Value at Risk (VaR)
- **Historical VaR**: `percentile(returns, (1-confidence)*100)`
- **Conditional VaR**: `mean(returns[returns <= VaR_threshold])`

#### Drawdown Analysis
- **Maximum Drawdown**: `min((cumulative - running_max) / running_max)`
- **Current Drawdown**: Latest drawdown value
- **Drawdown Duration**: Days since last peak

### Benchmark Comparison

#### Alpha and Beta
- **Beta**: `covariance(asset, benchmark) / variance(benchmark)`
- **Alpha**: `asset_return - (risk_free + beta * (benchmark_return - risk_free))`

#### Information Metrics
- **Information Ratio**: `mean(active_returns) / std(active_returns)`
- **Tracking Error**: `std(asset_returns - benchmark_returns) * sqrt(252)`

## Database Schema

### Tables
- `portfolio_analytics_history`: Historical analytics results
- `performance_metrics`: Performance metric time series
- `risk_metrics`: Risk metric time series
- `correlation_matrices`: Correlation analysis results

### Indexes
- Portfolio ID and date indexes for efficient querying
- Composite indexes for time-series analysis

## Deployment

### Docker
```bash
# Build image
docker build -t portfolio-analytics:latest .

# Run container
docker run -d \
  --name portfolio-analytics \
  -p 8308:8308 \
  -e DB_HOST=postgres \
  -e REDIS_HOST=redis \
  portfolio-analytics:latest
```

### Docker Compose
```yaml
services:
  portfolio-analytics:
    build: .
    ports:
      - "8308:8308"
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
```

## Monitoring

### Health Checks
- Database connectivity
- Redis cache availability
- Service initialization status

### Metrics (Prometheus)
- Request counters by endpoint and status
- Calculation duration histograms
- Cache hit/miss ratios
- Error rates and types

### Logging
- Structured JSON logging
- Performance calculation timing
- Error tracking with context
- Cache operations logging

## Development

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Start development server
uvicorn src.main:app --reload --port 8308
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_api.py -v
```

## Performance Considerations

### Optimization Strategies
- **Caching**: Redis caching with configurable TTL
- **Batch Processing**: Concurrent calculations for multiple assets
- **Data Efficiency**: Optimized pandas operations for large datasets
- **Connection Pooling**: Database connection pooling for high throughput

### Scaling
- **Horizontal Scaling**: Stateless service design supports multiple instances
- **Cache Warming**: Background cache warming for frequently accessed portfolios
- **Async Processing**: Full async/await implementation for I/O operations

## Integration

### External Services
- **Price Fetcher**: Historical price data retrieval
- **Holdings Router**: Portfolio composition data
- **Database**: PostgreSQL for persistent storage
- **Cache**: Redis for performance optimization

### Data Flow
1. Receive analytics request
2. Fetch portfolio holdings data
3. Retrieve historical price data
4. Calculate returns time series
5. Compute performance and risk metrics
6. Store results and return response

## Error Handling

### Validation
- Request parameter validation
- Data quality checks
- Business rule validation

### Resilience
- Graceful degradation on data issues
- Fallback calculations for missing data
- Comprehensive error logging

### Recovery
- Automatic retry for transient failures
- Circuit breaker pattern for external services
- Health check endpoints for monitoring

## Security

### Authentication
- Service-to-service authentication
- API key validation
- Request rate limiting

### Data Protection
- Sensitive data encryption
- Audit logging
- Access control validation

## Support

### Documentation
- API documentation via OpenAPI/Swagger
- Code documentation with docstrings
- Configuration examples

### Troubleshooting
- Comprehensive logging for debugging
- Health check endpoints
- Performance metrics for optimization

---

**Service**: Portfolio Analytics  
**Port**: 8308  
**Version**: 1.0.0  
**Status**: Production Ready ✅ 