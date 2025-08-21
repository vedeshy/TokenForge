#!/bin/bash
set -e

echo "Starting a minimal test worker"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create a minimal FastAPI server for testing
cat > minimal_server.py << EOF
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import time
import random

app = FastAPI()

class InferenceRequest(BaseModel):
    prompt: str
    max_tokens: int = 128
    temperature: float = 0.7
    top_p: float = 0.95
    stream: bool = False

class InferenceResponse(BaseModel):
    output: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    runtime_meta: dict

@app.get("/healthz")
async def health():
    return {"status": "ok"}

@app.post("/infer")
async def infer(request: InferenceRequest):
    # Simulate processing time
    time.sleep(0.5)
    
    # Generate a mock response
    token_count = len(request.prompt.split())
    output_tokens = random.randint(10, request.max_tokens)
    
    # Create a mock response based on the prompt
    if "KV cache" in request.prompt:
        output = "The KV cache stores key and value tensors from previous attention computations. It enables faster generation by avoiding recomputation of already processed tokens. This optimization significantly reduces inference time for autoregressive language models."
    elif "language model" in request.prompt:
        output = "Language models are statistical models that predict the probability distribution of words in a sequence. They are trained on large corpora of text data to learn patterns and relationships between words. Modern language models use transformer architectures with self-attention mechanisms."
    else:
        output = "This is a mock response from the minimal test worker. It simulates what a real language model would generate. The actual output would depend on the specific model being used and the input prompt."
    
    # Truncate to match the requested token count
    words = output.split()
    if len(words) > output_tokens:
        output = " ".join(words[:output_tokens])
    
    return InferenceResponse(
        output=output,
        latency_ms=int(500 + random.random() * 200),  # Simulate some latency variation
        tokens_in=token_count,
        tokens_out=len(output.split()),
        runtime_meta={
            "engine": "minimal-test-worker",
            "version": "0.1.0",
            "cuda": "N/A",
            "gpu": "CPU",
        }
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# Create a Dockerfile for the minimal server
cat > Dockerfile.minimal << EOF
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Copy server code
COPY minimal_server.py .

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "minimal_server.py"]
EOF

# Build the Docker image
echo "Building Docker image for minimal worker..."
docker build -t tokenforge-minimal-worker:latest -f Dockerfile.minimal .

# Run the container
echo "Starting minimal worker container..."
docker run -d --name tokenforge-minimal-worker \
    -p 8000:8000 \
    tokenforge-minimal-worker:latest

echo "Minimal worker is starting up."
echo "You can check the logs with: docker logs -f tokenforge-minimal-worker"

# Wait for the container to start
echo "Waiting for container to start..."
sleep 5

# Create a simple test script
cat > test_minimal_worker.py << EOF
import requests
import json
import time

print("Testing minimal worker...")
time.sleep(2)  # Give time for server to start

# Test health endpoint
try:
    response = requests.get("http://localhost:8000/healthz")
    print(f"Health check: {response.status_code} - {response.json()}")
except Exception as e:
    print(f"Health check failed: {e}")

# Test inference
try:
    payload = {
        "prompt": "Explain what a KV cache is in language models in 3 sentences.",
        "max_tokens": 128,
        "temperature": 0.7,
        "top_p": 0.95
    }
    
    print("\nSending inference request...")
    start_time = time.time()
    response = requests.post("http://localhost:8000/infer", json=payload)
    end_time = time.time()
    
    if response.status_code == 200:
        result = response.json()
        print("\nInference successful!")
        print(f"Generated output: {result['output']}")
        print(f"Worker latency: {result['latency_ms']}ms")
        print(f"Client latency: {(end_time - start_time)*1000:.2f}ms")
        print(f"Tokens in: {result['tokens_in']}")
        print(f"Tokens out: {result['tokens_out']}")
        print(f"Runtime metadata: {json.dumps(result['runtime_meta'], indent=2)}")
    else:
        print(f"Inference failed: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Inference failed: {e}")

print("\nTest completed!")
EOF

echo "When you're ready, test the worker with: python test_minimal_worker.py"
echo "When you're done, stop the container with: docker stop tokenforge-minimal-worker && docker rm tokenforge-minimal-worker"
