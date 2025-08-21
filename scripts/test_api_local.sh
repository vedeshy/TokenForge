#!/bin/bash
set -e

echo "Testing TokenForge API locally without Docker"

# Create bin directory if it doesn't exist
mkdir -p bin

# Build API if it doesn't exist
if [ ! -f bin/api ]; then
    echo "Building API..."
    go build -o bin/api ./api
fi

# Run API server in background
echo "Starting API server..."
CONFIG_PATH=configs bin/api &
API_PID=$!

# Wait for API server to start
echo "Waiting for API server to start..."
sleep 3

# Test health endpoint
echo "Testing health endpoint..."
curl -v http://localhost:8080/healthz

# Test models endpoint
echo -e "\n\nTesting models endpoint..."
curl -v http://localhost:8080/api/v1/models

# Test runtimes endpoint
echo -e "\n\nTesting runtimes endpoint..."
curl -v http://localhost:8080/api/v1/runtimes

# Test deploy endpoint (will fail without workers but should return a response)
echo -e "\n\nTesting deploy endpoint..."
curl -v -X POST http://localhost:8080/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{"model":"meta-llama/Llama-3-8b-instruct","runtime":"vllm","quant":"fp16"}'

# Clean up
echo -e "\n\nCleaning up..."
kill $API_PID

echo "Test completed"
