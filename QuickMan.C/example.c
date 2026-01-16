#include "quickman.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>

/* Global server instance for signal handling */
QuickManServer *g_server = NULL;

/* Signal handler for graceful shutdown */
void signal_handler(int signum) {
    printf("\nReceived signal %d, shutting down...\n", signum);
    if (g_server) {
        quickman_stop(g_server);
    }
    exit(0);
}

/* Example endpoint: Get status */
void endpoint_status(HttpContext *context) {
    const char *json = "{\"status\":\"running\",\"message\":\"QuickMan C server is operational\"}";
    quickman_respond_json(context, json, HTTP_OK);
    quickman_log("GET /status - 200 OK");
}

/* Example endpoint: Echo request info */
void endpoint_info(HttpContext *context) {
    char response[2048];
    const char *user_agent = quickman_get_header(context->request, "User-Agent");

    snprintf(response, sizeof(response),
        "{"
        "\"method\":\"%s\","
        "\"path\":\"%s\","
        "\"query\":\"%s\","
        "\"user_agent\":\"%s\""
        "}",
        context->request->method == HTTP_GET ? "GET" :
        context->request->method == HTTP_POST ? "POST" :
        context->request->method == HTTP_PUT ? "PUT" :
        context->request->method == HTTP_DELETE ? "DELETE" : "UNKNOWN",
        context->request->path,
        context->request->query_string ? context->request->query_string : "",
        user_agent ? user_agent : "Unknown"
    );

    quickman_respond_json(context, response, HTTP_OK);
    quickman_log("GET /info - 200 OK");
}

/* Example endpoint: Echo query parameters */
void endpoint_echo(HttpContext *context) {
    const char *message = quickman_get_query_param(context->request, "message");

    if (message) {
        char response[1024];
        snprintf(response, sizeof(response),
            "{\"echo\":\"%s\",\"length\":%zu}",
            message, strlen(message));
        quickman_respond_json(context, response, HTTP_OK);
        quickman_log("GET /echo?message=%s - 200 OK", message);
    } else {
        quickman_respond_status(context, HTTP_BAD_REQUEST,
            "Missing 'message' query parameter");
        quickman_log("GET /echo - 400 Bad Request");
    }
}

/* Example endpoint: Return HTML page */
void endpoint_home(HttpContext *context) {
    const char *html =
        "<!DOCTYPE html>"
        "<html>"
        "<head><title>QuickMan C Server</title></head>"
        "<body>"
        "<h1>Welcome to QuickMan C Server!</h1>"
        "<p>This is a high-performance HTTP server written in C.</p>"
        "<h2>Available Endpoints:</h2>"
        "<ul>"
        "<li><a href='/status'>/status</a> - Server status</li>"
        "<li><a href='/info'>/info</a> - Request information</li>"
        "<li><a href='/echo?message=Hello'>/echo?message=Hello</a> - Echo message</li>"
        "<li><a href='/data'>/data</a> - Sample data</li>"
        "<li><a href='/hello'>/hello</a> - Plain text response</li>"
        "</ul>"
        "</body>"
        "</html>";

    quickman_respond_html(context, html, HTTP_OK);
    quickman_log("GET / - 200 OK");
}

/* Example endpoint: Return sample data */
void endpoint_data(HttpContext *context) {
    const char *json =
        "{"
        "\"users\":["
        "{\"id\":1,\"name\":\"Alice\",\"email\":\"alice@example.com\"},"
        "{\"id\":2,\"name\":\"Bob\",\"email\":\"bob@example.com\"},"
        "{\"id\":3,\"name\":\"Charlie\",\"email\":\"charlie@example.com\"}"
        "],"
        "\"total\":3"
        "}";

    quickman_respond_json(context, json, HTTP_OK);
    quickman_log("GET /data - 200 OK");
}

/* Example endpoint: Plain text response */
void endpoint_hello(HttpContext *context) {
    const char *name = quickman_get_query_param(context->request, "name");

    if (name) {
        char response[256];
        snprintf(response, sizeof(response), "Hello, %s! Welcome to QuickMan C Server.", name);
        quickman_respond_text(context, response, HTTP_OK);
        quickman_log("GET /hello?name=%s - 200 OK", name);
    } else {
        quickman_respond_text(context, "Hello, World! Welcome to QuickMan C Server.", HTTP_OK);
        quickman_log("GET /hello - 200 OK");
    }
}

