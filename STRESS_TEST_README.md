# QuickMan Stress Test Suite

Comprehensive performance testing tools for QuickMan HTTP server implementations.

## Overview

This stress test suite provides tools to benchmark and compare the performance of QuickMan server implementations. It measures throughput, latency, and reliability under various load conditions.

## Test Tools

### 1. Python Stress Tester (`stress_test.py`)

A pure Python implementation that requires no external dependencies beyond Python 3's standard library.

#### Features
- Concurrent request testing with configurable connection levels
- Latency measurement (average, min, max, percentiles)
- Throughput calculation (requests per second)
- Success rate tracking
- JSON result output for analysis
- Detailed performance reporting

#### Usage

```bash
# Start your server first
cd QuickMan.C
./quickman_example 8001 500 &

# Run the stress test
python3 stress_test.py
```

#### Configuration

Edit the script to modify test parameters:

```python
C_PORT = 8001                          # Server port
WARMUP_REQUESTS = 500                   # Warmup request count
REQUESTS_PER_TEST = 10000               # Requests per test scenario
CONCURRENT_LEVELS = [10, 50, 100, 200]  # Connection levels to test
```

#### Output

The test generates:
- Real-time console output with progress
- Detailed performance summary table
- JSON results file in `stress_test_results/`

### 2. Bash Stress Tester (`stress_test.sh`)

Advanced bash script that uses `wrk` for professional-grade load testing.

#### Requirements
- `wrk` - Modern HTTP benchmarking tool
- `curl` - For server availability checks
- `gcc` - To build C version
- `dotnet` - To build C# version (if comparing)

#### Installation of wrk

```bash
# Ubuntu/Debian
sudo apt-get install wrk

# macOS
brew install wrk

# From source
git clone https://github.com/wg/wrk.git
cd wrk
make
sudo cp wrk /usr/local/bin/
```

#### Usage

```bash
# Make executable
chmod +x stress_test.sh

# Run comprehensive tests
./stress_test.sh
```

This script will:
1. Build both C and C# versions
2. Start each server automatically
3. Run warmup requests
4. Execute load tests at multiple concurrency levels
5. Generate comparison reports
6. Save detailed results

## Test Scenarios

### Standard Test Configuration

All tests use these parameters by default:

- **Test Duration**: 30 seconds per scenario
- **Concurrent Connection Levels**: 10, 50, 100, 200
- **Warmup**: 1,000 requests before testing
- **Endpoints Tested**:
  - `/benchmark` - Minimal response (performance baseline)
  - `/status` - Status JSON
  - `/data` - Larger JSON with data array

### Custom Testing

You can create custom test scenarios:

```python
# Custom Python test
from stress_test import StressTest

tester = StressTest("localhost", 8001)
result = tester.run_test(
    endpoint="/your-endpoint",
    num_requests=50000,
    concurrent_connections=100
)
print(f"Throughput: {result.requests_per_second:.2f} req/s")
```

## Interpreting Results

### Key Metrics

1. **Requests/sec**: Total throughput (higher is better)
2. **Success Rate**: Percentage of successful requests (should be 100%)
3. **Average Latency**: Mean response time
4. **P50 Latency**: Median response time (50th percentile)
5. **P95 Latency**: 95th percentile (only 5% of requests are slower)
6. **P99 Latency**: 99th percentile (only 1% of requests are slower)

### What to Look For

✅ **Good Performance**:
- High requests/sec (>1,000 for simple endpoints)
- Low average latency (<10ms at low concurrency)
- P95 and P99 close to average (consistent performance)
- 100% success rate

⚠️ **Potential Issues**:
- Success rate < 100% (connection failures)
- Large gap between P50 and P99 (inconsistent performance)
- Throughput decreases significantly with concurrency
- Latency increases exponentially with load

## Performance Baseline

Expected performance for QuickMan C on modern hardware:

| Metric | Expected Value |
|--------|----------------|
| Throughput (10 conn) | 1,200-1,500 req/s |
| Throughput (50 conn) | 1,400-1,600 req/s |
| Throughput (100 conn) | 1,300-1,500 req/s |
| Latency (10 conn) | 6-10 ms |
| Latency (50 conn) | 20-30 ms |
| Success Rate | 100% |

