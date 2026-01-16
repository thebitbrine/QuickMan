#!/usr/bin/env python3
"""
QuickMan Stress Test Suite
Compares performance between C and C# implementations
"""

import http.client
import time
import statistics
import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Tuple
import threading

@dataclass
class RequestResult:
    """Result of a single HTTP request"""
    success: bool
    latency_ms: float
    status_code: int = 0
    error: str = ""

@dataclass
class TestResult:
    """Aggregated test results"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_seconds: float
    requests_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float

class StressTest:
    """HTTP stress testing tool"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.lock = threading.Lock()

    def make_request(self, endpoint: str) -> RequestResult:
        """Make a single HTTP request and measure latency"""
        start_time = time.time()

        try:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
            conn.request("GET", endpoint)
            response = conn.getresponse()
            response.read()  # Read the body to complete the request
            conn.close()

            latency_ms = (time.time() - start_time) * 1000

            return RequestResult(
                success=True,
                latency_ms=latency_ms,
                status_code=response.status
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return RequestResult(
                success=False,
                latency_ms=latency_ms,
                error=str(e)
            )

    def run_test(self, endpoint: str, num_requests: int,
                 concurrent_connections: int, duration_seconds: int = None) -> TestResult:
        """Run stress test with specified parameters"""

        results: List[RequestResult] = []
        start_time = time.time()
        requests_made = 0

        with ThreadPoolExecutor(max_workers=concurrent_connections) as executor:
            if duration_seconds:
                # Duration-based test
                futures = []
                while time.time() - start_time < duration_seconds:
                    future = executor.submit(self.make_request, endpoint)
                    futures.append(future)
                    requests_made += 1

                for future in as_completed(futures):
                    results.append(future.result())
            else:
                # Request count-based test
                futures = [executor.submit(self.make_request, endpoint)
                          for _ in range(num_requests)]
                requests_made = num_requests

                for future in as_completed(futures):
                    results.append(future.result())

        end_time = time.time()
        total_duration = end_time - start_time

        # Calculate statistics
        successful = [r for r in results if r.success]
        latencies = [r.latency_ms for r in successful]

        if not latencies:
            latencies = [0]

        latencies.sort()

        return TestResult(
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(results) - len(successful),
            duration_seconds=total_duration,
            requests_per_second=len(successful) / total_duration if total_duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p50_latency_ms=self._percentile(latencies, 50),
            p95_latency_ms=self._percentile(latencies, 95),
            p99_latency_ms=self._percentile(latencies, 99)
        )

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of sorted data"""
        if not data:
            return 0
        index = int((percentile / 100) * len(data))
        if index >= len(data):
            index = len(data) - 1
        return data[index]

def print_header():
    """Print test suite header"""
    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║        QuickMan Performance Comparison Suite             ║")
    print("║        C HTTP Server Stress Testing                      ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

def print_test_config(config: dict):
    """Print test configuration"""
    print("Test Configuration:")
    print(f"  Requests per test:     {config['requests_per_test']}")
    print(f"  Concurrent connections: {', '.join(map(str, config['concurrent_levels']))}")
    print(f"  Warmup requests:       {config['warmup_requests']}")
    print(f"  Endpoints:             {', '.join(config['endpoints'])}")
    print()

def print_result(name: str, result: TestResult):
    """Print test result"""
    print(f"  Results:")
    print(f"    Requests/sec:    {result.requests_per_second:>10.2f}")
    print(f"    Success rate:    {result.successful_requests/result.total_requests*100:>10.1f}%")
    print(f"    Avg latency:     {result.avg_latency_ms:>10.2f} ms")
    print(f"    Min latency:     {result.min_latency_ms:>10.2f} ms")
    print(f"    Max latency:     {result.max_latency_ms:>10.2f} ms")
    print(f"    P50 latency:     {result.p50_latency_ms:>10.2f} ms")
    print(f"    P95 latency:     {result.p95_latency_ms:>10.2f} ms")
    print(f"    P99 latency:     {result.p99_latency_ms:>10.2f} ms")
    print()

def test_server_available(host: str, port: int) -> bool:
    """Check if server is available"""
    try:
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/status")
        response = conn.getresponse()
        response.read()
        conn.close()
        return response.status == 200
    except:
        return False

def main():
    """Main test execution"""

    # Configuration
    C_PORT = 8001
    WARMUP_REQUESTS = 500
    REQUESTS_PER_TEST = 10000
    CONCURRENT_LEVELS = [10, 50, 100, 200]
    ENDPOINTS = {
        "benchmark": "/benchmark",
        "status": "/status",
        "data": "/data"
    }

    print_header()

    config = {
        'requests_per_test': REQUESTS_PER_TEST,
        'concurrent_levels': CONCURRENT_LEVELS,
        'warmup_requests': WARMUP_REQUESTS,
        'endpoints': list(ENDPOINTS.keys())
    }
    print_test_config(config)

    # Test C server
    print("═══════════════════════════════════════════════════════════")
    print("Testing C Server")
    print("═══════════════════════════════════════════════════════════")
    print()

    if not test_server_available("localhost", C_PORT):
        print(f"ERROR: C server is not running on port {C_PORT}")
        print(f"Please start it with: cd QuickMan.C && ./quickman_example {C_PORT}")
        sys.exit(1)

    print(f"✓ C server is running on port {C_PORT}")
    print()

    c_tester = StressTest("localhost", C_PORT)

    # Warmup
    print("Warming up server...")
    c_tester.run_test("/benchmark", WARMUP_REQUESTS, 10)
    print("✓ Warmup complete")
    print()

    # Store all results for comparison
    all_results = {}

    # Run tests for each endpoint
    for endpoint_name, endpoint_path in ENDPOINTS.items():
        print(f"Testing endpoint: {endpoint_name} ({endpoint_path})")
        print("─" * 63)

        endpoint_results = []

        for concurrent in CONCURRENT_LEVELS:
            print(f"  Concurrent connections: {concurrent}")

            result = c_tester.run_test(
                endpoint_path,
                REQUESTS_PER_TEST,
                concurrent
            )

            endpoint_results.append((concurrent, result))
            print_result(f"C @ {concurrent}", result)

        all_results[endpoint_name] = endpoint_results
        print()

    # Generate summary report
    print("═══════════════════════════════════════════════════════════")
    print("PERFORMANCE SUMMARY")
    print("═══════════════════════════════════════════════════════════")
    print()

    for endpoint_name, results in all_results.items():
        print(f"Endpoint: {endpoint_name}")
        print("─" * 63)
        print(f"{'Connections':<15} {'Req/sec':<15} {'Avg Latency':<15}")
        print("─" * 63)

        for concurrent, result in results:
            print(f"{concurrent:<15} {result.requests_per_second:<15.2f} "
                  f"{result.avg_latency_ms:<15.2f}")
        print()

    # Save results to file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_dir = "stress_test_results"
    os.makedirs(results_dir, exist_ok=True)

    report_file = f"{results_dir}/c_results_{timestamp}.json"

    # Convert results to JSON-serializable format
    json_results = {}
    for endpoint_name, results in all_results.items():
        json_results[endpoint_name] = []
        for concurrent, result in results:
            json_results[endpoint_name].append({
                "concurrent_connections": concurrent,
                "requests_per_second": result.requests_per_second,
                "avg_latency_ms": result.avg_latency_ms,
                "p50_latency_ms": result.p50_latency_ms,
                "p95_latency_ms": result.p95_latency_ms,
                "p99_latency_ms": result.p99_latency_ms,
                "success_rate": result.successful_requests / result.total_requests * 100
            })

    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'server': 'C',
            'port': C_PORT,
            'config': config,
            'results': json_results
        }, f, indent=2)

    print("═══════════════════════════════════════════════════════════")
    print(f"Results saved to: {report_file}")
    print("═══════════════════════════════════════════════════════════")
    print()

if __name__ == "__main__":
    main()
