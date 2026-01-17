#!/usr/bin/env python3
"""
QuickMan MEGA Stress Test
Push harder with controlled high-volume testing
"""

import http.client
import time
import socket
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

def benchmark_throughput(host, port, total_requests, concurrency):
    """Benchmark maximum throughput"""
    print(f"\n{'='*70}")
    print(f"🔥 MAXIMUM THROUGHPUT TEST")
    print(f"{'='*70}")
    print(f"  Target: {total_requests:,} requests with {concurrency} concurrent threads")
    print()

    success = 0
    failed = 0
    latencies = []

    def make_request():
        try:
            start = time.time()
            conn = http.client.HTTPConnection(host, port, timeout=5)
            conn.request("GET", "/benchmark")
            resp = conn.getresponse()
            resp.read()
            conn.close()
            latency = (time.time() - start) * 1000
            return True, latency
        except Exception as e:
            return False, 0

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request) for _ in range(total_requests)]

        for future in as_completed(futures):
            result, latency = future.result()
            if result:
                success += 1
                latencies.append(latency)
            else:
                failed += 1

    elapsed = time.time() - start_time

    latencies.sort()

    print(f"  ✓ Completed in {elapsed:.2f}s")
    print(f"  Total Requests:    {success + failed:,}")
    print(f"  Successful:        {success:,}")
    print(f"  Failed:            {failed:,}")
    print(f"  Success Rate:      {success/(success+failed)*100:.2f}%")
    print(f"  🚀 Throughput:     {success/elapsed:,.2f} req/s")
    print(f"  Avg Latency:       {sum(latencies)/len(latencies):.2f} ms")
    print(f"  Min Latency:       {min(latencies):.2f} ms")
    print(f"  Max Latency:       {max(latencies):.2f} ms")
    print(f"  P50 Latency:       {latencies[len(latencies)//2]:.2f} ms")
    print(f"  P95 Latency:       {latencies[int(len(latencies)*0.95)]:.2f} ms")
    print(f"  P99 Latency:       {latencies[int(len(latencies)*0.99)]:.2f} ms")

    return success, failed, elapsed

def sustained_load_test(host, port, duration, concurrency):
    """Sustained load over time"""
    print(f"\n{'='*70}")
    print(f"⏱️  SUSTAINED LOAD TEST")
    print(f"{'='*70}")
    print(f"  Duration: {duration}s with {concurrency} concurrent threads")
    print()

    success = 0
    failed = 0
    start_time = time.time()

    def make_request():
        try:
            conn = http.client.HTTPConnection(host, port, timeout=3)
            conn.request("GET", "/benchmark")
            resp = conn.getresponse()
            resp.read()
            conn.close()
            return True
        except:
            return False

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []

        while time.time() - start_time < duration:
            future = executor.submit(make_request)
            futures.append(future)

        for future in as_completed(futures):
            if future.result():
                success += 1
            else:
                failed += 1

    elapsed = time.time() - start_time

    print(f"  ✓ Test completed")
    print(f"  Total Requests:    {success + failed:,}")
    print(f"  Successful:        {success:,}")
    print(f"  Failed:            {failed:,}")
    print(f"  Success Rate:      {success/(success+failed)*100:.2f}%")
    print(f"  ⚡ Throughput:     {success/elapsed:,.2f} req/s")

    return success, failed, elapsed

def concurrent_connections_test(host, port, max_concurrent):
    """Test with increasing concurrent connections"""
    print(f"\n{'='*70}")
    print(f"📈 CONCURRENT CONNECTIONS SCALE TEST")
    print(f"{'='*70}")
    print()

    levels = [50, 100, 200, 500]
    requests_per_level = 5000

    results = []

    for level in levels:
        if level > max_concurrent:
            break

        print(f"  Testing with {level} concurrent connections...")

        success = 0
        start = time.time()

        def make_request():
            try:
                conn = http.client.HTTPConnection(host, port, timeout=5)
                conn.request("GET", "/benchmark")
                resp = conn.getresponse()
                resp.read()
                conn.close()
                return True
            except:
                return False

        with ThreadPoolExecutor(max_workers=level) as executor:
            futures = [executor.submit(make_request) for _ in range(requests_per_level)]
            for future in as_completed(futures):
                if future.result():
                    success += 1

        elapsed = time.time() - start
        throughput = success / elapsed

        print(f"    ✓ {throughput:,.2f} req/s ({success:,}/{requests_per_level:,} success)")
        results.append((level, throughput, success))

    print()
    print("  Scale Results:")
    for level, throughput, success in results:
        print(f"    {level:3d} concurrent: {throughput:>10,.2f} req/s")

    return results

def main():
    host = "localhost"
    port = 8001

    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║          QUICKMAN MEGA STRESS TEST SUITE                     ║")
    print("║          💪 HIGH-VOLUME PERFORMANCE TESTING 💪                ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()

    # Check server
    try:
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/status")
        resp = conn.getresponse()
        resp.read()
        conn.close()
        print(f"✓ Server is running on port {port}\n")
    except Exception as e:
        print(f"✗ Server not available: {e}")
        return 1

    # Test 1: Throughput test with 20K requests, 200 concurrent
    r1_success, r1_failed, r1_time = benchmark_throughput(host, port, 20000, 200)
    time.sleep(2)

    # Test 2: Sustained load for 15 seconds, 150 concurrent
    r2_success, r2_failed, r2_time = sustained_load_test(host, port, 15, 150)
    time.sleep(2)

    # Test 3: Scale test
    scale_results = concurrent_connections_test(host, port, 500)

    # Summary
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║                    MEGA TEST SUMMARY                          ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    print(f"  Test 1 - Throughput:      {r1_success/r1_time:,.2f} req/s")
    print(f"  Test 2 - Sustained:       {r2_success/r2_time:,.2f} req/s")

    if scale_results:
        peak_throughput = max(r[1] for r in scale_results)
        peak_level = [r[0] for r in scale_results if r[1] == peak_throughput][0]
        print(f"  Test 3 - Peak:            {peak_throughput:,.2f} req/s @ {peak_level} concurrent")

    total_requests = r1_success + r1_failed + r2_success + r2_failed
    if scale_results:
        total_requests += sum(r[2] for r in scale_results)

    print(f"\n  💥 TOTAL REQUESTS:        {total_requests:,}")
    print()

    # Final check
    print("Final server check...")
    try:
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/status")
        resp = conn.getresponse()
        data = resp.read()
        conn.close()

        if resp.status == 200:
            print("✓ 🏆 SERVER IS STILL RUNNING STRONG!")
            print(f"   After {total_requests:,} requests, server is healthy and responsive")
        else:
            print(f"⚠  Server status: {resp.status}")
    except Exception as e:
        print(f"✗ Server unresponsive: {e}")

    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