/* Example endpoint: POST handler with body parsing */
void endpoint_post(HttpContext *context) {
    if (context->request->method != HTTP_POST) {
        quickman_respond_status(context, HTTP_BAD_REQUEST, "POST method required");
        return;
    }

    if (context->request->body) {
        char response[1024];
        snprintf(response, sizeof(response),
            "{\"received\":true,\"body_length\":%zu,\"body\":\"%s\"}",
            context->request->body_length,
            context->request->body);

        quickman_respond_json(context, response, HTTP_OK);
        quickman_log("POST /post - 200 OK (body: %zu bytes)", context->request->body_length);
    } else {
        quickman_respond_status(context, HTTP_BAD_REQUEST, "No body provided");
        quickman_log("POST /post - 400 Bad Request");
    }
}

/* Example endpoint: Custom headers */
void endpoint_headers(HttpContext *context) {
    quickman_add_header(context->response, "X-Custom-Header", "QuickMan");
    quickman_add_header(context->response, "X-Powered-By", "C Language");
    quickman_add_header(context->response, "X-Version", "1.0");

    const char *json = "{\"message\":\"Check the response headers!\"}";
    quickman_respond_json(context, json, HTTP_OK);
    quickman_log("GET /headers - 200 OK");
}

/* Example endpoint: Benchmark endpoint */
void endpoint_benchmark(HttpContext *context) {
    const char *json = "{\"benchmark\":true}";
    quickman_respond_json(context, json, HTTP_OK);
}

/* Main function */
int main(int argc, char *argv[]) {
    /* Setup signal handlers */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    /* Parse command line arguments */
    int port = 1999;
    int max_connections = 20;

    if (argc > 1) {
        port = atoi(argv[1]);
        if (port <= 0 || port > 65535) {
            printf("Invalid port number. Using default: 1999\n");
            port = 1999;
        }
    }

    if (argc > 2) {
        max_connections = atoi(argv[2]);
        if (max_connections <= 0) {
            printf("Invalid max connections. Using default: 20\n");
            max_connections = 20;
        }
    }

    /* Create server */
    g_server = quickman_create();
    if (!g_server) {
        fprintf(stderr, "Failed to create server\n");
        return 1;
    }

    /* Define endpoints */
    Endpoint endpoints[] = {
        { "", endpoint_home },                  /* Root endpoint */
        { "status", endpoint_status },
        { "info", endpoint_info },
        { "echo", endpoint_echo },
        { "data", endpoint_data },
        { "hello", endpoint_hello },
        { "post", endpoint_post },
        { "headers", endpoint_headers },
        { "benchmark", endpoint_benchmark }
    };

    int endpoint_count = sizeof(endpoints) / sizeof(endpoints[0]);

    /* Print startup information */
    printf("\n");
    printf("╔════════════════════════════════════════════════════════╗\n");
    printf("║          QuickMan C - HTTP Server v1.0                ║\n");
    printf("╚════════════════════════════════════════════════════════╝\n");
    printf("\n");
    printf("Configuration:\n");
    printf("  Port:            %d\n", port);
    printf("  Max Connections: %d\n", max_connections);
    printf("  Endpoints:       %d\n", endpoint_count);
    printf("  Local IP:        %s\n", quickman_get_local_ip());
    printf("\n");
    printf("Available endpoints:\n");
    printf("  http://localhost:%d/\n", port);
    printf("  http://localhost:%d/status\n", port);
    printf("  http://localhost:%d/info\n", port);
    printf("  http://localhost:%d/echo?message=test\n", port);
    printf("  http://localhost:%d/data\n", port);
    printf("  http://localhost:%d/hello?name=YourName\n", port);
    printf("  http://localhost:%d/headers\n", port);
    printf("  http://localhost:%d/benchmark\n", port);
    printf("\n");
    printf("Press Ctrl+C to stop the server\n");
    printf("\n");
    printf("═══════════════════════════════════════════════════════════\n\n");

    /* Start server */
    if (quickman_start(g_server, "0.0.0.0", port, endpoints, endpoint_count, max_connections) < 0) {
        fprintf(stderr, "Failed to start server\n");
        quickman_destroy(g_server);
        return 1;
    }

    /* Cleanup (will only reach here if server stops) */
    quickman_destroy(g_server);

    return 0;
}
