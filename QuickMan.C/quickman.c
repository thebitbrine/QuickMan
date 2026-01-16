#define _POSIX_C_SOURCE 200809L
#include "quickman.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <semaphore.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <stdarg.h>
#include <errno.h>
#include <sys/stat.h>
#include <fcntl.h>

#define BUFFER_SIZE 16384
#define MAX_HEADER_SIZE 8192
#define MAX_HEADERS 64
#define DEFAULT_PORT 1999
#define DEFAULT_MAX_CONNECTIONS 20

/* Internal structures */
typedef struct {
    QuickManServer *server;
    int client_socket;
} RequestData;

/* Static helper function declarations */
static void* request_handler_thread(void* arg);
static void process_request(QuickManServer *server, int client_socket);
static HttpMethod parse_method(const char *method_str);
static char* parse_path(const char *raw_url, char **query_string);
static HttpRequest* parse_http_request(int client_socket);
static void free_request(HttpRequest *req);
static void free_response(HttpResponse *resp);
static void send_response_headers(HttpResponse *response);
static void send_response_body(int client_socket, const char *body, size_t length);
static char* url_decode(const char *str);
static const char* get_status_text(HttpStatus status);
static const char* get_mime_type(const char *filepath);

/* Logging function */
void quickman_log(const char *format, ...) {
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", t);

    printf("[%s] ", timestamp);

    va_list args;
    va_start(args, format);
    vprintf(format, args);
    va_end(args);

    printf("\n");
    fflush(stdout);
}

/* Create a new QuickMan server instance */
QuickManServer* quickman_create(void) {
    QuickManServer *server = calloc(1, sizeof(QuickManServer));
    if (!server) {
        quickman_log("ERROR: Failed to allocate server structure");
        return NULL;
    }

    server->server_socket = -1;
    server->running = 0;
    server->semaphore = malloc(sizeof(sem_t));

    if (!server->semaphore) {
        free(server);
        return NULL;
    }

    return server;
}

/* Start server with custom configuration */
int quickman_start(QuickManServer *server, const char *address, int port,
                   Endpoint *endpoints, int endpoint_count, int max_connections) {
    if (!server || !endpoints || endpoint_count <= 0) {
        quickman_log("ERROR: Invalid server configuration");
        return -1;
    }

    /* Configure server */
    server->config.address = strdup(address ? address : "0.0.0.0");
    server->config.port = port > 0 ? port : DEFAULT_PORT;
    server->config.max_connections = max_connections > 0 ? max_connections : DEFAULT_MAX_CONNECTIONS;
    server->config.endpoints = endpoints;
    server->config.endpoint_count = endpoint_count;

    /* Initialize semaphore */
    if (sem_init((sem_t*)server->semaphore, 0, server->config.max_connections) != 0) {
        quickman_log("ERROR: Failed to initialize semaphore");
        return -1;
    }

    /* Create socket */
    server->server_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server->server_socket < 0) {
        quickman_log("ERROR: Failed to create socket: %s", strerror(errno));
        return -1;
    }

    /* Set socket options */
    int opt = 1;
    if (setsockopt(server->server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        quickman_log("WARNING: Failed to set SO_REUSEADDR");
    }

    /* Bind socket */
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(server->config.port);

    if (inet_pton(AF_INET, server->config.address, &addr.sin_addr) <= 0) {
        quickman_log("ERROR: Invalid address: %s", server->config.address);
        close(server->server_socket);
        return -1;
    }

    if (bind(server->server_socket, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        quickman_log("ERROR: Failed to bind to %s:%d: %s",
                    server->config.address, server->config.port, strerror(errno));
        close(server->server_socket);
        return -1;
    }

    /* Listen */
    if (listen(server->server_socket, 128) < 0) {
        quickman_log("ERROR: Failed to listen: %s", strerror(errno));
        close(server->server_socket);
        return -1;
    }

    server->running = 1;
    quickman_log("QuickMan server started on %s:%d (max connections: %d)",
                server->config.address, server->config.port, server->config.max_connections);

    /* Main accept loop */
    while (server->running) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);

        int client_socket = accept(server->server_socket,
                                   (struct sockaddr*)&client_addr, &client_len);

        if (client_socket < 0) {
            if (server->running) {
                quickman_log("WARNING: Accept failed: %s", strerror(errno));
            }
            continue;
        }

        /* Wait for available connection slot */
        sem_wait((sem_t*)server->semaphore);

        /* Create request data */
        RequestData *req_data = malloc(sizeof(RequestData));
        if (!req_data) {
            close(client_socket);
            sem_post((sem_t*)server->semaphore);
            continue;
        }

        req_data->server = server;
        req_data->client_socket = client_socket;

        /* Spawn thread to handle request */
        pthread_t thread;
        pthread_attr_t attr;
        pthread_attr_init(&attr);
        pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);

        if (pthread_create(&thread, &attr, request_handler_thread, req_data) != 0) {
            quickman_log("ERROR: Failed to create thread");
            free(req_data);
            close(client_socket);
            sem_post((sem_t*)server->semaphore);
        }

        pthread_attr_destroy(&attr);
    }

    return 0;
}

