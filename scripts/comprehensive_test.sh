#!/bin/bash
set -e

echo "Running comprehensive tests for TokenForge"

# Create bin directory if it doesn't exist
mkdir -p bin

# Build API if it doesn't exist
if [ ! -f bin/api ]; then
    echo "Building API..."
    go build -o bin/api ./api
fi

# Make sure Docker is running
echo "Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clean up any existing containers
echo "Cleaning up existing containers..."
docker compose down -v || true

# Start Docker services
echo "Starting Docker services..."
docker compose up -d postgres minio

# Build and start stub worker
echo "Building and starting stub worker..."
docker build -t tokenforge-worker-stub:latest -f workers/worker-vllm/Dockerfile.stub workers/worker-vllm
docker run -d --name tokenforge-worker-stub -p 8000:8000 -p 8001:8001 tokenforge-worker-stub:latest

# Wait for services to start
echo "Waiting for services to start..."
sleep 5

# Run API server in background
echo "Starting API server..."
CONFIG_PATH=configs bin/api &
API_PID=$!

# Wait for API server to start
echo "Waiting for API server to start..."
sleep 3

# Test health endpoint
echo -e "\n\n===== Testing health endpoint ====="
curl -v http://localhost:8080/healthz

# Test models endpoint
echo -e "\n\n===== Testing models endpoint ====="
curl -v http://localhost:8080/api/v1/models

# Test runtimes endpoint
echo -e "\n\n===== Testing runtimes endpoint ====="
curl -v http://localhost:8080/api/v1/runtimes

# Test deploy endpoint
echo -e "\n\n===== Testing deploy endpoint ====="
curl -v -X POST http://localhost:8080/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{"model":"meta-llama/Llama-3-8b-instruct","runtime":"vllm","quant":"fp16"}'

# Test inference endpoint
echo -e "\n\n===== Testing inference endpoint ====="
curl -v -X POST http://localhost:8080/api/v1/infer \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3-8b-instruct",
    "runtime": "vllm",
    "prompt": "Explain what a KV cache is",
    "max_tokens": 50,
    "temperature": 0.2,
    "top_p": 0.95,
    "stream": false
  }'

# Test benchmark endpoint
echo -e "\n\n===== Testing benchmark endpoint ====="
curl -v -X POST http://localhost:8080/api/v1/benchmarks/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3-8b-instruct",
    "runtimes": ["vllm"],
    "workloads": [
      {
        "name": "qa-short",
        "qps": 1,
        "duration_s": 10,
        "prompt_len": 128,
        "gen_tokens": 32
      }
    ]
  }'

# Get the run ID from the response
RUN_ID=$(curl -s -X POST http://localhost:8080/api/v1/benchmarks/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3-8b-instruct",
    "runtimes": ["vllm"],
    "workloads": [
      {
        "name": "qa-short",
        "qps": 1,
        "duration_s": 5,
        "prompt_len": 128,
        "gen_tokens": 32
      }
    ]
  }' | jq -r '.id')

# Test benchmark status endpoint
if [ ! -z "$RUN_ID" ]; then
    echo -e "\n\n===== Testing benchmark status endpoint ====="
    sleep 2
    curl -v http://localhost:8080/api/v1/benchmarks/run/$RUN_ID
fi

# Clean up
echo -e "\n\n===== Cleaning up ====="
kill $API_PID
docker stop tokenforge-worker-stub
docker rm tokenforge-worker-stub
docker compose down -v

echo -e "\n\nComprehensive tests completed!"
