#!/bin/bash

# QuickMan Stress Test Suite
# Compares performance between C and C# implementations

set -e

RESULTS_DIR="stress_test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
C_PORT=8001
CS_PORT=8002
WARMUP_REQUESTS=1000
TEST_DURATION=30
CONCURRENT_CONNECTIONS=(10 50 100 200)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p "$RESULTS_DIR"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║        QuickMan Performance Comparison Suite             ║"
echo "║        C vs C# HTTP Server Stress Testing                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for required tools
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}ERROR: $1 is not installed${NC}"
        echo "Please install it to continue"
        exit 1
    fi
}

echo -e "${YELLOW}Checking required tools...${NC}"
check_tool "wrk"
check_tool "curl"
check_tool "dotnet"
check_tool "gcc"
echo -e "${GREEN}✓ All required tools found${NC}\n"

# Build C version
echo -e "${YELLOW}Building C version...${NC}"
cd QuickMan.C
make clean > /dev/null 2>&1
make > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ C version built successfully${NC}\n"
else
    echo -e "${RED}✗ Failed to build C version${NC}"
    exit 1
fi
cd ..

# Build C# version
echo -e "${YELLOW}Building C# version...${NC}"
cd QuickMan.Lib
dotnet build -c Release > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ C# version built successfully${NC}\n"
else
    echo -e "${RED}✗ Failed to build C# version${NC}"
    exit 1
fi
cd ..

# Function to start C server
start_c_server() {
    echo -e "${BLUE}Starting C server on port $C_PORT...${NC}"
    cd QuickMan.C
    ./quickman_example $C_PORT 1000 > "$RESULTS_DIR/c_server_${TIMESTAMP}.log" 2>&1 &
    C_PID=$!
    cd ..
    sleep 2

    if ps -p $C_PID > /dev/null; then
        echo -e "${GREEN}✓ C server started (PID: $C_PID)${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to start C server${NC}"
        return 1
    fi
}

# Function to start C# server
start_cs_server() {
    echo -e "${BLUE}Starting C# server on port $CS_PORT...${NC}"
    cd QuickMan.Lib
    dotnet run -c Release -- $CS_PORT > "../$RESULTS_DIR/cs_server_${TIMESTAMP}.log" 2>&1 &
    CS_PID=$!
    cd ..
    sleep 3

    if ps -p $CS_PID > /dev/null; then
        echo -e "${GREEN}✓ C# server started (PID: $CS_PID)${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to start C# server${NC}"
        return 1
    fi
}

# Function to stop servers
stop_servers() {
    echo -e "\n${YELLOW}Stopping servers...${NC}"
    if [ ! -z "$C_PID" ]; then
        kill $C_PID 2>/dev/null || true
        echo -e "${GREEN}✓ C server stopped${NC}"
    fi
    if [ ! -z "$CS_PID" ]; then
        kill $CS_PID 2>/dev/null || true
        echo -e "${GREEN}✓ C# server stopped${NC}"
    fi
    sleep 1
}

# Function to run wrk benchmark
run_wrk_test() {
    local port=$1
    local endpoint=$2
    local threads=$3
    local connections=$4
    local duration=$5
    local output_file=$6

    wrk -t${threads} -c${connections} -d${duration}s \
        --latency \
        "http://localhost:${port}${endpoint}" \
        > "$output_file" 2>&1
}

# Function to parse wrk results
parse_wrk_results() {
    local file=$1

    local requests_sec=$(grep "Requests/sec:" "$file" | awk '{print $2}')
    local avg_latency=$(grep "Latency" "$file" | head -1 | awk '{print $2}')
    local transfer_sec=$(grep "Transfer/sec:" "$file" | awk '{print $2}')
    local total_requests=$(grep "requests in" "$file" | awk '{print $1}')

    echo "$requests_sec|$avg_latency|$transfer_sec|$total_requests"
}

# Function to run comprehensive test suite
run_test_suite() {
    local server_name=$1
    local port=$2
    local output_prefix=$3

    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Testing $server_name Server${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}\n"

    # Warmup
    echo -e "${YELLOW}Warming up server...${NC}"
    curl -s "http://localhost:${port}/benchmark" > /dev/null
    wrk -t2 -c10 -d5s "http://localhost:${port}/benchmark" > /dev/null 2>&1
    sleep 2
    echo -e "${GREEN}✓ Warmup complete${NC}\n"

    # Test different endpoints
    local endpoints=("/benchmark" "/status" "/data")
    local endpoint_names=("Simple" "Status" "JSON")

    for i in "${!endpoints[@]}"; do
        local endpoint="${endpoints[$i]}"
        local endpoint_name="${endpoint_names[$i]}"

        echo -e "${BLUE}Testing endpoint: ${endpoint_name} (${endpoint})${NC}"

        for conns in "${CONCURRENT_CONNECTIONS[@]}"; do
            local threads=$((conns / 10))
            if [ $threads -lt 1 ]; then
                threads=1
            fi
            if [ $threads -gt 12 ]; then
                threads=12
            fi

            echo -e "  ${YELLOW}├─${NC} Connections: ${conns}, Threads: ${threads}"

            local output_file="$RESULTS_DIR/${output_prefix}_${endpoint_name}_c${conns}_${TIMESTAMP}.txt"
            run_wrk_test "$port" "$endpoint" "$threads" "$conns" "$TEST_DURATION" "$output_file"

            local results=$(parse_wrk_results "$output_file")
            local req_sec=$(echo "$results" | cut -d'|' -f1)
            local latency=$(echo "$results" | cut -d'|' -f2)

            echo -e "  ${GREEN}├─${NC} Requests/sec: ${req_sec}"
            echo -e "  ${GREEN}└─${NC} Avg Latency: ${latency}"
        done
        echo ""
    done
}

