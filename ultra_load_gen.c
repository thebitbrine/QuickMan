/*
 * Ultra Fast Load Generator for QuickMan
 * Generate millions of requests per second using raw sockets
 * Multi-threaded, optimized for maximum throughput
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <errno.h>
#include <signal.h>
#include <sys/time.h>

#define MAX_THREADS 1000
#define BUFFER_SIZE 4096

typedef struct {
    char *host;
    int port;
    int requests_per_thread;
    int thread_id;
    volatile int *total_requests;
    volatile int *total_errors;
    volatile int *running;
    pthread_mutex_t *mutex;
} ThreadData;

typedef struct {
    long long total_requests;
    long long total_errors;
    double duration_seconds;
    double requests_per_second;
} TestResult;

volatile int g_running = 1;

void signal_handler(int sig) {
    printf("\nStopping load generator...\n");
    g_running = 0;
}

double get_time() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec / 1000000.0;
}

void* worker_thread(void* arg) {
    ThreadData *data = (ThreadData*)arg;
    int successful = 0;
    int failed = 0;
    char request[512];
    char buffer[BUFFER_SIZE];

    // Prepare HTTP request
    snprintf(request, sizeof(request),
        "GET /benchmark HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Connection: close\r\n"
        "\r\n",
        data->host
    );

    int request_len = strlen(request);

    // Fire requests
    for (int i = 0; i < data->requests_per_thread && *data->running; i++) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) {
            failed++;
            continue;
        }

        // Set timeout
        struct timeval timeout;
        timeout.tv_sec = 1;
        timeout.tv_usec = 0;
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_port = htons(data->port);
        inet_pton(AF_INET, data->host, &addr.sin_addr);

        // Connect
        if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
            failed++;
            close(sock);
            continue;
        }

        // Send request
        if (send(sock, request, request_len, 0) < 0) {
            failed++;
            close(sock);
            continue;
        }

        // Receive response
        int bytes = recv(sock, buffer, sizeof(buffer) - 1, 0);
        if (bytes > 0) {
            successful++;
        } else {
            failed++;
        }

        close(sock);
    }

    // Update counters
    pthread_mutex_lock(data->mutex);
    *data->total_requests += successful;
    *data->total_errors += failed;
    pthread_mutex_unlock(data->mutex);

    return NULL;
}

void* connection_flooder(void* arg) {
    ThreadData *data = (ThreadData*)arg;
    int count = 0;

    while (*data->running && count < data->requests_per_thread) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) continue;

        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_port = htons(data->port);
        inet_pton(AF_INET, data->host, &addr.sin_addr);

        // Just connect and disconnect rapidly
        if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) == 0) {
            count++;
        }

        close(sock);
    }

    pthread_mutex_lock(data->mutex);
    *data->total_requests += count;
    pthread_mutex_unlock(data->mutex);

    return NULL;
}

void* pipeline_attack(void* arg) {
    ThreadData *data = (ThreadData*)arg;
    int successful = 0;
    int failed = 0;

    // Send multiple pipelined requests in one connection
    char pipelined[10240];
    int offset = 0;

    for (int i = 0; i < 100; i++) {
        offset += snprintf(pipelined + offset, sizeof(pipelined) - offset,
            "GET /benchmark HTTP/1.1\r\n"
            "Host: %s\r\n"
            "\r\n",
            data->host
        );
    }

    for (int i = 0; i < data->requests_per_thread / 100 && *data->running; i++) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) {
            failed += 100;
            continue;
        }

        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_port = htons(data->port);
        inet_pton(AF_INET, data->host, &addr.sin_addr);

        if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
            failed += 100;
            close(sock);
            continue;
        }

        if (send(sock, pipelined, offset, 0) > 0) {
            successful += 100;
        } else {
            failed += 100;
        }

        close(sock);
    }

    pthread_mutex_lock(data->mutex);
    *data->total_requests += successful;
    *data->total_errors += failed;
    pthread_mutex_unlock(data->mutex);

    return NULL;
}

TestResult run_load_test(char *host, int port, int total_requests, int num_threads,
                         void* (*worker)(void*), const char *test_name) {
    printf("\n╔══════════════════════════════════════════════════════════╗\n");
    printf("║ %-56s ║\n", test_name);
    printf("╚══════════════════════════════════════════════════════════╝\n");
    printf("  Threads:        %d\n", num_threads);
    printf("  Target Requests: %d\n", total_requests);
    printf("  Starting...\n\n");

    pthread_t threads[MAX_THREADS];
    ThreadData thread_data[MAX_THREADS];
    volatile int total_done = 0;
    volatile int total_err = 0;
    pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;

    int requests_per_thread = total_requests / num_threads;
    double start_time = get_time();

    // Launch threads
    for (int i = 0; i < num_threads; i++) {
        thread_data[i].host = host;
        thread_data[i].port = port;
        thread_data[i].requests_per_thread = requests_per_thread;
        thread_data[i].thread_id = i;
        thread_data[i].total_requests = &total_done;
        thread_data[i].total_errors = &total_err;
        thread_data[i].running = &g_running;
        thread_data[i].mutex = &mutex;

        if (pthread_create(&threads[i], NULL, worker, &thread_data[i]) != 0) {
            fprintf(stderr, "Failed to create thread %d\n", i);
        }
    }

    // Progress monitoring
    int last_count = 0;
    while (g_running) {
        sleep(1);
        int current = total_done;
        int rate = current - last_count;
        last_count = current;

        printf("\r  Progress: %d requests | %d req/s | %d errors     ",
               current, rate, (int)total_err);
        fflush(stdout);

        // Check if all done
        int all_done = 1;
        for (int i = 0; i < num_threads; i++) {
            if (pthread_tryjoin_np(threads[i], NULL) != 0) {
                all_done = 0;
            }
        }

        if (all_done) break;
    }

    // Wait for remaining threads
    for (int i = 0; i < num_threads; i++) {
        pthread_join(threads[i], NULL);
    }

    double duration = get_time() - start_time;

    printf("\n\n  Results:\n");
    printf("    Completed:   %d\n", (int)total_done);
    printf("    Errors:      %d\n", (int)total_err);
    printf("    Duration:    %.2f seconds\n", duration);
    printf("    Throughput:  %.2f req/s\n", total_done / duration);
    printf("    Success Rate: %.2f%%\n", (total_done * 100.0) / (total_done + total_err));

    TestResult result = {
        .total_requests = total_done,
        .total_errors = total_err,
        .duration_seconds = duration,
        .requests_per_second = total_done / duration
    };

    return result;
}

int main(int argc, char *argv[]) {
    char *host = "127.0.0.1";
    int port = 8001;

    if (argc > 1) {
        port = atoi(argv[1]);
    }

    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║        ULTRA LOAD GENERATOR - QuickMan Stress Test          ║\n");
    printf("║        ⚡ Multi-threaded C-based Load Generator ⚡          ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");
    printf("Target Server: %s:%d\n", host, port);
    printf("\n");

    // Test 1: Warm up
    printf("Warming up...\n");
    run_load_test(host, port, 1000, 10, worker_thread, "WARMUP");

    sleep(2);

    // Test 2: Normal Load (10K requests, 100 threads)
    TestResult r1 = run_load_test(host, port, 10000, 100, worker_thread,
                                   "TEST 1: Normal Load (10K req, 100 threads)");

    sleep(2);

    // Test 3: High Load (50K requests, 200 threads)
    TestResult r2 = run_load_test(host, port, 50000, 200, worker_thread,
                                   "TEST 2: High Load (50K req, 200 threads)");

    sleep(2);

    // Test 4: Extreme Load (100K requests, 500 threads)
    TestResult r3 = run_load_test(host, port, 100000, 500, worker_thread,
                                   "TEST 3: Extreme Load (100K req, 500 threads)");

    sleep(2);

    // Test 5: Connection Flood
    TestResult r4 = run_load_test(host, port, 10000, 100, connection_flooder,
                                   "TEST 4: Connection Flood (10K, 100 threads)");

    sleep(2);

    // Test 6: Pipeline Attack
    TestResult r5 = run_load_test(host, port, 50000, 50, pipeline_attack,
                                   "TEST 5: HTTP Pipelining (50K req, 50 threads)");

    // Summary
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║                    SUMMARY RESULTS                           ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");
    printf("  Test 1 (Normal):      %.2f req/s\n", r1.requests_per_second);
    printf("  Test 2 (High):        %.2f req/s\n", r2.requests_per_second);
    printf("  Test 3 (Extreme):     %.2f req/s\n", r3.requests_per_second);
    printf("  Test 4 (Flood):       %.2f req/s\n", r4.requests_per_second);
    printf("  Test 5 (Pipeline):    %.2f req/s\n", r5.requests_per_second);
    printf("\n");
    printf("  Peak Throughput:      %.2f req/s\n",
           r1.requests_per_second > r2.requests_per_second ?
           (r1.requests_per_second > r3.requests_per_second ? r1.requests_per_second : r3.requests_per_second) :
           (r2.requests_per_second > r3.requests_per_second ? r2.requests_per_second : r3.requests_per_second));
    printf("\n");

    // Check server
    printf("Checking if server is still alive...\n");
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, host, &addr.sin_addr);

    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) == 0) {
        printf("✓ SERVER SURVIVED!\n");
        close(sock);
    } else {
        printf("✗ SERVER DOWN!\n");
    }

    printf("\n");
    return 0;
}
