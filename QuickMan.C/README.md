# QuickMan C - High-Performance HTTP Server Library

A lightweight, high-performance HTTP server library written in pure C, inspired by QuickMan.Lib. QuickMan C provides a simple API for building fast, self-hosted web services with minimal overhead.

## Features

- **High Performance**: Designed for speed with minimal overhead
- **Simple API**: Easy-to-use endpoint mapping system
- **Thread-Safe**: Built-in connection limiting with POSIX semaphores
- **Multi-Threading**: One thread per request for concurrent handling
- **Flexible Responses**: Support for JSON, HTML, plain text, files, and streams
- **HTTP/1.1 Support**: Full HTTP method support (GET, POST, PUT, DELETE, etc.)
- **Query Parameters**: Built-in query string parsing
- **Custom Headers**: Easy header management
- **Cross-Platform**: Works on Linux, macOS, and other POSIX systems
- **Zero Dependencies**: Only requires standard C library and POSIX threads

## Architecture

QuickMan C follows a simple yet efficient architecture:

```
┌─────────────────────────────────────────┐
│         Main Server Thread              │
│  (Accept connections, manage semaphore) │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        │  Semaphore Gate  │
        │  (Connection     │
        │   Limiting)      │
        └────────┬─────────┘
                 │
    ┌────────────┴─────────────┐
    │                          │
┌───▼────┐  ┌───────┐  ┌──────▼──┐
│Worker  │  │Worker │  │ Worker  │
│Thread 1│  │Thread │  │ Thread N│
└────────┘  └───────┘  └─────────┘
```

### Key Components

1. **Server Socket**: Listens for incoming connections
2. **Semaphore**: Limits concurrent connections to prevent resource exhaustion
3. **Thread Pool**: Spawns detached threads for each request
4. **Endpoint Router**: Hash-based routing to handler functions
5. **Request Parser**: Parses HTTP requests from raw socket data
6. **Response Builder**: Constructs HTTP responses with proper headers

## Quick Start

### Building the Library

```bash
# Clone or download the repository
cd QuickMan.C

# Build the library and example
make

# Run the example server
make run

# Or run on a custom port
./quickman_example 8080
```

### Basic Usage

```c
#include "quickman.h"

/* Define an endpoint handler */
void endpoint_hello(HttpContext *context) {
    const char *json = "{\"message\":\"Hello, World!\"}";
    quickman_respond_json(context, json, HTTP_OK);
}

int main() {
    /* Create server */
    QuickManServer *server = quickman_create();

    /* Define endpoints */
    Endpoint endpoints[] = {
        { "hello", endpoint_hello }
    };

    /* Start server on port 8080 with 20 max connections */
    quickman_start(server, "0.0.0.0", 8080,
                   endpoints, 1, 20);

    /* Cleanup */
    quickman_destroy(server);
    return 0;
}
```

## API Reference

### Server Management

#### `QuickManServer* quickman_create(void)`
Creates a new server instance.

**Returns**: Pointer to server instance or NULL on failure

#### `int quickman_start(QuickManServer *server, const char *address, int port, Endpoint *endpoints, int endpoint_count, int max_connections)`
Starts the HTTP server with custom configuration.

**Parameters**:
- `server`: Server instance
- `address`: IP address to bind (e.g., "0.0.0.0", "127.0.0.1")
- `port`: Port number (1-65535)
- `endpoints`: Array of endpoint definitions
- `endpoint_count`: Number of endpoints
- `max_connections`: Maximum concurrent connections

**Returns**: 0 on success, -1 on failure

#### `int quickman_start_simple(QuickManServer *server, Endpoint *endpoints, int endpoint_count)`
Starts the server with default configuration (localhost:1999, 20 max connections).

#### `void quickman_stop(QuickManServer *server)`
Stops the server gracefully.

#### `void quickman_destroy(QuickManServer *server)`
Destroys the server and frees all resources.

### Response Functions

#### `void quickman_respond_json(HttpContext *context, const char *json, HttpStatus status)`
Sends a JSON response with Content-Type: application/json.

```c
void endpoint_data(HttpContext *context) {
    const char *json = "{\"status\":\"ok\",\"data\":[1,2,3]}";
    quickman_respond_json(context, json, HTTP_OK);
}
```

#### `void quickman_respond_text(HttpContext *context, const char *text, HttpStatus status)`
Sends a plain text response with Content-Type: text/plain.

```c
void endpoint_hello(HttpContext *context) {
    quickman_respond_text(context, "Hello, World!", HTTP_OK);
}
```

#### `void quickman_respond_html(HttpContext *context, const char *html, HttpStatus status)`
Sends an HTML response with Content-Type: text/html.

