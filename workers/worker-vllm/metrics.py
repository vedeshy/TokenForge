#!/usr/bin/env python3
import time
import threading
from typing import Dict

import torch
from prometheus_client import Gauge, Histogram

# Define metrics
vram_bytes = Gauge(
    "vram_bytes", "GPU VRAM usage in bytes", ["engine"]
)
kv_cache_bytes = Gauge(
    "kv_cache_bytes", "KV cache memory usage in bytes", ["engine"]
)

# Streaming-specific metrics
ttft_ms = Histogram(
    "ttft_ms_bucket", "Time to first token in milliseconds", ["engine"]
)
token_gen_rate = Gauge(
    "token_gen_rate", "Token generation rate (tokens/sec)", ["engine"]
)
inter_token_latency_ms = Histogram(
    "inter_token_latency_ms_bucket", "Time between token generations in milliseconds", ["engine"]
)

def setup_metrics(engine_name: str = "vllm"):
    """
    Setup periodic metrics collection for GPU memory usage.
    
    Args:
        engine_name: Name of the LLM engine
    """
    if not torch.cuda.is_available():
        return
    
    def collect_metrics():
        while True:
            try:
                # Collect GPU memory usage
                vram_bytes.labels(engine=engine_name).set(torch.cuda.memory_allocated())
                
                # Sleep for 5 seconds
                time.sleep(5)
            except Exception as e:
                print(f"Error collecting metrics: {e}")
                time.sleep(10)
    
    # Start metrics collection in a background thread
    thread = threading.Thread(target=collect_metrics, daemon=True)
    thread.start()

def update_kv_cache_size(size_bytes: int, engine_name: str = "vllm"):
    """
    Update KV cache size metric.
    
    Args:
        size_bytes: Size of KV cache in bytes
        engine_name: Name of the LLM engine
    """
    kv_cache_bytes.labels(engine=engine_name).set(size_bytes)

def record_ttft(latency_ms: float, engine_name: str = "vllm"):
    """
    Record time to first token metric.
    
    Args:
        latency_ms: Time to first token in milliseconds
        engine_name: Name of the LLM engine
    """
    ttft_ms.labels(engine=engine_name).observe(latency_ms)

def update_token_gen_rate(tokens_per_second: float, engine_name: str = "vllm"):
    """
    Update token generation rate metric.
    
    Args:
        tokens_per_second: Token generation rate in tokens/sec
        engine_name: Name of the LLM engine
    """
    token_gen_rate.labels(engine=engine_name).set(tokens_per_second)

def record_inter_token_latency(latency_ms: float, engine_name: str = "vllm"):
    """
    Record inter-token latency metric.
    
    Args:
        latency_ms: Time between token generations in milliseconds
        engine_name: Name of the LLM engine
    """
    inter_token_latency_ms.labels(engine=engine_name).observe(latency_ms)
