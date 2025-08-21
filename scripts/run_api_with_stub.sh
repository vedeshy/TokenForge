#!/bin/bash
set -e

echo "Starting TokenForge API with stub worker"

# Create bin directory if it doesn't exist
mkdir -p bin

# Build API if it doesn't exist
if [ ! -f bin/api ]; then
    echo "Building API..."
    go build -o bin/api ./api
fi

# Start Docker Compose with stub worker
echo "Starting Docker Compose with stub worker..."
docker compose up -d postgres minio worker-stub

# Wait for services to start
echo "Waiting for services to start..."
sleep 5

# Run API server
echo "Starting API server..."
CONFIG_PATH=configs bin/api