/* Start server with default configuration (localhost:1999) */
int quickman_start_simple(QuickManServer *server, Endpoint *endpoints, int endpoint_count) {
    return quickman_start(server, "127.0.0.1", DEFAULT_PORT, endpoints, endpoint_count, DEFAULT_MAX_CONNECTIONS);
}

/* Request handler thread */
static void* request_handler_thread(void* arg) {
    RequestData *req_data = (RequestData*)arg;
    process_request(req_data->server, req_data->client_socket);

    /* Release semaphore */
    sem_post((sem_t*)req_data->server->semaphore);

    /* Cleanup */
    close(req_data->client_socket);
    free(req_data);

    return NULL;
}

/* Process incoming request */
static void process_request(QuickManServer *server, int client_socket) {
    HttpRequest *request = parse_http_request(client_socket);

    if (!request) {
        const char *error_resp = "HTTP/1.1 400 Bad Request\r\n"
                                "Content-Length: 0\r\n"
                                "Connection: close\r\n\r\n";
        send(client_socket, error_resp, strlen(error_resp), 0);
        return;
    }

    /* Create response */
    HttpResponse *response = calloc(1, sizeof(HttpResponse));
    response->status_code = HTTP_OK;
    response->status_description = strdup("OK");
    response->content_type = strdup("application/json");
    response->client_socket = client_socket;
    response->headers = calloc(MAX_HEADERS, sizeof(char*));
    response->header_count = 0;

    /* Add server header */
    quickman_add_header(response, "Server", "QuickMan/1.0 (C)");

    /* Create context */
    HttpContext context = {
        .request = request,
        .response = response
    };

    /* Find and execute endpoint */
    int found = 0;
    for (int i = 0; i < server->config.endpoint_count; i++) {
        if (strcmp(server->config.endpoints[i].path, request->path) == 0) {
            found = 1;

            /* Execute handler */
            server->config.endpoints[i].handler(&context);
            break;
        }
    }

    if (!found) {
        quickman_respond_status(&context, HTTP_NOT_FOUND, "Endpoint not found");
    }

    /* Cleanup */
    free_request(request);
    free_response(response);
}

/* Parse HTTP method */
static HttpMethod parse_method(const char *method_str) {
    if (strcmp(method_str, "GET") == 0) return HTTP_GET;
    if (strcmp(method_str, "POST") == 0) return HTTP_POST;
    if (strcmp(method_str, "PUT") == 0) return HTTP_PUT;
    if (strcmp(method_str, "DELETE") == 0) return HTTP_DELETE;
    if (strcmp(method_str, "HEAD") == 0) return HTTP_HEAD;
    if (strcmp(method_str, "OPTIONS") == 0) return HTTP_OPTIONS;
    if (strcmp(method_str, "PATCH") == 0) return HTTP_PATCH;
    return HTTP_UNKNOWN;
}

/* Parse path from raw URL */
static char* parse_path(const char *raw_url, char **query_string) {
    char *url_copy = strdup(raw_url);
    char *query_start = strchr(url_copy, '?');

    if (query_start) {
        *query_start = '\0';
        *query_string = strdup(query_start + 1);
    } else {
        *query_string = NULL;
    }

    /* Remove leading slash */
    char *path = url_copy;
    if (path[0] == '/') path++;

    /* Remove trailing slash */
    size_t len = strlen(path);
    if (len > 0 && path[len - 1] == '/') {
        path[len - 1] = '\0';
    }

    char *result = strdup(path);
    free(url_copy);
    return result;
}

