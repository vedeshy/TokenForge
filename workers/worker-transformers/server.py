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

# Import Transformers components
from transformers import AutoModelForCausalLM, AutoTokenizer, TextGenerationPipeline

# Import local modules
from metrics import setup_metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Transformers Worker")

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
MODEL = None
TOKENIZER = None
PIPELINE = None
MODEL_NAME = os.environ.get("MODEL_NAME", "meta-llama/Llama-3-8b-instruct")
QUANT = os.environ.get("QUANT", "fp16")

@app.on_event("startup")
async def startup_event():
    global MODEL, TOKENIZER, PIPELINE
    
    logger.info(f"Starting Transformers with model {MODEL_NAME}")
    
    try:
        # Initialize tokenizer
        TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME)
        
        # Initialize model with specified precision
        if QUANT == "fp16" and torch.cuda.is_available():
            MODEL = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
            )
        else:
            MODEL = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                device_map="auto",
                trust_remote_code=True,
            )
        
        # Initialize pipeline
        PIPELINE = TextGenerationPipeline(
            model=MODEL,
            tokenizer=TOKENIZER,
            device=0 if torch.cuda.is_available() else -1,
        )
        
        # Start Prometheus metrics server on a different port
        start_http_server(8001)
        
        # Setup GPU metrics collection
        setup_metrics(engine_name="transformers")
        
        logger.info("Transformers model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Transformers model: {e}")
        raise

@app.get("/healthz")
async def healthz():
    if MODEL is None or TOKENIZER is None:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    # This endpoint is just for documentation
    # The actual metrics are served by the Prometheus client on port 8001
    return {"message": "Metrics available at :8001/metrics"}

@app.post("/infer")
async def infer(request: InferenceRequest):
    global MODEL, TOKENIZER, PIPELINE
    
    if MODEL is None or TOKENIZER is None or PIPELINE is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    
    # Record start time
    start_time = time.time()
    
    try:
        # Tokenize input to count tokens
        input_tokens = TOKENIZER.encode(request.prompt)
        tokens_in = len(input_tokens)
        
        # Generate text
        generation_config = {
            "max_new_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "do_sample": request.temperature > 0,
        }
        
        output = PIPELINE(
            request.prompt,
            **generation_config
        )[0]["generated_text"]
        
        # Extract only the newly generated text
        generated_text = output[len(request.prompt):]
        
        # Tokenize output to count tokens
        output_tokens = TOKENIZER.encode(generated_text)
        tokens_out = len(output_tokens)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Update Prometheus metrics
        inference_requests.labels(engine="transformers").inc()
        inference_latency.labels(engine="transformers").observe(latency_ms)
        generated_tokens.labels(engine="transformers").inc(tokens_out)
        
        # Update GPU memory metrics
        if torch.cuda.is_available():
            vram_bytes.labels(engine="transformers").set(torch.cuda.memory_allocated())
        
        # Get runtime metadata
        import transformers
        runtime_meta = {
            "engine": "transformers",
            "version": transformers.__version__,
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
            oom_counter.labels(engine="transformers").inc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
