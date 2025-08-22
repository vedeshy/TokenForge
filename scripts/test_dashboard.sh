#!/bin/bash

# Script to set up and test the TokenForge dashboard

# Exit on error
set -e

# Function to clean up on exit
cleanup() {
  echo "Cleaning up..."
  docker stop tokenforge-minimal-worker || true
  docker rm tokenforge-minimal-worker || true
  kill $API_PID || true
  kill $UI_PID || true
}

# Set up trap to call cleanup function on exit
trap cleanup EXIT

# Clean up any existing containers
echo "Cleaning up any existing containers..."
docker stop tokenforge-minimal-worker 2>/dev/null || true
docker rm tokenforge-minimal-worker 2>/dev/null || true

# Start the minimal worker
echo "Starting minimal worker..."
./scripts/run_minimal_worker.sh

# Wait for the worker to start
echo "Waiting for worker to start..."
sleep 5

# Start the API server in the background
echo "Starting API server..."
cd api && go run . &
API_PID=$!
cd ..

# Wait for the API server to start
echo "Waiting for API server to start..."
sleep 5

# Enable CORS for the API server
echo "Note: For a production environment, you would need to enable CORS in the API server."
echo "For testing purposes, you can use a browser extension to bypass CORS restrictions."

# Start the UI dashboard in the background
echo "Starting UI dashboard..."
cd ui/ui-dashboard && npm run dev &
UI_PID=$!
cd ../..

# Wait for the UI dashboard to start
echo "Waiting for UI dashboard to start..."
sleep 5

# Deploy a model using the API
echo "Deploying a test model..."
curl -X POST http://localhost:8080/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "model": "test-model",
    "runtime": "minimal",
    "quant": "fp16"
  }'

echo -e "\n\n=== Test Environment Ready ==="
echo "Minimal Worker: Running at http://localhost:8000"
echo "API Server: Running at http://localhost:8080"
echo "UI Dashboard: Running at http://localhost:5173"
echo ""
echo "You can now test the dashboard by opening http://localhost:5173 in your browser."
echo "Press Ctrl+C to stop all services and clean up."

# Keep the script running until Ctrl+C
echo "Press Ctrl+C to exit..."
wait
