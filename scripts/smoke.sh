#!/bin/bash
set -e

echo "Running smoke test"

# Check if API is running
if ! curl -s http://localhost:8080/healthz > /dev/null; then
    echo "API is not running. Please start it with 'make run-api'"
    exit 1
fi

# Test deploy endpoint
echo "Testing /deploy endpoint..."
DEPLOY_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{"model":"meta-llama/Llama-3-8b-instruct","runtime":"vllm","quant":"fp16"}')

echo "Deploy response: $DEPLOY_RESPONSE"

# Test infer endpoint
echo "Testing /infer endpoint..."
INFER_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/infer \
  -H "Content-Type: application/json" \
  -d '{"model":"meta-llama/Llama-3-8b-instruct","runtime":"vllm","prompt":"Hello, world!","max_tokens":10,"temperature":0.2,"top_p":0.95,"stream":false}')

echo "Infer response: $INFER_RESPONSE"

# Test benchmark endpoint
echo "Testing /benchmarks/run endpoint..."
BENCHMARK_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/benchmarks/run \
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
  }')

echo "Benchmark response: $BENCHMARK_RESPONSE"

# Extract run ID from benchmark response
RUN_ID=$(echo $BENCHMARK_RESPONSE | jq -r '.id')

# Test benchmark status endpoint
echo "Testing /benchmarks/run/$RUN_ID endpoint..."
sleep 2
STATUS_RESPONSE=$(curl -s -X GET http://localhost:8080/api/v1/benchmarks/run/$RUN_ID)

echo "Status response: $STATUS_RESPONSE"

# Test models endpoint
echo "Testing /models endpoint..."
MODELS_RESPONSE=$(curl -s -X GET http://localhost:8080/api/v1/models)

echo "Models response: $MODELS_RESPONSE"

# Test runtimes endpoint
echo "Testing /runtimes endpoint..."
RUNTIMES_RESPONSE=$(curl -s -X GET http://localhost:8080/api/v1/runtimes)

echo "Runtimes response: $RUNTIMES_RESPONSE"

echo "Smoke test completed successfully!"