# Main execution
trap stop_servers EXIT INT TERM

# Test C# version
start_cs_server
if [ $? -eq 0 ]; then
    run_test_suite "C#" "$CS_PORT" "cs"
    stop_servers
    CS_PID=""
    sleep 2
fi

# Test C version
start_c_server
if [ $? -eq 0 ]; then
    run_test_suite "C" "$C_PORT" "c"
    stop_servers
    C_PID=""
fi

# Generate comparison report
echo -e "\n${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Generating Performance Comparison Report${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}\n"

REPORT_FILE="$RESULTS_DIR/comparison_report_${TIMESTAMP}.txt"

cat > "$REPORT_FILE" << 'REPORT_HEADER'
╔═══════════════════════════════════════════════════════════════════════════╗
║              QuickMan Performance Comparison Report                       ║
║                      C vs C# Implementation                               ║
╚═══════════════════════════════════════════════════════════════════════════╝

REPORT_HEADER

echo "Test Date: $(date)" >> "$REPORT_FILE"
echo "Test Duration per scenario: ${TEST_DURATION}s" >> "$REPORT_FILE"
echo "Concurrent Connection Levels: ${CONCURRENT_CONNECTIONS[*]}" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Parse and compare results
echo "═══════════════════════════════════════════════════════════════════════════" >> "$REPORT_FILE"
echo "PERFORMANCE SUMMARY" >> "$REPORT_FILE"
echo "═══════════════════════════════════════════════════════════════════════════" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

for endpoint_name in "Simple" "Status" "JSON"; do
    echo "Endpoint: $endpoint_name" >> "$REPORT_FILE"
    echo "───────────────────────────────────────────────────────────────────────────" >> "$REPORT_FILE"
    printf "%-15s %-20s %-20s %-15s\n" "Connections" "C# (req/s)" "C (req/s)" "Improvement" >> "$REPORT_FILE"
    echo "───────────────────────────────────────────────────────────────────────────" >> "$REPORT_FILE"

    for conns in "${CONCURRENT_CONNECTIONS[@]}"; do
        cs_file=$(ls "$RESULTS_DIR"/cs_${endpoint_name}_c${conns}_${TIMESTAMP}.txt 2>/dev/null | head -1)
        c_file=$(ls "$RESULTS_DIR"/c_${endpoint_name}_c${conns}_${TIMESTAMP}.txt 2>/dev/null | head -1)

        if [ -f "$cs_file" ] && [ -f "$c_file" ]; then
            cs_results=$(parse_wrk_results "$cs_file")
            c_results=$(parse_wrk_results "$c_file")

            cs_req=$(echo "$cs_results" | cut -d'|' -f1)
            c_req=$(echo "$c_results" | cut -d'|' -f1)

            if [ ! -z "$cs_req" ] && [ ! -z "$c_req" ]; then
                improvement=$(awk "BEGIN {printf \"%.2f%%\", (($c_req - $cs_req) / $cs_req) * 100}")
                printf "%-15s %-20s %-20s %-15s\n" "$conns" "$cs_req" "$c_req" "$improvement" >> "$REPORT_FILE"
            fi
        fi
    done
    echo "" >> "$REPORT_FILE"
done

echo "═══════════════════════════════════════════════════════════════════════════" >> "$REPORT_FILE"
echo "LATENCY COMPARISON" >> "$REPORT_FILE"
echo "═══════════════════════════════════════════════════════════════════════════" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

for endpoint_name in "Simple" "Status" "JSON"; do
    echo "Endpoint: $endpoint_name" >> "$REPORT_FILE"
    echo "───────────────────────────────────────────────────────────────────────────" >> "$REPORT_FILE"
    printf "%-15s %-20s %-20s\n" "Connections" "C# Latency" "C Latency" >> "$REPORT_FILE"
    echo "───────────────────────────────────────────────────────────────────────────" >> "$REPORT_FILE"

    for conns in "${CONCURRENT_CONNECTIONS[@]}"; do
        cs_file=$(ls "$RESULTS_DIR"/cs_${endpoint_name}_c${conns}_${TIMESTAMP}.txt 2>/dev/null | head -1)
        c_file=$(ls "$RESULTS_DIR"/c_${endpoint_name}_c${conns}_${TIMESTAMP}.txt 2>/dev/null | head -1)

        if [ -f "$cs_file" ] && [ -f "$c_file" ]; then
            cs_results=$(parse_wrk_results "$cs_file")
            c_results=$(parse_wrk_results "$c_file")

            cs_lat=$(echo "$cs_results" | cut -d'|' -f2)
            c_lat=$(echo "$c_results" | cut -d'|' -f2)

            if [ ! -z "$cs_lat" ] && [ ! -z "$c_lat" ]; then
                printf "%-15s %-20s %-20s\n" "$conns" "$cs_lat" "$c_lat" >> "$REPORT_FILE"
            fi
        fi
    done
    echo "" >> "$REPORT_FILE"
done

# Display report
cat "$REPORT_FILE"

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Test Results:${NC}"
echo -e "${GREEN}  - Full report: $REPORT_FILE${NC}"
echo -e "${GREEN}  - All results: $RESULTS_DIR/${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}\n"