/* Parse HTTP request from socket */
static HttpRequest* parse_http_request(int client_socket) {
    char buffer[MAX_HEADER_SIZE];
    ssize_t received = recv(client_socket, buffer, sizeof(buffer) - 1, 0);

    if (received <= 0) {
        return NULL;
    }

    buffer[received] = '\0';

    /* Find end of headers */
    char *body_start = strstr(buffer, "\r\n\r\n");
    if (!body_start) {
        body_start = strstr(buffer, "\n\n");
    }

    HttpRequest *request = calloc(1, sizeof(HttpRequest));
    if (!request) return NULL;

    request->headers = calloc(MAX_HEADERS, sizeof(char*));
    request->header_count = 0;
    request->client_socket = client_socket;

    /* Parse request line */
    char method[16], url[2048], version[16];
    if (sscanf(buffer, "%15s %2047s %15s", method, url, version) != 3) {
        free_request(request);
        return NULL;
    }

    request->method = parse_method(method);
    request->raw_url = strdup(url);
    request->path = parse_path(url, &request->query_string);

    /* Parse headers */
    char *line = strchr(buffer, '\n');
    while (line && request->header_count < MAX_HEADERS) {
        line++;
        if (*line == '\r' || *line == '\n') break;

        char *line_end = strchr(line, '\n');
        if (!line_end) break;

        *line_end = '\0';
        if (line_end > line && *(line_end - 1) == '\r') {
            *(line_end - 1) = '\0';
        }

        request->headers[request->header_count++] = strdup(line);
        line = line_end;
    }

    /* Parse body if present */
    if (body_start) {
        body_start += 4; /* Skip \r\n\r\n */
        size_t header_len = body_start - buffer;
        size_t body_len = received - header_len;

        if (body_len > 0) {
            request->body = malloc(body_len + 1);
            memcpy(request->body, body_start, body_len);
            request->body[body_len] = '\0';
            request->body_length = body_len;
        }
    }

    return request;
}

/* Free request structure */
static void free_request(HttpRequest *req) {
    if (!req) return;

    free(req->path);
    free(req->query_string);
    free(req->raw_url);
    free(req->body);

    for (int i = 0; i < req->header_count; i++) {
        free(req->headers[i]);
    }
    free(req->headers);

    free(req);
}

/* Free response structure */
static void free_response(HttpResponse *resp) {
    if (!resp) return;

    free(resp->status_description);
    free(resp->content_type);

    for (int i = 0; i < resp->header_count; i++) {
        free(resp->headers[i]);
    }
    free(resp->headers);

    free(resp);
}

/* Get status text */
static const char* get_status_text(HttpStatus status) {
    switch (status) {
        case HTTP_OK: return "OK";
        case HTTP_CREATED: return "Created";
        case HTTP_NO_CONTENT: return "No Content";
        case HTTP_BAD_REQUEST: return "Bad Request";
        case HTTP_NOT_FOUND: return "Not Found";
        case HTTP_INTERNAL_ERROR: return "Internal Server Error";
        default: return "Unknown";
    }
}

/* Send response headers */
static void send_response_headers(HttpResponse *response) {
    char header_buffer[MAX_HEADER_SIZE];
    int offset = 0;

    offset += snprintf(header_buffer + offset, sizeof(header_buffer) - offset,
                      "HTTP/1.1 %d %s\r\n", response->status_code,
                      get_status_text(response->status_code));

    offset += snprintf(header_buffer + offset, sizeof(header_buffer) - offset,
                      "Content-Type: %s\r\n", response->content_type);

    /* Add custom headers */
    for (int i = 0; i < response->header_count; i++) {
        offset += snprintf(header_buffer + offset, sizeof(header_buffer) - offset,
                          "%s\r\n", response->headers[i]);
    }

    send(response->client_socket, header_buffer, offset, 0);
}

