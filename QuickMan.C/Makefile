# QuickMan C HTTP Server - Makefile

CC = gcc
CFLAGS = -Wall -Wextra -O2 -pthread -D_POSIX_C_SOURCE=200809L
LDFLAGS = -pthread

# Source files
LIB_SRC = quickman.c
LIB_OBJ = $(LIB_SRC:.c=.o)
LIB_TARGET = libquickman.a

EXAMPLE_SRC = example.c
EXAMPLE_TARGET = quickman_example

# Installation paths
PREFIX = /usr/local
INCLUDE_DIR = $(PREFIX)/include
LIB_DIR = $(PREFIX)/lib

# Default target
all: $(LIB_TARGET) $(EXAMPLE_TARGET)

# Build static library
$(LIB_TARGET): $(LIB_OBJ)
	@echo "Creating static library: $@"
	ar rcs $@ $^
	@echo "Library created successfully!"

# Build example
$(EXAMPLE_TARGET): $(EXAMPLE_SRC) $(LIB_TARGET)
	@echo "Building example: $@"
	$(CC) $(CFLAGS) -o $@ $(EXAMPLE_SRC) $(LIB_TARGET) $(LDFLAGS)
	@echo "Example built successfully!"

# Compile object files
%.o: %.c quickman.h
	@echo "Compiling: $<"
	$(CC) $(CFLAGS) -c $< -o $@

# Run the example server
run: $(EXAMPLE_TARGET)
	@echo "Starting QuickMan server..."
	./$(EXAMPLE_TARGET)

# Run with custom port
run-port: $(EXAMPLE_TARGET)
	@echo "Starting QuickMan server on port 8080..."
	./$(EXAMPLE_TARGET) 8080

# Run with custom port and max connections
run-custom: $(EXAMPLE_TARGET)
	@echo "Starting QuickMan server on port 8080 with 50 max connections..."
	./$(EXAMPLE_TARGET) 8080 50

# Benchmark test
benchmark: $(EXAMPLE_TARGET)
	@echo "Running benchmark test..."
	@./$(EXAMPLE_TARGET) 8080 100 &
	@sleep 1
	@echo "Server started, running benchmark..."
	@if command -v ab > /dev/null; then \
		ab -n 10000 -c 50 http://localhost:8080/benchmark; \
	elif command -v wrk > /dev/null; then \
		wrk -t4 -c50 -d10s http://localhost:8080/benchmark; \
	else \
		echo "Please install 'ab' (Apache Bench) or 'wrk' for benchmarking"; \
	fi
	@pkill -f quickman_example

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(LIB_OBJ) $(LIB_TARGET) $(EXAMPLE_TARGET)
	@echo "Clean complete!"

# Clean and rebuild
rebuild: clean all

# Install library and headers
install: $(LIB_TARGET)
	@echo "Installing QuickMan library..."
	mkdir -p $(INCLUDE_DIR)
	mkdir -p $(LIB_DIR)
	cp quickman.h $(INCLUDE_DIR)/
	cp $(LIB_TARGET) $(LIB_DIR)/
	@echo "Installation complete!"
	@echo "Include path: $(INCLUDE_DIR)/quickman.h"
	@echo "Library path: $(LIB_DIR)/$(LIB_TARGET)"

# Uninstall library and headers
uninstall:
	@echo "Uninstalling QuickMan library..."
	rm -f $(INCLUDE_DIR)/quickman.h
	rm -f $(LIB_DIR)/$(LIB_TARGET)
	@echo "Uninstallation complete!"

# Debug build
debug: CFLAGS += -g -DDEBUG -O0
debug: clean all
	@echo "Debug build complete!"

# Test with curl
test: $(EXAMPLE_TARGET)
	@echo "Starting test server..."
	@./$(EXAMPLE_TARGET) 8080 &
	@sleep 1
	@echo ""
	@echo "Testing endpoints..."
	@echo ""
	@echo "1. Testing /status:"
	@curl -s http://localhost:8080/status | json_pp || curl -s http://localhost:8080/status
	@echo ""
	@echo "2. Testing /info:"
	@curl -s http://localhost:8080/info | json_pp || curl -s http://localhost:8080/info
	@echo ""
	@echo "3. Testing /echo with query parameter:"
	@curl -s "http://localhost:8080/echo?message=HelloWorld" | json_pp || curl -s "http://localhost:8080/echo?message=HelloWorld"
	@echo ""
	@echo "4. Testing /data:"
	@curl -s http://localhost:8080/data | json_pp || curl -s http://localhost:8080/data
	@echo ""
	@echo "5. Testing /hello:"
	@curl -s http://localhost:8080/hello
	@echo ""
	@echo "6. Testing /headers:"
	@curl -s -i http://localhost:8080/headers | head -15
	@echo ""
	@echo "7. Testing 404 (non-existent endpoint):"
	@curl -s http://localhost:8080/nonexistent | json_pp || curl -s http://localhost:8080/nonexistent
	@echo ""
	@echo "Tests complete! Stopping server..."
	@pkill -f quickman_example

# Help target
help:
	@echo "QuickMan C HTTP Server - Makefile Commands"
	@echo ""
	@echo "Build targets:"
	@echo "  make              - Build library and example"
	@echo "  make all          - Same as 'make'"
	@echo "  make clean        - Remove build artifacts"
	@echo "  make rebuild      - Clean and rebuild"
	@echo "  make debug        - Build with debug symbols"
	@echo ""
	@echo "Run targets:"
	@echo "  make run          - Run example server (port 1999)"
	@echo "  make run-port     - Run example server (port 8080)"
	@echo "  make run-custom   - Run with custom port and connections"
	@echo "  make test         - Run automated tests"
	@echo "  make benchmark    - Run performance benchmark"
	@echo ""
	@echo "Installation:"
	@echo "  make install      - Install library to $(PREFIX)"
	@echo "  make uninstall    - Remove installed library"
	@echo ""
	@echo "Usage example:"
	@echo "  ./quickman_example [port] [max_connections]"
	@echo "  ./quickman_example 8080 50"

.PHONY: all clean rebuild install uninstall run run-port run-custom test benchmark debug help