```c
void endpoint_home(HttpContext *context) {
    const char *html = "<html><body><h1>Welcome!</h1></body></html>";
    quickman_respond_html(context, html, HTTP_OK);
}
```

#### `void quickman_respond_file(HttpContext *context, const char *filepath, HttpStatus status)`
Sends a file response with automatic MIME type detection.

```c
void endpoint_download(HttpContext *context) {
    quickman_respond_file(context, "/path/to/file.pdf", HTTP_OK);
}
```

#### `void quickman_respond_stream(HttpContext *context, FILE *stream, HttpStatus status)`
Sends a stream response using chunked transfer encoding.

#### `void quickman_respond_status(HttpContext *context, HttpStatus status, const char *message)`
Sends a status response with JSON message.

```c
void endpoint_test(HttpContext *context) {
    quickman_respond_status(context, HTTP_NOT_FOUND, "Resource not found");
}
```

### Header Management

#### `void quickman_add_header(HttpResponse *response, const char *name, const char *value)`
Adds a custom header to the response.

```c
void endpoint_custom(HttpContext *context) {
    quickman_add_header(context->response, "X-Custom-Header", "MyValue");
    quickman_respond_json(context, "{}", HTTP_OK);
}
```

#### `const char* quickman_get_header(HttpRequest *request, const char *name)`
Gets a header value from the request.

```c
void endpoint_check_auth(HttpContext *context) {
    const char *auth = quickman_get_header(context->request, "Authorization");
    if (auth) {
        /* Process authorization */
    }
}
```

### Query Parameters

#### `const char* quickman_get_query_param(HttpRequest *request, const char *name)`
Gets a query parameter value (URL decoded).

```c
void endpoint_search(HttpContext *context) {
    const char *query = quickman_get_query_param(context->request, "q");
    if (query) {
        /* Process search query */
    }
}
```

### Utility Functions

#### `void quickman_log(const char *format, ...)`
Logs a timestamped message to stdout.

```c
quickman_log("Server started on port %d", 8080);
// Output: [2026-01-16 10:30:45] Server started on port 8080
```

#### `const char* quickman_get_local_ip(void)`
Gets the local IP address of the machine.

## HTTP Status Codes

The following status codes are available:

- `HTTP_OK` (200)
- `HTTP_CREATED` (201)
- `HTTP_NO_CONTENT` (204)
- `HTTP_BAD_REQUEST` (400)
- `HTTP_NOT_FOUND` (404)
- `HTTP_INTERNAL_ERROR` (500)

## HTTP Methods

Supported HTTP methods:

- `HTTP_GET`
- `HTTP_POST`
- `HTTP_PUT`
- `HTTP_DELETE`
- `HTTP_HEAD`
- `HTTP_OPTIONS`
- `HTTP_PATCH`
- `HTTP_UNKNOWN`

## Advanced Examples

### Handling POST Requests

```c
void endpoint_create_user(HttpContext *context) {
    if (context->request->method != HTTP_POST) {
        quickman_respond_status(context, HTTP_BAD_REQUEST,
                               "POST method required");
        return;
    }

    /* Access request body */
    if (context->request->body) {
        printf("Received body: %s\n", context->request->body);
        printf("Body length: %zu\n", context->request->body_length);

        quickman_respond_json(context,
            "{\"status\":\"created\"}", HTTP_CREATED);
    } else {
        quickman_respond_status(context, HTTP_BAD_REQUEST,
                               "Body required");
    }
}
```

### Multiple Query Parameters

```c
void endpoint_filter(HttpContext *context) {
    const char *category = quickman_get_query_param(context->request, "category");
    const char *sort = quickman_get_query_param(context->request, "sort");
    const char *limit = quickman_get_query_param(context->request, "limit");

    char response[512];
    snprintf(response, sizeof(response),
        "{\"category\":\"%s\",\"sort\":\"%s\",\"limit\":\"%s\"}",
        category ? category : "all",
        sort ? sort : "asc",
        limit ? limit : "10");

    quickman_respond_json(context, response, HTTP_OK);
}
```

### Custom Headers and CORS

```c
void endpoint_cors(HttpContext *context) {
    quickman_add_header(context->response, "Access-Control-Allow-Origin", "*");
    quickman_add_header(context->response, "Access-Control-Allow-Methods",
                       "GET, POST, PUT, DELETE");
    quickman_add_header(context->response, "Access-Control-Allow-Headers",
                       "Content-Type");

    quickman_respond_json(context, "{\"message\":\"CORS enabled\"}", HTTP_OK);
}
```

### RESTful API Example

