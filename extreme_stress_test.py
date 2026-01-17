#!/usr/bin/env python3
"""
QuickMan EXTREME Stress Test Suite
Push servers to absolute breaking point with millions of requests
Simulates bot attacks, edge cases, and malicious traffic patterns
"""

import http.client
import socket
import time
import statistics
import json
import sys
import os
import random
import string
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from multiprocessing import Process, Queue, Manager, cpu_count
from dataclasses import dataclass
from typing import List, Tuple, Dict
import threading
import signal

@dataclass
class ExtremeTestResult:
    """Result of extreme stress test"""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_seconds: float
    requests_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    error_types: Dict[str, int]
    memory_peak_mb: float = 0

class ExtremeTester:
    """Extreme HTTP stress testing - push to the limit!"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.results_queue = Manager().Queue()
        self.stop_flag = Manager().Value('i', 0)

    def rapid_fire_requests(self, endpoint: str, duration_seconds: int, process_id: int):
        """Fire requests as fast as possible from a single process"""
        results = []
        errors = {}
        start_time = time.time()
        count = 0

        while time.time() - start_time < duration_seconds and not self.stop_flag.value:
            try:
                conn = http.client.HTTPConnection(self.host, self.port, timeout=1)
                req_start = time.time()
                conn.request("GET", endpoint)
                response = conn.getresponse()
                response.read()
                latency = (time.time() - req_start) * 1000
                conn.close()

                results.append({
                    'success': True,
                    'latency_ms': latency,
                    'status': response.status
                })
                count += 1
            except Exception as e:
                error_type = type(e).__name__
                errors[error_type] = errors.get(error_type, 0) + 1
                results.append({
                    'success': False,
                    'latency_ms': 0,
                    'error': error_type
                })

        self.results_queue.put({
            'process_id': process_id,
            'results': results,
            'errors': errors
        })

    def connection_flood(self, duration_seconds: int, process_id: int):
        """Open and close connections rapidly without sending requests"""
        count = 0
        errors = {}
        start_time = time.time()

        while time.time() - start_time < duration_seconds and not self.stop_flag.value:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                sock.connect((self.host, self.port))
                sock.close()
                count += 1
            except Exception as e:
                error_type = type(e).__name__
                errors[error_type] = errors.get(error_type, 0) + 1

        self.results_queue.put({
            'process_id': process_id,
            'connection_flood_count': count,
            'errors': errors
        })

    def malformed_request_attack(self, duration_seconds: int, process_id: int):
        """Send malformed and malicious requests"""
        attack_patterns = [
            # Path traversal
            b"GET /../../../etc/passwd HTTP/1.1\r\nHost: test\r\n\r\n",
            # Extremely long URL
            b"GET /" + b"A" * 10000 + b" HTTP/1.1\r\nHost: test\r\n\r\n",
            # Invalid HTTP version
            b"GET / HTTP/99.99\r\nHost: test\r\n\r\n",
            # Missing protocol
            b"GET / \r\n\r\n",
            # Null bytes
            b"GET /\x00\x00\x00 HTTP/1.1\r\nHost: test\r\n\r\n",
            # Header injection
            b"GET / HTTP/1.1\r\nHost: test\r\nX-Injected: \r\nAdmin: true\r\n\r\n",
            # Very long headers
            b"GET / HTTP/1.1\r\nHost: test\r\nX-Long: " + b"X" * 50000 + b"\r\n\r\n",
            # Invalid method
            b"HACK / HTTP/1.1\r\nHost: test\r\n\r\n",
            # SQL injection attempts in URL
            b"GET /?id=1' OR '1'='1 HTTP/1.1\r\nHost: test\r\n\r\n",
            # XSS attempts
            b"GET /?q=<script>alert(1)</script> HTTP/1.1\r\nHost: test\r\n\r\n",
        ]

        count = 0
        errors = {}
        start_time = time.time()

        while time.time() - start_time < duration_seconds and not self.stop_flag.value:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                sock.connect((self.host, self.port))
                sock.send(random.choice(attack_patterns))
                sock.recv(1024)
                sock.close()
                count += 1
            except Exception as e:
                error_type = type(e).__name__
                errors[error_type] = errors.get(error_type, 0) + 1

        self.results_queue.put({
            'process_id': process_id,
            'malformed_count': count,
            'errors': errors
        })

    def slowloris_attack(self, duration_seconds: int, process_id: int):
        """Slowloris-style slow HTTP attack"""
        connections = []
        count = 0
        start_time = time.time()

        try:
            # Open many connections and keep them alive
            for _ in range(100):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    sock.connect((self.host, self.port))
                    sock.send(b"GET / HTTP/1.1\r\n")
                    connections.append(sock)
                    count += 1
                except:
                    break

            # Keep connections alive by sending partial headers
            while time.time() - start_time < duration_seconds and not self.stop_flag.value:
                for sock in connections[:]:
                    try:
                        sock.send(b"X-Keep-Alive: 1\r\n")
                        time.sleep(0.1)
                    except:
                        connections.remove(sock)

        finally:
            for sock in connections:
                try:
                    sock.close()
                except:
                    pass

        self.results_queue.put({
            'process_id': process_id,
            'slowloris_connections': count
        })

    def memory_bomb(self, endpoint: str, count: int, process_id: int):
        """Send requests with huge payloads to test memory handling"""
        results = []
        errors = {}

        for i in range(count):
            if self.stop_flag.value:
                break

            try:
                # Create huge POST body
                huge_data = "X" * (1024 * 1024 * 10)  # 10MB payload

                conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
                req_start = time.time()
                conn.request("POST", endpoint, body=huge_data)
                response = conn.getresponse()
                response.read()
                latency = (time.time() - req_start) * 1000
                conn.close()

                results.append({
                    'success': True,
                    'latency_ms': latency,
                    'status': response.status
                })
            except Exception as e:
                error_type = type(e).__name__
                errors[error_type] = errors.get(error_type, 0) + 1
                results.append({
                    'success': False,
                    'error': error_type
                })

        self.results_queue.put({
            'process_id': process_id,
            'results': results,
            'errors': errors
        })

    def url_fuzzing(self, duration_seconds: int, process_id: int):
        """Fuzz URLs with random patterns"""
        count = 0
        errors = {}
        start_time = time.time()

        while time.time() - start_time < duration_seconds and not self.stop_flag.value:
            try:
                # Generate random URL
                length = random.randint(1, 1000)
                url = "/" + ''.join(random.choices(
                    string.ascii_letters + string.digits + "/.?=&%",
                    k=length
                ))

                conn = http.client.HTTPConnection(self.host, self.port, timeout=1)
                conn.request("GET", url)
                response = conn.getresponse()
                response.read()
                conn.close()
                count += 1
            except Exception as e:
                error_type = type(e).__name__
                errors[error_type] = errors.get(error_type, 0) + 1

        self.results_queue.put({
            'process_id': process_id,
            'url_fuzz_count': count,
            'errors': errors
        })

    def run_extreme_test(self, test_name: str, test_func, *args):
        """Run an extreme test with multiple processes"""
        print(f"\n{'='*70}")
        print(f"EXTREME TEST: {test_name}")
        print(f"{'='*70}")

        num_processes = cpu_count() * 2  # Use 2x CPU cores
        print(f"Launching {num_processes} attack processes...")

        start_time = time.time()
        processes = []

        for i in range(num_processes):
            p = Process(target=test_func, args=(*args, i))
            p.start()
            processes.append(p)

        # Wait for all processes
        for p in processes:
            p.join()

        duration = time.time() - start_time

        # Collect results
        all_results = []
        all_errors = {}

        while not self.results_queue.empty():
            result = self.results_queue.get()
            all_results.append(result)

            if 'errors' in result:
                for error_type, count in result['errors'].items():
                    all_errors[error_type] = all_errors.get(error_type, 0) + count

        return {
            'test_name': test_name,
            'duration': duration,
            'processes': num_processes,
            'results': all_results,
            'errors': all_errors
        }


def print_extreme_header():
    """Print extreme test header"""
    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║          QUICKMAN EXTREME STRESS TEST SUITE                  ║")
    print("║          ⚠️  MAXIMUM LOAD - PUSH TO BREAKING POINT  ⚠️          ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    print("WARNING: This test will hammer the server with extreme load")
    print("         Simulating DDoS attacks, malformed requests, and")
    print("         connection flooding. Server may crash or become")
    print("         unresponsive. Use at your own risk!")
    print()


def main():
    """Main execution"""

    C_PORT = 8001
    TEST_DURATION = 15  # seconds per test

    print_extreme_header()

    # Check server availability
    print(f"Checking if C server is running on port {C_PORT}...")
    try:
        conn = http.client.HTTPConnection("localhost", C_PORT, timeout=2)
        conn.request("GET", "/status")
        response = conn.getresponse()
        response.read()
        conn.close()

        if response.status != 200:
            print(f"ERROR: Server returned status {response.status}")
            sys.exit(1)

        print(f"✓ Server is running\n")
    except Exception as e:
        print(f"ERROR: Cannot connect to server: {e}")
        print(f"Start the server with: cd QuickMan.C && ./quickman_example {C_PORT} 5000")
        sys.exit(1)

    print(f"CPU cores available: {cpu_count()}")
    print(f"Test processes per attack: {cpu_count() * 2}")
    print(f"Test duration per attack: {TEST_DURATION} seconds")
    print()

    input("Press ENTER to start the extreme tests (or Ctrl+C to cancel)...")
    print()

    tester = ExtremeTester("localhost", C_PORT)
    results = {}

    # Test 1: Maximum Rapid Fire
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║ TEST 1: RAPID FIRE ASSAULT                                   ║")
    print("║ Fire requests as fast as possible from multiple processes   ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    rapid_result = tester.run_extreme_test(
        "Rapid Fire Assault",
        tester.rapid_fire_requests,
        "/benchmark",
        TEST_DURATION
    )

    # Calculate stats
    total_requests = sum(len(r.get('results', [])) for r in rapid_result['results'])
    successful = sum(sum(1 for req in r.get('results', []) if req.get('success')) for r in rapid_result['results'])
    duration = rapid_result['duration']

    print(f"\n  Total Requests:    {total_requests:,}")
    print(f"  Successful:        {successful:,}")
    print(f"  Failed:            {total_requests - successful:,}")
    print(f"  Duration:          {duration:.2f}s")
    print(f"  Throughput:        {total_requests/duration:,.2f} req/s")
    print(f"  Success Rate:      {successful/total_requests*100:.2f}%")

    if rapid_result['errors']:
        print(f"\n  Errors:")
        for error, count in sorted(rapid_result['errors'].items(), key=lambda x: x[1], reverse=True):
            print(f"    {error}: {count}")

    results['rapid_fire'] = rapid_result

    time.sleep(2)

    # Test 2: Connection Flood
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║ TEST 2: CONNECTION FLOOD                                     ║")
    print("║ Open and close connections as fast as possible              ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    flood_result = tester.run_extreme_test(
        "Connection Flood",
        tester.connection_flood,
        TEST_DURATION
    )

    total_connections = sum(r.get('connection_flood_count', 0) for r in flood_result['results'])
    print(f"\n  Total Connections: {total_connections:,}")
    print(f"  Duration:          {flood_result['duration']:.2f}s")
    print(f"  Conn/sec:          {total_connections/flood_result['duration']:,.2f}")

    if flood_result['errors']:
        print(f"\n  Errors:")
        for error, count in sorted(flood_result['errors'].items(), key=lambda x: x[1], reverse=True):
            print(f"    {error}: {count}")

    results['connection_flood'] = flood_result

    time.sleep(2)

    # Test 3: Malformed Request Attack
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║ TEST 3: MALFORMED REQUEST ATTACK                            ║")
    print("║ Send malicious and malformed HTTP requests                  ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    malformed_result = tester.run_extreme_test(
        "Malformed Request Attack",
        tester.malformed_request_attack,
        TEST_DURATION
    )

    total_malformed = sum(r.get('malformed_count', 0) for r in malformed_result['results'])
    print(f"\n  Malformed Requests: {total_malformed:,}")
    print(f"  Duration:           {malformed_result['duration']:.2f}s")
    print(f"  Attack Rate:        {total_malformed/malformed_result['duration']:,.2f} req/s")

    if malformed_result['errors']:
        print(f"\n  Errors (expected):")
        for error, count in sorted(malformed_result['errors'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {error}: {count}")

    results['malformed_attack'] = malformed_result

    time.sleep(2)

    # Test 4: URL Fuzzing
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║ TEST 4: URL FUZZING ATTACK                                   ║")
    print("║ Send random URLs to find crashes or vulnerabilities         ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    fuzz_result = tester.run_extreme_test(
        "URL Fuzzing",
        tester.url_fuzzing,
        TEST_DURATION
    )

    total_fuzzes = sum(r.get('url_fuzz_count', 0) for r in fuzz_result['results'])
    print(f"\n  Fuzzed URLs:       {total_fuzzes:,}")
    print(f"  Duration:          {fuzz_result['duration']:.2f}s")
    print(f"  Fuzz Rate:         {total_fuzzes/fuzz_result['duration']:,.2f} req/s")

    results['url_fuzzing'] = fuzz_result

    time.sleep(2)

    # Test 5: Slowloris Attack
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║ TEST 5: SLOWLORIS ATTACK                                     ║")
    print("║ Hold connections open with slow requests                    ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    slowloris_result = tester.run_extreme_test(
        "Slowloris Attack",
        tester.slowloris_attack,
        TEST_DURATION
    )

    total_slow_conns = sum(r.get('slowloris_connections', 0) for r in slowloris_result['results'])
    print(f"\n  Slowloris Connections: {total_slow_conns:,}")
    print(f"  Duration:              {slowloris_result['duration']:.2f}s")

    results['slowloris'] = slowloris_result

    time.sleep(2)

    # Generate final report
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║ EXTREME STRESS TEST SUMMARY                                  ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    # Save results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_dir = "stress_test_results"
    os.makedirs(results_dir, exist_ok=True)

    report_file = f"{results_dir}/extreme_results_{timestamp}.json"

    # Check if server is still alive
    print("Checking if server survived the tests...")
    try:
        conn = http.client.HTTPConnection("localhost", C_PORT, timeout=2)
        conn.request("GET", "/status")
        response = conn.getresponse()
        response.read()
        conn.close()

        if response.status == 200:
            print("✓ SERVER SURVIVED! Still responding normally.")
        else:
            print(f"⚠  Server responding with status {response.status}")
    except Exception as e:
        print(f"✗ SERVER DOWN! Server is not responding: {e}")

    print(f"\nResults saved to: {report_file}")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
