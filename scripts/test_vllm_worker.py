#!/usr/bin/env python3
import argparse
import os
import sys
import time
import json
import requests
from typing import Dict, Any, Optional

def parse_args():
    parser = argparse.ArgumentParser(description="Test vLLM worker with a small model")
    parser.add_argument("--model", type=str, default="TinyLlama/TinyLlama-1.1B-Chat-v1.0", 
                        help="Model to test with")
    parser.add_argument("--port", type=int, default=8000, 
                        help="Port for the vLLM worker")
    parser.add_argument("--host", type=str, default="localhost", 
                        help="Host for the vLLM worker")
    parser.add_argument("--prompt", type=str, 
                        default="Explain what a KV cache is in language models in 3 sentences.",
                        help="Prompt to use for testing")
    return parser.parse_args()

def check_health(host: str, port: int) -> bool:
    """Check if the worker is healthy."""
    try:
        response = requests.get(f"http://{host}:{port}/healthz")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def run_inference(host: str, port: int, prompt: str, 
                 max_tokens: int = 128, 
                 temperature: float = 0.7,
                 top_p: float = 0.95) -> Optional[Dict[str, Any]]:
    """Run inference on the worker."""
    try:
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False
        }
        
        print(f"Sending request to http://{host}:{port}/infer")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        start_time = time.time()
        response = requests.post(
            f"http://{host}:{port}/infer",
            json=payload,
            timeout=60  # Longer timeout for model loading
        )
        end_time = time.time()
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
        
        # Add our own timing
        result["client_latency_ms"] = int((end_time - start_time) * 1000)
        
        return result
    except Exception as e:
        print(f"Inference failed: {e}")
        return None

def main():
    args = parse_args()
    
    print(f"Testing vLLM worker with model {args.model}")
    print(f"Checking if worker is healthy at {args.host}:{args.port}...")
    
    if not check_health(args.host, args.port):
        print("Worker is not healthy. Please make sure it's running.")
        sys.exit(1)
    
    print("Worker is healthy. Running inference...")
    
    result = run_inference(args.host, args.port, args.prompt)
    if result:
        print("\nInference successful!")
        print(f"Generated output: {result['output']}")
        print(f"Worker latency: {result['latency_ms']}ms")
        print(f"Client latency: {result['client_latency_ms']}ms")
        print(f"Tokens in: {result['tokens_in']}")
        print(f"Tokens out: {result['tokens_out']}")
        print(f"Runtime metadata: {json.dumps(result['runtime_meta'], indent=2)}")
    else:
        print("Inference failed.")
        sys.exit(1)
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
