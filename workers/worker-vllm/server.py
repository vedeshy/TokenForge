#!/usr/bin/env python3
import os
import time
import json
import logging
import psutil
from typing import Dict, List, Optional, Union

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import asyncio

# Import vLLM components
from vllm import LLMEngine, SamplingParams
from vllm.utils import random_uuid

# Import local modules
from metrics import setup_metrics, record_ttft, update_token_gen_rate, record_inter_token_latency

def get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    result = {
        "cpu": {
            "rss": memory_info.rss,  # Resident Set Size
            "vms": memory_info.vms,  # Virtual Memory Size
        }
    }
    
    # Add GPU memory info if available
    if torch.cuda.is_available():
        gpu_info = {}
        for i in range(torch.cuda.device_count()):
            gpu_info[f"gpu_{i}_allocated"] = int(torch.cuda.memory_allocated(i))
            gpu_info[f"gpu_{i}_reserved"] = int(torch.cuda.memory_reserved(i))
            
            # Get memory stats if available
            try:
                memory_stats = torch.cuda.memory_stats(i)
                gpu_info[f"gpu_{i}_active_bytes"] = memory_stats.get("active_bytes.all.current", 0)
                gpu_info[f"gpu_{i}_reserved_bytes"] = memory_stats.get("reserved_bytes.all.current", 0)
                gpu_info[f"gpu_{i}_active_count"] = memory_stats.get("active_bytes.all.current_count", 0)
                gpu_info[f"gpu_{i}_segment_count"] = memory_stats.get("segment.all.current_count", 0)
            except:
                pass
                
        result["gpu"] = gpu_info
    
    return result

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
    memory_usage: Optional[Dict[str, Any]] = None

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
        
        # Handle streaming differently
        if request.stream:
            return StreamingResponse(
                stream_tokens(request.prompt, sampling_params, start_time),
                media_type="text/event-stream"
            )
        
        # Non-streaming generation
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
        
        # Calculate and update token generation rate
        if latency_ms > 0:
            tokens_per_second = (tokens_out * 1000) / latency_ms
            update_token_gen_rate(tokens_per_second, "vllm")
        
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
        
        # Get memory usage
        memory_usage = get_memory_usage()
        
        # Return response
        return InferenceResponse(
            output=generated_text,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            runtime_meta=runtime_meta,
            memory_usage=memory_usage,
        )
    
    except Exception as e:
        logger.error(f"Inference error: {e}")
        if "CUDA out of memory" in str(e):
            oom_counter.labels(engine="vllm").inc()
        raise HTTPException(status_code=500, detail=str(e))

async def stream_tokens(prompt: str, sampling_params: SamplingParams, start_time: float):
    """Stream tokens from the model with streaming-specific metrics."""
    global ENGINE
    
    # Track metrics for streaming
    first_token_received = False
    last_token_time = start_time
    tokens_generated = 0
    
    # Create request ID
    request_id = random_uuid()
    
    try:
        # Add request to the engine
        ENGINE.add_request(request_id, prompt, sampling_params)
        
        # Process request and stream results
        while True:
            # Get request output (this is non-blocking)
            request_output = ENGINE.get_request_output(request_id)
            
            # If request is finished, break
            if request_output is not None and request_output.finished:
                break
            
            # If we have new tokens, yield them
            if request_output is not None and len(request_output.outputs) > 0:
                # Get the latest output
                output = request_output.outputs[0]
                
                # If this is the first token, record TTFT
                if not first_token_received and len(output.token_ids) > 0:
                    first_token_received = True
                    ttft = (time.time() - start_time) * 1000
                    record_ttft(ttft, "vllm")
                    logger.info(f"Time to first token: {ttft:.2f}ms")
                
                # If we have new tokens since last check
                if tokens_generated < len(output.token_ids):
                    # Get the new tokens
                    new_tokens = output.token_ids[tokens_generated:]
                    new_text = output.text[len(output.text) - len(new_tokens):]
                    
                    # Record inter-token latency
                    current_time = time.time()
                    if tokens_generated > 0:  # Skip for the first token
                        inter_token_ms = (current_time - last_token_time) * 1000
                        record_inter_token_latency(inter_token_ms, "vllm")
                    
                    # Update last token time
                    last_token_time = current_time
                    
                    # Update tokens generated
                    tokens_generated = len(output.token_ids)
                    
                    # Update token generation rate
                    elapsed_sec = current_time - start_time
                    if elapsed_sec > 0:
                        tokens_per_second = tokens_generated / elapsed_sec
                        update_token_gen_rate(tokens_per_second, "vllm")
                    
                    # Create event data
                    data = {
                        "token": new_text,
                        "index": tokens_generated,
                        "is_last": request_output.finished
                    }
                    
                    # Yield SSE event
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    # Update metrics
                    generated_tokens.labels(engine="vllm").inc(len(new_tokens))
            
            # Sleep a bit to avoid busy waiting
            await asyncio.sleep(0.01)
        
        # Send final event
        yield f"data: {json.dumps({'is_last': True, 'token': '', 'index': tokens_generated})}\n\n"
        
        # Update inference request counter
        inference_requests.labels(engine="vllm").inc()
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        if "CUDA out of memory" in str(e):
            oom_counter.labels(engine="vllm").inc()
        # Send error event
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        # Always try to clear the request
        try:
            ENGINE.abort_request(request_id)
        except Exception:
            pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