## Comparing C vs C# Performance

To run a full comparison:

```bash
# Automated comparison (if both versions available)
./stress_test.sh

# Manual comparison
# Terminal 1: Start C server
cd QuickMan.C && ./quickman_example 8001

# Terminal 2: Test C server
python3 stress_test.py

# Terminal 3: Start C# server
cd QuickMan.Lib && dotnet run -- 8002

# Terminal 2: Modify stress_test.py port and test C# server
# Edit: C_PORT = 8002
python3 stress_test.py
```

Expected improvements of C over C#:
- **Throughput**: 20-50% higher
- **Latency**: 30-60% lower
- **Memory**: 70-90% less
- **Consistency**: More predictable (no GC pauses)

## Advanced Usage

### High-Load Testing

Test with extreme concurrency:

```python
# Modify CONCURRENT_LEVELS in stress_test.py
CONCURRENT_LEVELS = [100, 200, 500, 1000]
REQUESTS_PER_TEST = 50000  # More requests for statistical significance
```

⚠️ Note: Ensure your system has enough resources (file descriptors, memory)

```bash
# Increase file descriptor limit
ulimit -n 10000
```

### Endurance Testing

Test server stability over extended periods:

```python
# Duration-based testing (add to StressTest class)
result = tester.run_test(
    endpoint="/benchmark",
    num_requests=0,  # Unlimited
    concurrent_connections=50,
    duration_seconds=3600  # 1 hour
)
```

### Latency Analysis

For detailed latency distribution:

```python
# The test already provides percentiles, but you can add more:
# In parse_wrk_results or modify the percentile calculation
percentiles = [50, 75, 90, 95, 99, 99.9]
for p in percentiles:
    print(f"P{p}: {_percentile(latencies, p):.2f} ms")
```

## Troubleshooting

### "Connection Refused" Errors

```bash
# Check if server is running
curl http://localhost:8001/status

# Check port availability
lsof -i :8001

# Verify server logs
tail -f stress_test_results/*_server.log
```

### Low Performance

1. **Check CPU**: `top` or `htop` - ensure CPU isn't maxed out
2. **Check Memory**: `free -h` - ensure adequate RAM
3. **Check Network**: `netstat -s` - look for dropped packets
4. **Check Limits**: `ulimit -a` - verify file descriptor limits

### Inconsistent Results

- Run warmup phase longer
- Increase test duration
- Ensure no other processes are competing for resources
- Run tests multiple times and average results

## Results Storage

All test results are saved in `stress_test_results/`:

```
stress_test_results/
├── c_results_20260116_235257.json       # Python test results
├── c_server_20260116_235257.log         # Server logs
├── cs_server_20260116_235257.log        # C# server logs
├── comparison_report_20260116.txt       # Comparison report
└── *_Simple_c50_20260116.txt           # wrk detailed results
```

## Best Practices

1. **Consistent Environment**: Always test in the same environment
2. **Warmup**: Always include warmup phase
3. **Multiple Runs**: Run tests 3-5 times and average results
4. **Resource Monitoring**: Monitor CPU, memory, network during tests
5. **Baseline**: Establish a baseline before optimizations
6. **Document Changes**: Note any configuration changes
7. **Reproducibility**: Save test parameters with results

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Performance Test

on: [push]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Server
        run: cd QuickMan.C && make
      - name: Run Performance Test
        run: |
          cd QuickMan.C && ./quickman_example 8001 &
          sleep 2
          python3 stress_test.py
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: performance-results
          path: stress_test_results/
```

## Further Reading

- [PERFORMANCE_ANALYSIS.md](PERFORMANCE_ANALYSIS.md) - Detailed analysis of test results
- [QuickMan.C/README.md](QuickMan.C/README.md) - C implementation documentation
- [wrk documentation](https://github.com/wg/wrk) - Advanced wrk usage

## License

Part of the QuickMan project. See main README for license information.