/* Send response body */
static void send_response_body(int client_socket, const char *body, size_t length) {
    char header[256];
    int header_len = snprintf(header, sizeof(header), "Content-Length: %zu\r\n\r\n", length);

    send(client_socket, header, header_len, 0);

    if (body && length > 0) {
        send(client_socket, body, length, 0);
    }
}

/* Respond with plain text */
void quickman_respond_text(HttpContext *context, const char *text, HttpStatus status) {
    context->response->status_code = status;
    free(context->response->content_type);
    context->response->content_type = strdup("text/plain");

    send_response_headers(context->response);
    send_response_body(context->response->client_socket, text, text ? strlen(text) : 0);
}

/* Respond with JSON */
void quickman_respond_json(HttpContext *context, const char *json, HttpStatus status) {
    context->response->status_code = status;
    free(context->response->content_type);
    context->response->content_type = strdup("application/json");

    send_response_headers(context->response);
    send_response_body(context->response->client_socket, json, json ? strlen(json) : 0);
}

/* Respond with HTML */
void quickman_respond_html(HttpContext *context, const char *html, HttpStatus status) {
    context->response->status_code = status;
    free(context->response->content_type);
    context->response->content_type = strdup("text/html");

    send_response_headers(context->response);
    send_response_body(context->response->client_socket, html, html ? strlen(html) : 0);
}

/* Respond with file */
void quickman_respond_file(HttpContext *context, const char *filepath, HttpStatus status) {
    FILE *file = fopen(filepath, "rb");
    if (!file) {
        quickman_respond_status(context, HTTP_NOT_FOUND, "File not found");
        return;
    }

    /* Get file size */
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    /* Set content type based on file extension */
    const char *mime_type = get_mime_type(filepath);
    free(context->response->content_type);
    context->response->content_type = strdup(mime_type);
    context->response->status_code = status;

    /* Send headers */
    send_response_headers(context->response);

    char header[256];
    int header_len = snprintf(header, sizeof(header), "Content-Length: %ld\r\n\r\n", file_size);
    send(context->response->client_socket, header, header_len, 0);

    /* Send file in chunks */
    char buffer[BUFFER_SIZE];
    size_t bytes_read;
    while ((bytes_read = fread(buffer, 1, sizeof(buffer), file)) > 0) {
        send(context->response->client_socket, buffer, bytes_read, 0);
    }

    fclose(file);
}

/* Respond with stream */
void quickman_respond_stream(HttpContext *context, FILE *stream, HttpStatus status) {
    if (!stream) {
        quickman_respond_status(context, HTTP_INTERNAL_ERROR, "Invalid stream");
        return;
    }

    context->response->status_code = status;
    send_response_headers(context->response);

    /* Note: Content-Length is unknown for streams, use chunked encoding */
    const char *chunked_header = "Transfer-Encoding: chunked\r\n\r\n";
    send(context->response->client_socket, chunked_header, strlen(chunked_header), 0);

    char buffer[BUFFER_SIZE];
    size_t bytes_read;
    while ((bytes_read = fread(buffer, 1, sizeof(buffer), stream)) > 0) {
        char chunk_header[32];
        int chunk_header_len = snprintf(chunk_header, sizeof(chunk_header), "%zx\r\n", bytes_read);
        send(context->response->client_socket, chunk_header, chunk_header_len, 0);
        send(context->response->client_socket, buffer, bytes_read, 0);
        send(context->response->client_socket, "\r\n", 2, 0);
    }

    /* Send final chunk */
    send(context->response->client_socket, "0\r\n\r\n", 5, 0);
}

/* Respond with status code and message */
void quickman_respond_status(HttpContext *context, HttpStatus status, const char *message) {
    context->response->status_code = status;

    char body[1024];
    snprintf(body, sizeof(body), "{\"status\":%d,\"message\":\"%s\"}", status, message);

    send_response_headers(context->response);
    send_response_body(context->response->client_socket, body, strlen(body));
}

/* Add header to response */
void quickman_add_header(HttpResponse *response, const char *name, const char *value) {
    if (response->header_count >= MAX_HEADERS) return;

    char header[512];
    snprintf(header, sizeof(header), "%s: %s", name, value);
    response->headers[response->header_count++] = strdup(header);
}