```c
void endpoint_users(HttpContext *context) {
    switch (context->request->method) {
        case HTTP_GET:
            /* List all users */
            quickman_respond_json(context, "{\"users\":[]}", HTTP_OK);
            break;

        case HTTP_POST:
            /* Create new user */
            quickman_respond_json(context, "{\"id\":1}", HTTP_CREATED);
            break;

        case HTTP_PUT:
            /* Update user */
            quickman_respond_json(context, "{\"updated\":true}", HTTP_OK);
            break;

        case HTTP_DELETE:
            /* Delete user */
            quickman_respond_status(context, HTTP_NO_CONTENT, "Deleted");
            break;

        default:
            quickman_respond_status(context, HTTP_BAD_REQUEST,
                                   "Method not supported");
            break;
    }
}
```

## Performance Considerations

### Connection Limiting

QuickMan C uses POSIX semaphores to limit concurrent connections. This prevents resource exhaustion under high load:

- Default: 20 concurrent connections
- Configurable via `max_connections` parameter
- Additional connections wait until a slot becomes available

### Threading Model

- **One thread per request**: Simple and effective for most use cases
- **Detached threads**: Automatic cleanup when request completes
- **Semaphore gating**: Prevents thread explosion
- **Non-blocking accept**: Main thread continues accepting connections

### Buffer Sizes

- Request header buffer: 8KB
- Response body buffer: 16KB
- File streaming buffer: 16KB

### Optimization Tips

1. **Adjust max_connections** based on your workload
2. **Use appropriate response types** (don't load entire files into memory)
3. **Keep endpoint handlers fast** (offload heavy work to background threads)
4. **Reuse connections** where possible
5. **Monitor resource usage** under load

## Building and Installation

### Build Commands

```bash
# Build library and example
make

# Build with debug symbols
make debug

# Clean build artifacts
make clean

# Rebuild from scratch
make rebuild

# Install system-wide
sudo make install

# Uninstall
sudo make uninstall
```

### Running Tests

```bash
# Run automated tests
make test

# Run performance benchmark (requires 'ab' or 'wrk')
make benchmark
```

### Custom Build

```bash
# Compile your own program
gcc -o myserver myserver.c -L. -lquickman -pthread

# Or link directly
gcc -o myserver myserver.c quickman.c -pthread
```

## Platform Support

- **Linux**: Full support
- **macOS**: Full support
- **BSD**: Should work (not tested)
- **Windows**: Not supported (requires POSIX threads and sockets)

## Requirements

- C99 or later
- POSIX-compliant system
- pthread library
- Standard C library

## Comparison with QuickMan.Lib (C#)

| Feature | QuickMan.Lib (C#) | QuickMan C |
|---------|-------------------|------------|
| Language | C# | C |
| Performance | 20,000+ req/s | Similar or better |
| Dependencies | .NET Framework | None (POSIX only) |
| Memory Usage | Higher (managed) | Lower (native) |
| Ease of Use | Very Easy | Easy |
| Platform | Windows, .NET | POSIX systems |

## Known Limitations

1. **Request Size**: Limited to 8KB headers, configurable body size
2. **HTTP/1.1 Only**: No HTTP/2 support
3. **No HTTPS**: Plain HTTP only (use reverse proxy for SSL)
4. **No Persistent Connections**: Each request closes the connection
5. **No Chunked Request Bodies**: Only supports Content-Length

## Future Enhancements

- [ ] HTTP/2 support
- [ ] Persistent connections (Keep-Alive)
- [ ] WebSocket support
- [ ] Built-in SSL/TLS support
- [ ] Connection pooling
- [ ] Request/response middleware
- [ ] Static file serving with caching
- [ ] Compression support (gzip, brotli)

## Examples

Check out `example.c` for a complete working example with multiple endpoints demonstrating:

- JSON responses
- HTML responses
- Plain text responses
- Query parameter parsing
- Custom headers
- POST request handling
- Error handling
- Multiple HTTP methods

## Troubleshooting

### "Address already in use" Error

```bash
# Check if port is in use
lsof -i :8080

# Kill process using the port
kill -9 <PID>
```

### Permission Denied on Port < 1024

```bash
# Run with sudo for ports < 1024
sudo ./quickman_example 80

# Or use a higher port number
./quickman_example 8080
```

### Compilation Errors

```bash
# Ensure pthread library is available
sudo apt-get install libc6-dev

# Try with explicit pthread flag
gcc -o example example.c quickman.c -pthread
```

## License

This project is inspired by QuickMan.Lib and is provided as-is for educational and commercial use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Credits

Inspired by [QuickMan.Lib](https://github.com/thebitbrine/QuickMan) - A lightweight C# HTTP server library.

## Support

For issues, questions, or contributions, please visit the GitHub repository.

---

**QuickMan C** - High-performance HTTP serving made simple in C.
