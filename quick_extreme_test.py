#!/usr/bin/env python3
"""
QuickMan Quick Extreme Test - Lightweight version
"""

import http.client
import socket
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor
import sys

def rapid_fire_test(host, port, duration):
    """Fire requests as fast as possible"""
    print(f"\n{'='*70}")
    print(f"⚡ RAPID FIRE ASSAULT")
    print(f"{'='*70}")

    success = 0
    failed = 0
    start = time.time()

    def make_request():
        nonlocal success, failed
        try:
            conn = http.client.HTTPConnection(host, port, timeout=2)
            conn.request("GET", "/benchmark")
            resp = conn.getresponse()
            resp.read()
            conn.close()
            success += 1
        except:
            failed += 1

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        while time.time() - start < duration:
            futures.append(executor.submit(make_request))

    elapsed = time.time() - start
    total = success + failed

    print(f"\n  Total Requests:    {total:,}")
    print(f"  Successful:        {success:,}")
    print(f"  Failed:            {failed:,}")
    print(f"  Duration:          {elapsed:.2f}s")
    print(f"  🔥 Throughput:     {success/elapsed:,.2f} req/s")
    print(f"  Success Rate:      {success/total*100:.2f}%")

    return success, failed, elapsed

def connection_flood_test(host, port, duration):
    """Rapidly open/close connections"""
    print(f"\n{'='*70}")
    print(f"🌊 CONNECTION FLOOD")
    print(f"{'='*70}")

    count = 0
    errors = 0
    start = time.time()

    while time.time() - start < duration:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect((host, port))
            sock.close()
            count += 1
        except:
            errors += 1

    elapsed = time.time() - start

    print(f"\n  Connections:       {count:,}")
    print(f"  Errors:            {errors:,}")
    print(f"  Duration:          {elapsed:.2f}s")
    print(f"  🌊 Rate:           {count/elapsed:,.2f} conn/s")

    return count, errors, elapsed

def malformed_attack_test(host, port, duration):
    """Send malformed requests"""
    print(f"\n{'='*70}")
    print(f"💀 MALFORMED REQUEST ATTACK")
    print(f"{'='*70}")

    patterns = [
        b"GET /../../../etc/passwd HTTP/1.1\r\nHost: test\r\n\r\n",
        b"GET /" + b"A" * 5000 + b" HTTP/1.1\r\nHost: test\r\n\r\n",
        b"GET / HTTP/99.99\r\nHost: test\r\n\r\n",
        b"GET /\x00\x00 HTTP/1.1\r\nHost: test\r\n\r\n",
    ]

    count = 0
    start = time.time()

    while time.time() - start < duration:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect((host, port))
            sock.send(random.choice(patterns))
            try:
                sock.recv(1024)
            except:
                pass
            sock.close()
            count += 1
        except:
            pass

    elapsed = time.time() - start

    print(f"\n  Malformed Requests: {count:,}")
    print(f"  Duration:           {elapsed:.2f}s")
    print(f"  💀 Attack Rate:     {count/elapsed:,.2f} req/s")

    return count, elapsed

def url_fuzzing_test(host, port, duration):
    """Send random URLs"""
    print(f"\n{'='*70}")
    print(f"🎲 URL FUZZING")
    print(f"{'='*70}")

    count = 0
    start = time.time()

    while time.time() - start < duration:
        try:
            length = random.randint(10, 200)
            url = "/" + ''.join(random.choices(string.ascii_letters + "/.?=&", k=length))

            conn = http.client.HTTPConnection(host, port, timeout=1)
            conn.request("GET", url)
            resp = conn.getresponse()
            resp.read()
            conn.close()
            count += 1
        except:
            pass

    elapsed = time.time() - start

    print(f"\n  Fuzzed URLs:       {count:,}")
    print(f"  Duration:          {elapsed:.2f}s")
    print(f"  🎲 Fuzz Rate:      {count/elapsed:,.2f} req/s")

    return count, elapsed

def main():
    host = "localhost"
    port = 8001
    duration = 8  # seconds per test

    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║          QUICKMAN EXTREME STRESS TEST SUITE                  ║")
    print("║          ⚠️  MAXIMUM LOAD - PUSH TO BREAKING POINT  ⚠️          ║")
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

    print(f"Test duration: {duration} seconds per test")
    print(f"Concurrency: 100 threads for rapid fire")
    print()

    # Run tests
    r1_success, r1_failed, r1_time = rapid_fire_test(host, port, duration)
    time.sleep(1)

    r2_count, r2_errors, r2_time = connection_flood_test(host, port, duration)
    time.sleep(1)

    r3_count, r3_time = malformed_attack_test(host, port, duration)
    time.sleep(1)

    r4_count, r4_time = url_fuzzing_test(host, port, duration)

    # Summary
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║                    EXTREME TEST SUMMARY                       ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    print(f"  Rapid Fire:           {r1_success/r1_time:,.2f} req/s ({r1_success:,} requests)")
    print(f"  Connection Flood:     {r2_count/r2_time:,.2f} conn/s ({r2_count:,} connections)")
    print(f"  Malformed Attack:     {r3_count/r3_time:,.2f} req/s ({r3_count:,} malformed)")
    print(f"  URL Fuzzing:          {r4_count/r4_time:,.2f} req/s ({r4_count:,} fuzzed)")
    print()

    total_attacks = r1_success + r1_failed + r2_count + r3_count + r4_count
    print(f"  💥 TOTAL ATTACKS:     {total_attacks:,}")
    print()

    # Check if server survived
    print("Checking if server survived...")
    try:
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/status")
        resp = conn.getresponse()
        data = resp.read()
        conn.close()

        if resp.status == 200:
            print("✓ 🎉 SERVER SURVIVED! Still responding normally.")
            print(f"   Response: {data.decode()}")
        else:
            print(f"⚠  Server responding with status {resp.status}")
    except Exception as e:
        print(f"✗ 💀 SERVER DOWN! Not responding: {e}")

    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
