#!/usr/bin/env python3
"""
QuickMan 1:1 Comparison Test Suite
Head-to-head performance comparison between C and C# implementations
Identical tests, identical load, real numbers
"""

import http.client
import time
import statistics
import json
import sys
import os
import subprocess
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process, Manager, cpu_count
from dataclasses import dataclass
from typing import List, Dict, Tuple
import psutil

@dataclass
class ServerMetrics:
    """Real-time server metrics"""
    cpu_percent: float
    memory_mb: float
    threads: int
    connections: int

@dataclass
class ComparisonResult:
    """Results from a single test"""
    server_name: str
    test_name: str
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
    peak_cpu_percent: float
    peak_memory_mb: float
    error_types: Dict[str, int]

class ServerProcess:
    """Manages server process lifecycle"""

    def __init__(self, name: str, command: List[str], port: int, cwd: str = None):
        self.name = name
        self.command = command
        self.port = port
        self.cwd = cwd
        self.process = None
        self.pid = None

    def start(self):
        """Start the server"""
        print(f"  Starting {self.name} server...")
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd
            )
            self.pid = self.process.pid

            # Wait for server to be ready
            time.sleep(3)

            # Verify server is running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                print(f"    ERROR: Server failed to start!")
                print(f"    STDOUT: {stdout.decode()}")
                print(f"    STDERR: {stderr.decode()}")
                return False

            # Check if responding
            for i in range(5):
                try:
                    conn = http.client.HTTPConnection("localhost", self.port, timeout=2)
                    conn.request("GET", "/status")
                    response = conn.getresponse()
                    response.read()
                    conn.close()

                    if response.status == 200:
                        print(f"    ✓ {self.name} server started successfully (PID: {self.pid})")
                        return True
                except:
                    time.sleep(1)

            print(f"    ✗ Server not responding on port {self.port}")
            self.stop()
            return False

        except Exception as e:
            print(f"    ERROR starting server: {e}")
            return False

    def stop(self):
        """Stop the server"""
        if self.process:
            print(f"  Stopping {self.name} server...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
            self.pid = None
            print(f"    ✓ {self.name} server stopped")

    def get_metrics(self) -> ServerMetrics:
        """Get current server metrics"""
        if not self.pid:
            return ServerMetrics(0, 0, 0, 0)

        try:
            proc = psutil.Process(self.pid)
            return ServerMetrics(
                cpu_percent=proc.cpu_percent(interval=0.1),
                memory_mb=proc.memory_info().rss / 1024 / 1024,
                threads=proc.num_threads(),
                connections=len(proc.connections())
            )
        except:
            return ServerMetrics(0, 0, 0, 0)


class ComparisonTester:
    """Runs identical tests on both servers"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def make_request(self, endpoint: str) -> Tuple[bool, float, int, str]:
        """Make a single request and return (success, latency_ms, status_code, error)"""
        start_time = time.time()

        try:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
            conn.request("GET", endpoint)
            response = conn.getresponse()
            response.read()
            conn.close()

            latency_ms = (time.time() - start_time) * 1000

            return (True, latency_ms, response.status, "")
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return (False, latency_ms, 0, type(e).__name__)

    def run_test(self, test_name: str, endpoint: str, num_requests: int,
                 concurrent_connections: int, server_process: ServerProcess) -> ComparisonResult:
        """Run a single test scenario"""

        print(f"\n    Running: {test_name}")
        print(f"      Requests: {num_requests}, Concurrency: {concurrent_connections}")

        results = []
        error_types = {}
        peak_cpu = 0
        peak_memory = 0

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_connections) as executor:
            futures = [executor.submit(self.make_request, endpoint)
                      for _ in range(num_requests)]

            # Monitor server metrics while requests are running
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1

                # Update metrics every 100 requests
                if completed % 100 == 0:
                    metrics = server_process.get_metrics()
                    peak_cpu = max(peak_cpu, metrics.cpu_percent)
                    peak_memory = max(peak_memory, metrics.memory_mb)

        duration = time.time() - start_time

        # Calculate statistics
        successful = [r for r in results if r[0]]
        latencies = [r[1] for r in successful]
        failed = [r for r in results if not r[0]]

        for r in failed:
            error_type = r[3]
            error_types[error_type] = error_types.get(error_type, 0) + 1

        if not latencies:
            latencies = [0]

        latencies.sort()

        print(f"      ✓ Completed: {len(successful)} successful, {len(failed)} failed")
        print(f"      ✓ Throughput: {len(successful)/duration:.2f} req/s")
        print(f"      ✓ Avg Latency: {statistics.mean(latencies):.2f} ms")

        return ComparisonResult(
            server_name=server_process.name,
            test_name=test_name,
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            duration_seconds=duration,
            requests_per_second=len(successful) / duration if duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p50_latency_ms=self._percentile(latencies, 50),
            p95_latency_ms=self._percentile(latencies, 95),
            p99_latency_ms=self._percentile(latencies, 99),
            peak_cpu_percent=peak_cpu,
            peak_memory_mb=peak_memory,
            error_types=error_types
        )

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        index = int((percentile / 100) * len(data))
        if index >= len(data):
            index = len(data) - 1
        return data[index]


def print_header():
    """Print test header"""
    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║       QUICKMAN 1:1 COMPARISON TEST SUITE                     ║")
    print("║       C vs C# - Head to Head Performance Battle              ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()


def print_comparison_table(c_results: List[ComparisonResult],
                          cs_results: List[ComparisonResult]):
    """Print side-by-side comparison table"""

    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║                    COMPARISON RESULTS                         ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    for i, (c_res, cs_res) in enumerate(zip(c_results, cs_results)):
        print(f"Test: {c_res.test_name}")
        print("─" * 70)

        # Throughput comparison
        print(f"{'Metric':<30} {'C':<15} {'C#':<15} {'Improvement':<10}")
        print("─" * 70)

        # Requests/sec
        c_rps = c_res.requests_per_second
        cs_rps = cs_res.requests_per_second
        improvement = ((c_rps - cs_rps) / cs_rps * 100) if cs_rps > 0 else 0
        print(f"{'Requests/sec':<30} {c_rps:>14.2f} {cs_rps:>14.2f} {improvement:>9.1f}%")

        # Average latency
        c_lat = c_res.avg_latency_ms
        cs_lat = cs_res.avg_latency_ms
        improvement = ((cs_lat - c_lat) / cs_lat * 100) if cs_lat > 0 else 0
        print(f"{'Avg Latency (ms)':<30} {c_lat:>14.2f} {cs_lat:>14.2f} {improvement:>9.1f}%")

        # P95 latency
        c_p95 = c_res.p95_latency_ms
        cs_p95 = cs_res.p95_latency_ms
        improvement = ((cs_p95 - c_p95) / cs_p95 * 100) if cs_p95 > 0 else 0
        print(f"{'P95 Latency (ms)':<30} {c_p95:>14.2f} {cs_p95:>14.2f} {improvement:>9.1f}%")

        # P99 latency
        c_p99 = c_res.p99_latency_ms
        cs_p99 = cs_res.p99_latency_ms
        improvement = ((cs_p99 - c_p99) / cs_p99 * 100) if cs_p99 > 0 else 0
        print(f"{'P99 Latency (ms)':<30} {c_p99:>14.2f} {cs_p99:>14.2f} {improvement:>9.1f}%")

        # CPU
        c_cpu = c_res.peak_cpu_percent
        cs_cpu = cs_res.peak_cpu_percent
        improvement = ((cs_cpu - c_cpu) / cs_cpu * 100) if cs_cpu > 0 else 0
        print(f"{'Peak CPU (%)':<30} {c_cpu:>14.2f} {cs_cpu:>14.2f} {improvement:>9.1f}%")

        # Memory
        c_mem = c_res.peak_memory_mb
        cs_mem = cs_res.peak_memory_mb
        improvement = ((cs_mem - c_mem) / cs_mem * 100) if cs_mem > 0 else 0
        print(f"{'Peak Memory (MB)':<30} {c_mem:>14.2f} {cs_mem:>14.2f} {improvement:>9.1f}%")

        # Success rate
        c_success = c_res.successful_requests / c_res.total_requests * 100
        cs_success = cs_res.successful_requests / cs_res.total_requests * 100
        print(f"{'Success Rate (%)':<30} {c_success:>14.2f} {cs_success:>14.2f}")

        print()


def main():
    """Main execution"""

    C_PORT = 8001
    CS_PORT = 8002

    print_header()

    # Test configuration
    TEST_SCENARIOS = [
        ("Low Load (1K, 10 conn)", "/benchmark", 1000, 10),
        ("Medium Load (10K, 50 conn)", "/benchmark", 10000, 50),
        ("High Load (50K, 100 conn)", "/benchmark", 50000, 100),
        ("Extreme Load (100K, 200 conn)", "/benchmark", 100000, 200),
        ("JSON Endpoint (10K, 50 conn)", "/status", 10000, 50),
        ("Data Endpoint (10K, 50 conn)", "/data", 10000, 50),
    ]

    print("Test Configuration:")
    print(f"  CPU Cores: {cpu_count()}")
    print(f"  Test Scenarios: {len(TEST_SCENARIOS)}")
    print()

    # Define servers
    c_server = ServerProcess(
        "C",
        ["./quickman_example", str(C_PORT), "5000"],
        C_PORT,
        cwd="QuickMan.C"
    )

    cs_server = ServerProcess(
        "C#",
        ["dotnet", "run", "-c", "Release", "--", str(CS_PORT), "5000"],
        CS_PORT,
        cwd="QuickMan.Lib"
    )

    c_results = []
    cs_results = []

    try:
        # Test C version
        print("╔═══════════════════════════════════════════════════════════════╗")
        print("║ TESTING C VERSION                                            ║")
        print("╚═══════════════════════════════════════════════════════════════╝")

        if not c_server.start():
            print("ERROR: Failed to start C server")
            return 1

        c_tester = ComparisonTester("localhost", C_PORT)

        # Warmup
        print("\n  Warming up...")
        c_tester.run_test("Warmup", "/benchmark", 500, 10, c_server)

        # Run tests
        for test_name, endpoint, requests, concurrency in TEST_SCENARIOS:
            result = c_tester.run_test(test_name, endpoint, requests, concurrency, c_server)
            c_results.append(result)
            time.sleep(2)

        c_server.stop()
        time.sleep(3)

        # Test C# version
        print("\n╔═══════════════════════════════════════════════════════════════╗")
        print("║ TESTING C# VERSION                                           ║")
        print("╚═══════════════════════════════════════════════════════════════╝")

        if not cs_server.start():
            print("ERROR: Failed to start C# server")
            print("Make sure .NET is installed and QuickMan.Lib/Program.cs exists")
            return 1

        cs_tester = ComparisonTester("localhost", CS_PORT)

        # Warmup
        print("\n  Warming up...")
        cs_tester.run_test("Warmup", "/benchmark", 500, 10, cs_server)

        # Run tests
        for test_name, endpoint, requests, concurrency in TEST_SCENARIOS:
            result = cs_tester.run_test(test_name, endpoint, requests, concurrency, cs_server)
            cs_results.append(result)
            time.sleep(2)

        cs_server.stop()

        # Print comparison
        print_comparison_table(c_results, cs_results)

        # Calculate overall statistics
        print("\n╔═══════════════════════════════════════════════════════════════╗")
        print("║                    OVERALL SUMMARY                            ║")
        print("╚═══════════════════════════════════════════════════════════════╝\n")

        c_avg_rps = statistics.mean([r.requests_per_second for r in c_results])
        cs_avg_rps = statistics.mean([r.requests_per_second for r in cs_results])
        c_avg_lat = statistics.mean([r.avg_latency_ms for r in c_results])
        cs_avg_lat = statistics.mean([r.avg_latency_ms for r in cs_results])
        c_avg_cpu = statistics.mean([r.peak_cpu_percent for r in c_results if r.peak_cpu_percent > 0])
        cs_avg_cpu = statistics.mean([r.peak_cpu_percent for r in cs_results if r.peak_cpu_percent > 0])
        c_avg_mem = statistics.mean([r.peak_memory_mb for r in c_results if r.peak_memory_mb > 0])
        cs_avg_mem = statistics.mean([r.peak_memory_mb for r in cs_results if r.peak_memory_mb > 0])

        print(f"{'Metric':<30} {'C':<15} {'C#':<15} {'C Advantage':<15}")
        print("─" * 75)
        print(f"{'Avg Throughput (req/s)':<30} {c_avg_rps:>14.2f} {cs_avg_rps:>14.2f} {((c_avg_rps-cs_avg_rps)/cs_avg_rps*100):>14.1f}%")
        print(f"{'Avg Latency (ms)':<30} {c_avg_lat:>14.2f} {cs_avg_lat:>14.2f} {((cs_avg_lat-c_avg_lat)/cs_avg_lat*100):>14.1f}%")
        print(f"{'Avg CPU Usage (%)':<30} {c_avg_cpu:>14.2f} {cs_avg_cpu:>14.2f} {((cs_avg_cpu-c_avg_cpu)/cs_avg_cpu*100):>14.1f}%")
        print(f"{'Avg Memory (MB)':<30} {c_avg_mem:>14.2f} {cs_avg_mem:>14.2f} {((cs_avg_mem-c_avg_mem)/cs_avg_mem*100):>14.1f}%")

        print("\n" + "═" * 75 + "\n")

        # Determine winner
        c_wins = sum(1 for c, cs in zip(c_results, cs_results)
                    if c.requests_per_second > cs.requests_per_second)
        cs_wins = len(c_results) - c_wins

        print(f"🏆 WINNER: {'C' if c_wins > cs_wins else 'C#'}")
        print(f"   C won {c_wins}/{len(c_results)} tests")
        print(f"   C# won {cs_wins}/{len(c_results)} tests")
        print()

        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_dir = "stress_test_results"
        os.makedirs(results_dir, exist_ok=True)

        report_file = f"{results_dir}/comparison_{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'c_results': [vars(r) for r in c_results],
                'cs_results': [vars(r) for r in cs_results],
                'summary': {
                    'c_avg_rps': c_avg_rps,
                    'cs_avg_rps': cs_avg_rps,
                    'c_avg_latency': c_avg_lat,
                    'cs_avg_latency': cs_avg_lat,
                    'c_wins': c_wins,
                    'cs_wins': cs_wins
                }
            }, f, indent=2)

        print(f"Full results saved to: {report_file}\n")

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        c_server.stop()
        cs_server.stop()
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        c_server.stop()
        cs_server.stop()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
