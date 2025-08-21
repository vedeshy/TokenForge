#!/bin/bash
set -e

echo "Building and testing TokenForge"

# Create bin directory
mkdir -p bin

# Build API
echo "Building API..."
go build -o bin/api ./api

# Start Docker Compose with stub worker
echo "Starting Docker Compose with stub worker..."
docker-compose up -d postgres minio worker-stub

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Run API server in background
echo "Starting API server..."
bin/api &
API_PID=$!

# Wait for API server to start
echo "Waiting for API server to start..."
sleep 5

# Run smoke test
echo "Running smoke test..."
bash scripts/smoke.sh

# Clean up
echo "Cleaning up..."
kill $API_PID
docker-compose down

echo "Build and test completed successfully!"
