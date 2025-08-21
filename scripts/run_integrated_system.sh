#!/bin/bash
set -e

echo "Starting integrated TokenForge system with minimal worker"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create a minimal FastAPI server for testing
cat > minimal_server.py << EOF
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import time
import random
import asyncio
import json

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
    # Check if streaming is requested
    if request.stream:
        return StreamingResponse(
            stream_response(request),
            media_type="text/event-stream"
        )
    
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

async def stream_response(request: InferenceRequest):
    """Generate a streaming response token by token."""
    # Create a mock response based on the prompt
    if "KV cache" in request.prompt:
        output = "The KV cache stores key and value tensors from previous attention computations. It enables faster generation by avoiding recomputation of already processed tokens. This optimization significantly reduces inference time for autoregressive language models."
    elif "language model" in request.prompt:
        output = "Language models are statistical models that predict the probability distribution of words in a sequence. They are trained on large corpora of text data to learn patterns and relationships between words. Modern language models use transformer architectures with self-attention mechanisms."
    else:
        output = "This is a mock response from the minimal test worker. It simulates what a real language model would generate. The actual output would depend on the specific model being used and the input prompt."
    
    # Split into tokens (words for simplicity)
    tokens = output.split()
    
    # Stream each token with a delay
    for i, token in enumerate(tokens):
        if i >= request.max_tokens:
            break
            
        # Create event data
        data = {
            "token": token,
            "index": i,
            "is_last": i == len(tokens) - 1 or i == request.max_tokens - 1
        }
        
        # Format as SSE event
        yield f"data: {json.dumps(data)}\\n\\n"
        
        # Simulate generation time
        await asyncio.sleep(0.1)
    
    # Send final event
    yield f"data: {json.dumps({'is_last': True, 'token': '', 'index': len(tokens)})}\\n\\n"

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

# Wait for the worker to start
echo "Waiting for worker to start..."
sleep 5

# Build the API server
echo "Building API server..."
go build -o bin/api ./api

# Create a configuration file for testing
cat > configs/test_config.yaml << EOF
models:
  - name: test-model
    quant: fp16
    hash: sha256:test-hash
EOF

# Register the model in the registry
echo "Starting API server..."
CONFIG_PATH=configs bin/api &
API_PID=$!

# Wait for the API server to start
echo "Waiting for API server to start..."
sleep 5

# Register the worker with the API
echo "Registering worker with API..."
curl -X POST http://localhost:8080/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "model": "test-model",
    "runtime": "minimal",
    "quant": "fp16"
  }'

# Create a test script for the integrated system
cat > test_integrated_system.py << EOF
import requests
import json
import time
import sys

def test_health():
    print("Testing API health endpoint...")
    try:
        response = requests.get("http://localhost:8080/healthz")
        print(f"Health check: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_inference(stream=False):
    print(f"Testing inference endpoint (stream={stream})...")
    try:
        payload = {
            "model": "test-model",
            "runtime": "minimal",
            "prompt": "Explain what a KV cache is in language models.",
            "max_tokens": 50,
            "temperature": 0.7,
            "top_p": 0.95,
            "stream": stream
        }
        
        start_time = time.time()
        
        if not stream:
            response = requests.post("http://localhost:8080/api/v1/infer", json=payload)
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
                return True
            else:
                print(f"Inference failed: {response.status_code} - {response.text}")
                return False
        else:
            # Streaming request
            response = requests.post(
                "http://localhost:8080/api/v1/infer", 
                json=payload,
                stream=True
            )
            
            if response.status_code != 200:
                print(f"Streaming inference failed: {response.status_code} - {response.text}")
                return False
                
            print("\nStreaming inference started:")
            full_text = ""
            
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data = json.loads(line_text[6:])
                        if 'token' in data:
                            print(f"Token: {data['token']}", end=" ", flush=True)
                            full_text += data['token'] + " "
                        if data.get('is_last', False):
                            print("\nStream completed!")
                            break
            
            end_time = time.time()
            print(f"\nFull text: {full_text}")
            print(f"Client latency: {(end_time - start_time)*1000:.2f}ms")
            return True
            
    except Exception as e:
        print(f"Inference failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing integrated TokenForge system...")
    
    if not test_health():
        print("Health check failed, exiting.")
        sys.exit(1)
    
    # Test normal inference
    if not test_inference(stream=False):
        print("Inference test failed, exiting.")
        sys.exit(1)
    
    # Test streaming inference
    if not test_inference(stream=True):
        print("Streaming inference test failed, exiting.")
        sys.exit(1)
    
    print("\nAll tests passed!")
EOF

echo "Integrated system is ready for testing."
echo "Run the test with: python test_integrated_system.py"
echo "When done, clean up with: kill $API_PID && docker stop tokenforge-minimal-worker && docker rm tokenforge-minimal-worker"
echo "API server PID: $API_PID"
