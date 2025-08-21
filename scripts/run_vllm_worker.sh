#!/bin/bash
set -e

echo "Starting vLLM worker with a small model"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Set model name (default to TinyLlama)
MODEL_NAME=${1:-"TinyLlama/TinyLlama-1.1B-Chat-v1.0"}
echo "Using model: $MODEL_NAME"

# Create a Dockerfile for testing with a specific model
cat > Dockerfile.vllm_test << EOF
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir vllm==0.5.0 fastapi uvicorn pydantic prometheus-client

# Copy worker code
COPY workers/worker-vllm/server.py .
COPY workers/worker-vllm/metrics.py .

# Set environment variables
ENV MODEL_NAME="$MODEL_NAME"
ENV QUANT="fp16"
ENV MAX_MODEL_LEN="2048"

# Expose ports
EXPOSE 8000 8001

# Run the server
CMD ["python", "server.py"]
EOF

# Build the Docker image
echo "Building Docker image for vLLM worker..."
docker build -t tokenforge-vllm-test:latest -f Dockerfile.vllm_test .

# Run the container
echo "Starting vLLM worker container..."
docker run -d --name tokenforge-vllm-worker \
    -p 8000:8000 \
    -p 8001:8001 \
    tokenforge-vllm-test:latest

echo "vLLM worker is starting up. It may take a minute to download and load the model."
echo "You can check the logs with: docker logs -f tokenforge-vllm-worker"
echo "Once it's ready, test it with: python scripts/test_vllm_worker.py"
echo "When you're done, stop the container with: docker stop tokenforge-vllm-worker && docker rm tokenforge-vllm-worker"