/* Get header from request */
const char* quickman_get_header(HttpRequest *request, const char *name) {
    size_t name_len = strlen(name);

    for (int i = 0; i < request->header_count; i++) {
        if (strncasecmp(request->headers[i], name, name_len) == 0 &&
            request->headers[i][name_len] == ':') {
            const char *value = request->headers[i] + name_len + 1;
            while (*value == ' ') value++;
            return value;
        }
    }

    return NULL;
}

/* Get query parameter */
const char* quickman_get_query_param(HttpRequest *request, const char *name) {
    if (!request->query_string) return NULL;

    static char value_buffer[1024];
    char *query = strdup(request->query_string);
    char *token = strtok(query, "&");

    while (token) {
        char *equals = strchr(token, '=');
        if (equals) {
            *equals = '\0';
            if (strcmp(token, name) == 0) {
                strncpy(value_buffer, equals + 1, sizeof(value_buffer) - 1);
                value_buffer[sizeof(value_buffer) - 1] = '\0';
                free(query);
                return url_decode(value_buffer);
            }
        }
        token = strtok(NULL, "&");
    }

    free(query);
    return NULL;
}

/* URL decode */
static char* url_decode(const char *str) {
    static char decoded[1024];
    char *pstr = (char*)str;
    char *pbuf = decoded;

    while (*pstr && pbuf < decoded + sizeof(decoded) - 1) {
        if (*pstr == '%') {
            if (pstr[1] && pstr[2]) {
                int value;
                sscanf(pstr + 1, "%2x", &value);
                *pbuf++ = (char)value;
                pstr += 3;
            }
        } else if (*pstr == '+') {
            *pbuf++ = ' ';
            pstr++;
        } else {
            *pbuf++ = *pstr++;
        }
    }

    *pbuf = '\0';
    return decoded;
}

/* Get MIME type from file extension */
static const char* get_mime_type(const char *filepath) {
    const char *ext = strrchr(filepath, '.');
    if (!ext) return "application/octet-stream";

    if (strcmp(ext, ".html") == 0 || strcmp(ext, ".htm") == 0) return "text/html";
    if (strcmp(ext, ".css") == 0) return "text/css";
    if (strcmp(ext, ".js") == 0) return "application/javascript";
    if (strcmp(ext, ".json") == 0) return "application/json";
    if (strcmp(ext, ".png") == 0) return "image/png";
    if (strcmp(ext, ".jpg") == 0 || strcmp(ext, ".jpeg") == 0) return "image/jpeg";
    if (strcmp(ext, ".gif") == 0) return "image/gif";
    if (strcmp(ext, ".svg") == 0) return "image/svg+xml";
    if (strcmp(ext, ".txt") == 0) return "text/plain";
    if (strcmp(ext, ".pdf") == 0) return "application/pdf";

    return "application/octet-stream";
}

/* Get local IP address */
const char* quickman_get_local_ip(void) {
    static char ip_buffer[INET_ADDRSTRLEN];

    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) return "127.0.0.1";

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(53);
    inet_pton(AF_INET, "8.8.8.8", &addr.sin_addr);

    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(sock);
        return "127.0.0.1";
    }

    struct sockaddr_in local_addr;
    socklen_t addr_len = sizeof(local_addr);
    getsockname(sock, (struct sockaddr*)&local_addr, &addr_len);

    inet_ntop(AF_INET, &local_addr.sin_addr, ip_buffer, sizeof(ip_buffer));
    close(sock);

    return ip_buffer;
}

/* Stop server */
void quickman_stop(QuickManServer *server) {
    if (!server) return;

    server->running = 0;

    if (server->server_socket >= 0) {
        shutdown(server->server_socket, SHUT_RDWR);
        close(server->server_socket);
        server->server_socket = -1;
    }

    quickman_log("Server stopped");
}

/* Destroy server and free resources */
void quickman_destroy(QuickManServer *server) {
    if (!server) return;

    quickman_stop(server);

    if (server->semaphore) {
        sem_destroy((sem_t*)server->semaphore);
        free(server->semaphore);
    }

    free(server->config.address);
    free(server);
}
