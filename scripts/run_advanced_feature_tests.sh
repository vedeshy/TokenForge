#!/bin/bash
set -e

echo "===== Testing Advanced Benchmarking Features ====="

# Define color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to run a test and check its exit status
run_test() {
    echo -e "\n${YELLOW}Running $1...${NC}"
    if python3 "$1"; then
        echo -e "${GREEN}✓ $1 completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ $1 failed${NC}"
        return 1
    fi
}

# Test the prompt templates
echo -e "\n${YELLOW}=== Testing Prompt Templates ===${NC}"
run_test scripts/test_templates.py

# Test the evaluation metrics
echo -e "\n${YELLOW}=== Testing Evaluation Metrics ===${NC}"
run_test scripts/test_evaluation.py

# Test the memory profiling
echo -e "\n${YELLOW}=== Testing Memory Profiling ===${NC}"
run_test scripts/test_memory_profiling.py

# Start the minimal worker for benchmark testing
echo -e "\n${YELLOW}=== Starting Minimal Worker ===${NC}"
echo "Building and starting minimal worker..."
./scripts/run_minimal_worker.sh &
WORKER_PID=$!

# Wait for worker to start
echo "Waiting for worker to start..."
sleep 5

# Test the advanced benchmark features
echo -e "\n${YELLOW}=== Testing Template-based Benchmark ===${NC}"
python3 scripts/test_advanced_benchmark.py --config harness/workloads/template_benchmark.yaml

echo -e "\n${YELLOW}=== Testing Evaluation Benchmark ===${NC}"
python3 scripts/test_advanced_benchmark.py --config harness/workloads/evaluation_benchmark.yaml

echo -e "\n${YELLOW}=== Testing Memory Profiling Benchmark ===${NC}"
python3 scripts/test_advanced_benchmark.py --config harness/workloads/memory_benchmark.yaml

# Clean up
echo -e "\n${YELLOW}=== Cleaning Up ===${NC}"
if [ -n "$WORKER_PID" ]; then
    echo "Stopping minimal worker..."
    kill $WORKER_PID || true
fi

echo -e "\n${GREEN}All tests completed!${NC}"
echo "You can find the benchmark results in the /tmp directory."
