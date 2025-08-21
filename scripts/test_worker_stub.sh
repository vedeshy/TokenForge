#!/bin/bash
set -e

echo "Testing the worker stub"

# Make sure Docker is running
echo "Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build and start stub worker
echo "Building and starting stub worker..."
docker build -t tokenforge-worker-stub:latest -f workers/worker-vllm/Dockerfile.stub workers/worker-vllm
docker run -d --name tokenforge-worker-stub -p 8000:8000 -p 8001:8001 tokenforge-worker-stub:latest

# Wait for worker to start
echo "Waiting for worker to start..."
sleep 3

# Test health endpoint
echo -e "\n\n===== Testing worker health endpoint ====="
curl -v http://localhost:8000/healthz

# Test metrics endpoint
echo -e "\n\n===== Testing worker metrics endpoint ====="
curl -v http://localhost:8001/metrics

# Test inference endpoint
echo -e "\n\n===== Testing worker inference endpoint ====="
curl -v -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain what a KV cache is",
    "max_tokens": 50,
    "temperature": 0.2,
    "top_p": 0.95,
    "stream": false
  }'

# Clean up
echo -e "\n\n===== Cleaning up ====="
docker stop tokenforge-worker-stub
docker rm tokenforge-worker-stub

echo -e "\n\nWorker tests completed!"
