#!/usr/bin/env python3
"""
QuickMan EXTREME Stress Test - AUTO RUN VERSION
Push server to absolute breaking point with coordinated attacks
"""

import http.client
import socket
import time
import random
import string
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager, cpu_count
import sys

# Quick test version - reduced for faster execution
TEST_DURATION = 10  # seconds per attack

class ExtremeTester:
    """Extreme HTTP stress testing"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.results_queue = Manager().Queue()
        self.stop_flag = Manager().Value('i', 0)

    def rapid_fire_requests(self, endpoint: str, duration_seconds: int, process_id: int):
        """Fire requests as fast as possible"""
        results = []
        errors = {}
        start_time = time.time()

        while time.time() - start_time < duration_seconds and not self.stop_flag.value:
            try:
                conn = http.client.HTTPConnection(self.host, self.port, timeout=1)
                req_start = time.time()
                conn.request("GET", endpoint)
                response = conn.getresponse()
                response.read()
                latency = (time.time() - req_start) * 1000
                conn.close()

                results.append({'success': True, 'latency_ms': latency, 'status': response.status})
            except Exception as e:
                error_type = type(e).__name__
                errors[error_type] = errors.get(error_type, 0) + 1
                results.append({'success': False, 'error': error_type})

        self.results_queue.put({'process_id': process_id, 'results': results, 'errors': errors})

    def connection_flood(self, duration_seconds: int, process_id: int):
        """Rapidly open/close connections"""
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

        self.results_queue.put({'process_id': process_id, 'connection_flood_count': count, 'errors': errors})

    def malformed_request_attack(self, duration_seconds: int, process_id: int):
        """Send malformed and malicious requests"""
        attack_patterns = [
            b"GET /../../../etc/passwd HTTP/1.1\r\nHost: test\r\n\r\n",
            b"GET /" + b"A" * 10000 + b" HTTP/1.1\r\nHost: test\r\n\r\n",
            b"GET / HTTP/99.99\r\nHost: test\r\n\r\n",
            b"GET /\x00\x00\x00 HTTP/1.1\r\nHost: test\r\n\r\n",
            b"GET / HTTP/1.1\r\nHost: test\r\nX-Long: " + b"X" * 5000 + b"\r\n\r\n",
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
                try:
                    sock.recv(1024)
                except:
                    pass
                sock.close()
                count += 1
            except Exception as e:
                error_type = type(e).__name__
                errors[error_type] = errors.get(error_type, 0) + 1

        self.results_queue.put({'process_id': process_id, 'malformed_count': count, 'errors': errors})

    def url_fuzzing(self, duration_seconds: int, process_id: int):
        """Fuzz URLs with random patterns"""
        count = 0
        errors = {}
        start_time = time.time()

        while time.time() - start_time < duration_seconds and not self.stop_flag.value:
            try:
                length = random.randint(1, 500)
                url = "/" + ''.join(random.choices(string.ascii_letters + string.digits + "/.?=&%", k=length))

                conn = http.client.HTTPConnection(self.host, self.port, timeout=1)
                conn.request("GET", url)
                response = conn.getresponse()
                response.read()
                conn.close()
                count += 1
            except Exception as e:
                error_type = type(e).__name__
                errors[error_type] = errors.get(error_type, 0) + 1

        self.results_queue.put({'process_id': process_id, 'url_fuzz_count': count, 'errors': errors})

    def run_extreme_test(self, test_name: str, test_func, *args):
        """Run extreme test with multiple processes"""
        print(f"\n{'='*70}")
        print(f"⚡ {test_name}")
        print(f"{'='*70}")

        num_processes = cpu_count() * 2
        print(f"Launching {num_processes} attack processes for {TEST_DURATION} seconds...")

        start_time = time.time()

        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [executor.submit(test_func, *args, i) for i in range(num_processes)]
            for future in futures:
                future.result()

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

        return {'test_name': test_name, 'duration': duration, 'processes': num_processes,
                'results': all_results, 'errors': all_errors}


def main():
    C_PORT = 8001

    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║          QUICKMAN EXTREME STRESS TEST SUITE                  ║")
    print("║          ⚠️  MAXIMUM LOAD - PUSH TO BREAKING POINT  ⚠️          ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()

    # Check server
    print(f"Checking server on port {C_PORT}...")
    try:
        conn = http.client.HTTPConnection("localhost", C_PORT, timeout=2)
        conn.request("GET", "/status")
        response = conn.getresponse()
        response.read()
        conn.close()
        print(f"✓ Server is running (status: {response.status})\n")
    except Exception as e:
        print(f"✗ Server not available: {e}")
        return 1

    print(f"CPU cores: {cpu_count()} | Attack processes: {cpu_count() * 2}")
    print(f"Duration per test: {TEST_DURATION} seconds")
    print()

    tester = ExtremeTester("localhost", C_PORT)
    results = {}

    # Test 1: Rapid Fire
    rapid_result = tester.run_extreme_test("TEST 1: RAPID FIRE ASSAULT",
                                           tester.rapid_fire_requests, "/benchmark", TEST_DURATION)

    total_requests = sum(len(r.get('results', [])) for r in rapid_result['results'])
    successful = sum(sum(1 for req in r.get('results', []) if req.get('success'))
                    for r in rapid_result['results'])

    print(f"\n  Total Requests:    {total_requests:,}")
    print(f"  Successful:        {successful:,}")
    print(f"  Failed:            {total_requests - successful:,}")
    print(f"  Duration:          {rapid_result['duration']:.2f}s")
    print(f"  🔥 Throughput:     {total_requests/rapid_result['duration']:,.2f} req/s")
    print(f"  Success Rate:      {successful/total_requests*100:.2f}%")

    if rapid_result['errors']:
        print(f"\n  Errors:")
        for error, count in list(rapid_result['errors'].items())[:3]:
            print(f"    {error}: {count}")

    results['rapid_fire'] = rapid_result
    time.sleep(2)

    # Test 2: Connection Flood
    flood_result = tester.run_extreme_test("TEST 2: CONNECTION FLOOD",
                                          tester.connection_flood, TEST_DURATION)

    total_connections = sum(r.get('connection_flood_count', 0) for r in flood_result['results'])
    print(f"\n  Total Connections: {total_connections:,}")
    print(f"  Duration:          {flood_result['duration']:.2f}s")
    print(f"  🌊 Flood Rate:     {total_connections/flood_result['duration']:,.2f} conn/s")

    if flood_result['errors']:
        print(f"\n  Errors:")
        for error, count in list(flood_result['errors'].items())[:3]:
            print(f"    {error}: {count}")

    results['connection_flood'] = flood_result
    time.sleep(2)

    # Test 3: Malformed Requests
    malformed_result = tester.run_extreme_test("TEST 3: MALFORMED REQUEST ATTACK",
                                              tester.malformed_request_attack, TEST_DURATION)

    total_malformed = sum(r.get('malformed_count', 0) for r in malformed_result['results'])
    print(f"\n  Malformed Requests: {total_malformed:,}")
    print(f"  Duration:           {malformed_result['duration']:.2f}s")
    print(f"  💀 Attack Rate:     {total_malformed/malformed_result['duration']:,.2f} req/s")

    results['malformed_attack'] = malformed_result
    time.sleep(2)

    # Test 4: URL Fuzzing
    fuzz_result = tester.run_extreme_test("TEST 4: URL FUZZING ATTACK",
                                         tester.url_fuzzing, TEST_DURATION)

    total_fuzzes = sum(r.get('url_fuzz_count', 0) for r in fuzz_result['results'])
    print(f"\n  Fuzzed URLs:       {total_fuzzes:,}")
    print(f"  Duration:          {fuzz_result['duration']:.2f}s")
    print(f"  🎲 Fuzz Rate:      {total_fuzzes/fuzz_result['duration']:,.2f} req/s")

    results['url_fuzzing'] = fuzz_result

    # Final summary
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║                    EXTREME TEST SUMMARY                       ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    print(f"  Test 1 (Rapid Fire):      {total_requests/rapid_result['duration']:,.2f} req/s")
    print(f"  Test 2 (Flood):           {total_connections/flood_result['duration']:,.2f} conn/s")
    print(f"  Test 3 (Malformed):       {total_malformed/malformed_result['duration']:,.2f} req/s")
    print(f"  Test 4 (Fuzzing):         {total_fuzzes/fuzz_result['duration']:,.2f} req/s")
    print()

    # Check if server survived
    print("Checking if server survived the attack...")
    try:
        conn = http.client.HTTPConnection("localhost", C_PORT, timeout=2)
        conn.request("GET", "/status")
        response = conn.getresponse()
        response.read()
        conn.close()

        if response.status == 200:
            print("✓ 🎉 SERVER SURVIVED ALL ATTACKS! Still responding normally.")
        else:
            print(f"⚠  Server responding with status {response.status}")
    except Exception as e:
        print(f"✗ 💀 SERVER DOWN! Not responding: {e}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
