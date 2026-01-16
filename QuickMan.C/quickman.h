#ifndef QUICKMAN_H
#define QUICKMAN_H

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <pthread.h>
#include <strings.h>

/* HTTP Methods */
typedef enum {
    HTTP_GET,
    HTTP_POST,
    HTTP_PUT,
    HTTP_DELETE,
    HTTP_HEAD,
    HTTP_OPTIONS,
    HTTP_PATCH,
    HTTP_UNKNOWN
} HttpMethod;

/* HTTP Status Codes */
typedef enum {
    HTTP_OK = 200,
    HTTP_CREATED = 201,
    HTTP_NO_CONTENT = 204,
    HTTP_BAD_REQUEST = 400,
    HTTP_NOT_FOUND = 404,
    HTTP_INTERNAL_ERROR = 500
} HttpStatus;

/* Forward declarations */
typedef struct HttpRequest HttpRequest;
typedef struct HttpResponse HttpResponse;
typedef struct HttpContext HttpContext;
typedef struct QuickManServer QuickManServer;

/* HTTP Request structure */
struct HttpRequest {
    HttpMethod method;
    char *path;
    char *query_string;
    char *raw_url;
    char **headers;
    int header_count;
    char *body;
    size_t body_length;
    int client_socket;
};

/* HTTP Response structure */
struct HttpResponse {
    HttpStatus status_code;
    char *status_description;
    char *content_type;
    char **headers;
    int header_count;
    int client_socket;
};

/* HTTP Context - combines request and response */
struct HttpContext {
    HttpRequest *request;
    HttpResponse *response;
};

/* Endpoint handler function pointer */
typedef void (*EndpointHandler)(HttpContext *context);

/* Endpoint entry in routing table */
typedef struct {
    char *path;
    EndpointHandler handler;
} Endpoint;

/* Server configuration */
typedef struct {
    char *address;
    int port;
    int max_connections;
    Endpoint *endpoints;
    int endpoint_count;
} ServerConfig;

/* QuickMan Server structure */
struct QuickManServer {
    int server_socket;
    ServerConfig config;
    volatile int running;
    void *semaphore;  /* Platform-specific semaphore */
    pthread_t *thread_pool;
    int thread_pool_size;
};

/* Server Management Functions */
QuickManServer* quickman_create(void);
int quickman_start(QuickManServer *server, const char *address, int port,
                   Endpoint *endpoints, int endpoint_count, int max_connections);
int quickman_start_simple(QuickManServer *server, Endpoint *endpoints, int endpoint_count);
void quickman_stop(QuickManServer *server);
void quickman_destroy(QuickManServer *server);

/* Response Functions */
void quickman_respond_text(HttpContext *context, const char *text, HttpStatus status);
void quickman_respond_json(HttpContext *context, const char *json, HttpStatus status);
void quickman_respond_html(HttpContext *context, const char *html, HttpStatus status);
void quickman_respond_file(HttpContext *context, const char *filepath, HttpStatus status);
void quickman_respond_stream(HttpContext *context, FILE *stream, HttpStatus status);
void quickman_respond_status(HttpContext *context, HttpStatus status, const char *message);

/* Header Management */
void quickman_add_header(HttpResponse *response, const char *name, const char *value);
const char* quickman_get_header(HttpRequest *request, const char *name);
const char* quickman_get_query_param(HttpRequest *request, const char *name);

/* Utility Functions */
void quickman_log(const char *format, ...);
const char* quickman_get_local_ip(void);

#endif /* QUICKMAN_H */
