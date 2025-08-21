#!/usr/bin/env python3
import os
import time
import json
import logging
from typing import Dict, List, Optional, Union

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import start_http_server, Counter, Histogram, Gauge

# Import vLLM components
from vllm import LLMEngine, SamplingParams
from vllm.utils import random_uuid

# Import local modules
from metrics import setup_metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="vLLM Worker")

# Initialize metrics
inference_requests = Counter(
    "inference_requests_total", "Total number of inference requests", ["engine"]
)
inference_latency = Histogram(
    "inference_latency_ms_bucket", "Inference latency in milliseconds", ["engine"]
)
generated_tokens = Counter(
    "generated_tokens_total", "Total number of generated tokens", ["engine"]
)
kv_cache_bytes = Gauge(
    "kv_cache_bytes", "KV cache memory usage in bytes", ["engine"]
)
vram_bytes = Gauge(
    "vram_bytes", "GPU VRAM usage in bytes", ["engine"]
)
oom_counter = Counter(
    "oom_total", "Total number of OOM errors", ["engine"]
)

# Define request/response models
class InferenceRequest(BaseModel):
    prompt: str
    max_tokens: int = 128
    temperature: float = 0.2
    top_p: float = 0.95
    stream: bool = False

class InferenceResponse(BaseModel):
    output: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    runtime_meta: Dict[str, str]

# Global variables
ENGINE = None
MODEL_NAME = os.environ.get("MODEL_NAME", "meta-llama/Llama-3-8b-instruct")
QUANT = os.environ.get("QUANT", "fp16")

@app.on_event("startup")
async def startup_event():
    global ENGINE
    
    logger.info(f"Starting vLLM engine with model {MODEL_NAME}")
    
    try:
        # Initialize vLLM engine
        ENGINE = LLMEngine.from_engine_args(
            model=MODEL_NAME,
            dtype=torch.float16 if QUANT == "fp16" else torch.float32,
            trust_remote_code=True,
            max_model_len=int(os.environ.get("MAX_MODEL_LEN", "8192")),
        )
        
        # Start Prometheus metrics server on a different port
        start_http_server(8001)
        
        logger.info("vLLM engine started successfully")
    except Exception as e:
        logger.error(f"Failed to start vLLM engine: {e}")
        raise

@app.get("/healthz")
async def healthz():
    if ENGINE is None:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    # This endpoint is just for documentation
    # The actual metrics are served by the Prometheus client on port 8001
    return {"message": "Metrics available at :8001/metrics"}

@app.post("/infer")
async def infer(request: InferenceRequest):
    global ENGINE
    
    if ENGINE is None:
        raise HTTPException(status_code=503, detail="Engine not ready")
    
    # Record start time
    start_time = time.time()
    
    try:
        # Prepare sampling parameters
        sampling_params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
        )
        
        # Generate text
        result = ENGINE.generate(request.prompt, sampling_params)
        
        # Get the generated text
        generated_text = result[0].outputs[0].text
        
        # Calculate metrics
        latency_ms = int((time.time() - start_time) * 1000)
        tokens_in = result[0].prompt_token_ids.shape[0]
        tokens_out = len(result[0].outputs[0].token_ids)
        
        # Update Prometheus metrics
        inference_requests.labels(engine="vllm").inc()
        inference_latency.labels(engine="vllm").observe(latency_ms)
        generated_tokens.labels(engine="vllm").inc(tokens_out)
        
        # Update GPU memory metrics
        if torch.cuda.is_available():
            vram_bytes.labels(engine="vllm").set(torch.cuda.memory_allocated())
        
        # Get runtime metadata
        runtime_meta = {
            "engine": "vllm",
            "version": "0.5.0",  # Replace with actual version
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        }
        
        # Return response
        return InferenceResponse(
            output=generated_text,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            runtime_meta=runtime_meta,
        )
    
    except Exception as e:
        logger.error(f"Inference error: {e}")
        if "CUDA out of memory" in str(e):
            oom_counter.labels(engine="vllm").inc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
