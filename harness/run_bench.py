#!/usr/bin/env python3
import os
import sys
import time
import json
import yaml
import argparse
import asyncio
import logging
import statistics
from typing import Dict, List, Any
from datetime import datetime

import httpx
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import local modules
from harness.report import generate_report
from harness.templates import utils as template_utils
from harness.evaluation import evaluate_response
from harness.evaluation.references import get_reference_for_question, get_reference_for_logical_problem, get_reference_for_code
from harness.profiling import MemoryProfiler

class BenchmarkRunner:
    def __init__(self, run_id: str, config_path: str):
        self.run_id = run_id
        self.config_path = config_path
        self.config = self._load_config()
        self.api_url = os.environ.get("API_URL", "http://localhost:8080/api/v1")
        self.s3_client = self._init_s3_client()
        self.s3_bucket = os.environ.get("S3_BUCKET", "tokenforge-benchmarks")
        self.results = {
            "run_id": run_id,
            "model": self.config["model"],
            "runtimes": self.config["runtimes"],
            "timestamp": datetime.now().isoformat(),
            "workloads": {},
        }
    
    def _load_config(self) -> Dict:
        """Load benchmark configuration from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)
    
    def _init_s3_client(self):
        """Initialize S3 client for artifact storage."""
        try:
            endpoint_url = os.environ.get("S3_ENDPOINT", None)
            return boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            return None
    
    async def deploy_model(self, runtime: str) -> str:
        """Deploy a model with the specified runtime."""
        logger.info(f"Deploying model {self.config['model']} with runtime {runtime}")
        
        async with httpx.AsyncClient(timeout=600) as client:
            response = await client.post(
                f"{self.api_url}/deploy",
                json={
                    "model": self.config["model"],
                    "runtime": runtime,
                    "quant": "fp16",  # Default to fp16
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to deploy model: {response.text}")
                return None
            
            data = response.json()
            endpoint = data["endpoint"]
            
            # Wait for deployment to be ready
            while data["status"] == "deploying":
                logger.info(f"Waiting for deployment to be ready...")
                await asyncio.sleep(10)
                
                # Check deployment status
                response = await client.post(
                    f"{self.api_url}/deploy",
                    json={
                        "model": self.config["model"],
                        "runtime": runtime,
                        "quant": "fp16",
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to check deployment status: {response.text}")
                    return None
                
                data = response.json()
            
            logger.info(f"Model deployed successfully at {endpoint}")
            return endpoint
    
    async def warmup(self, endpoint: str, count: int = 5) -> bool:
        """Perform warmup requests to the model."""
        logger.info(f"Warming up model with {count} requests")
        
        async with httpx.AsyncClient(timeout=60) as client:
            for i in range(count):
                try:
                    response = await client.post(
                        f"{endpoint}/infer",
                        json={
                            "prompt": "This is a warmup request.",
                            "max_tokens": 10,
                            "temperature": 0.2,
                            "top_p": 0.95,
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Warmup request failed: {response.text}")
                    
                    logger.info(f"Warmup progress: {i}/{count}")
                except Exception as e:
                    logger.warning(f"Warmup request failed: {e}")
        
        logger.info("Warmup complete")
        return True
    
    async def run_workload(self, endpoint: str, runtime: str, workload: Dict) -> Dict:
        """Run a single workload against a model endpoint."""
        logger.info(f"Running workload {workload['name']} against {runtime}")
        
        # Generate prompts based on workload parameters
        prompts = self._generate_prompts(workload["name"], workload["prompt_len"], 100)
        
        # Determine if this is a streaming workload
        is_streaming = workload.get("stream", False)
        
        # Prepare results
        results = {
            "name": workload["name"],
            "runtime": runtime,
            "qps": workload["qps"],
            "duration_s": workload["duration_s"],
            "prompt_len": workload["prompt_len"],
            "gen_tokens": workload["gen_tokens"],
            "stream": is_streaming,
            "requests": [],
        }
        
        # Calculate delay between requests to achieve target QPS
        delay = 1.0 / workload["qps"]
        
        # Run the workload
        start_time = time.time()
        end_time = start_time + workload["duration_s"]
        request_count = 0
        
        # Start memory profiling if enabled
        memory_profiler = None
        if workload.get("profile_memory", False):
            memory_profiler = MemoryProfiler(interval=0.5, track_gpu=True)
            memory_profiler.start()
            logger.info("Memory profiling started")
        
        try:
            if is_streaming:
                # Run streaming benchmark
                results = await self._run_streaming_workload(endpoint, prompts, workload, results, delay, end_time)
            else:
                # Run regular benchmark
                results = await self._run_regular_workload(endpoint, prompts, workload, results, delay, end_time)
                
            # Add memory profiling results if available
            if memory_profiler:
                memory_profile = memory_profiler.stop()
                results["memory_profile"] = memory_profile
                logger.info("Memory profiling completed")
        finally:
            # Make sure profiling is stopped
            if memory_profiler and memory_profiler.running:
                memory_profiler.stop()
        
        logger.info(f"Workload {workload['name']} complete: {results['summary']['successful_requests']} successful requests, {results['summary']['error_rate']*100:.2f}% error rate")
        
        return results
        
    async def _run_regular_workload(self, endpoint: str, prompts: List[str], workload: Dict, results: Dict, delay: float, end_time: float) -> Dict:
        """Run a regular (non-streaming) workload."""
        request_count = 0
        
        async with httpx.AsyncClient(timeout=60) as client:
            while time.time() < end_time:
                # Select prompt
                prompt_idx = request_count % len(prompts)
                prompt = prompts[prompt_idx]
                
                # Record request start time
                request_start = time.time()
                
                # Send request
                try:
                    response = await client.post(
                        f"{endpoint}/infer",
                        json={
                            "prompt": prompt,
                            "max_tokens": workload["gen_tokens"],
                            "temperature": 0.2,
                            "top_p": 0.95,
                            "stream": False,
                        }
                    )
                    
                    request_end = time.time()
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Get the output text
                        output = data["output"]
                        
                        # Capture memory usage if provided by worker
                        memory_usage = data.get("memory_usage", None)
                        
                        # Evaluate the response if evaluation is enabled
                        evaluation_metrics = {}
                        if workload.get("evaluate", False):
                            # Get the reference based on workload type
                            reference_data = {"reference": None, "facts": []}
                            
                            if workload["name"].startswith("qa") or "factual_qa" in workload["name"]:
                                reference_data = get_reference_for_question(prompt)
                            elif "logical_reasoning" in workload["name"]:
                                reference_data = get_reference_for_logical_problem(prompt)
                            elif "code" in workload["name"] or "function_implementation" in workload["name"]:
                                # Extract language and task from prompt
                                language = "Python"  # Default
                                if "language" in workload:
                                    language = workload["language"]
                                task = prompt
                                reference_data = get_reference_for_code(task, language)
                            
                            # Evaluate the response
                            if reference_data["reference"] or reference_data["facts"]:
                                evaluation_metrics = evaluate_response(
                                    output,
                                    reference=reference_data["reference"],
                                    facts=reference_data["facts"]
                                )
                        
                        # Record request metrics
                        request_data = {
                            "id": request_count,
                            "latency_ms": data["latency_ms"],
                            "tokens_in": data["tokens_in"],
                            "tokens_out": data["tokens_out"],
                            "error": None,
                        }
                        
                        # Add evaluation metrics if available
                        if evaluation_metrics:
                            request_data["evaluation"] = evaluation_metrics
                        
                        # Add memory usage if available
                        if memory_usage:
                            request_data["memory_usage"] = memory_usage
                            
                        results["requests"].append(request_data)
                    else:
                        # Record error
                        results["requests"].append({
                            "id": request_count,
                            "latency_ms": int((request_end - request_start) * 1000),
                            "tokens_in": 0,
                            "tokens_out": 0,
                            "error": response.text,
                        })
                except Exception as e:
                    request_end = time.time()
                    
                    # Record error
                    results["requests"].append({
                        "id": request_count,
                        "latency_ms": int((request_end - request_start) * 1000),
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "error": str(e),
                    })
                
                request_count += 1
                
                # Sleep to maintain QPS
                elapsed = time.time() - request_start
                if elapsed < delay:
                    await asyncio.sleep(delay - elapsed)
        
        # Calculate summary metrics
        return self._calculate_metrics(results, workload)
    
    async def _run_streaming_workload(self, endpoint: str, prompts: List[str], workload: Dict, results: Dict, delay: float, end_time: float) -> Dict:
        """Run a streaming workload."""
        request_count = 0
        
        async with httpx.AsyncClient(timeout=60) as client:
            while time.time() < end_time:
                # Select prompt
                prompt_idx = request_count % len(prompts)
                prompt = prompts[prompt_idx]
                
                # Record request start time
                request_start = time.time()
                
                # Send streaming request
                try:
                    async with client.stream(
                        "POST",
                        f"{endpoint}/infer",
                        json={
                            "prompt": prompt,
                            "max_tokens": workload["gen_tokens"],
                            "temperature": 0.2,
                            "top_p": 0.95,
                            "stream": True,
                        },
                        timeout=60
                    ) as response:
                        if response.status_code != 200:
                            # Record error
                            results["requests"].append({
                                "id": request_count,
                                "latency_ms": int((time.time() - request_start) * 1000),
                                "tokens_in": 0,
                                "tokens_out": 0,
                                "ttft_ms": 0,
                                "error": await response.text(),
                            })
                        else:
                            # Process streaming response
                            tokens = []
                            first_token_time = None
                            last_token_time = None
                            token_times = []
                            
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    try:
                                        data = json.loads(line[6:])
                                        current_time = time.time()
                                        
                                        # Record first token time
                                        if first_token_time is None and "token" in data and data["token"]:
                                            first_token_time = current_time
                                            ttft_ms = int((first_token_time - request_start) * 1000)
                                        
                                        # Record token and time
                                        if "token" in data and data["token"]:
                                            tokens.append(data["token"])
                                            token_times.append(current_time)
                                            last_token_time = current_time
                                        
                                        # Break if this is the last token
                                        if data.get("is_last", False):
                                            break
                                    except json.JSONDecodeError:
                                        pass
                            
                            # Calculate streaming metrics
                            request_end = time.time()
                            total_latency_ms = int((request_end - request_start) * 1000)
                            ttft_ms = int((first_token_time - request_start) * 1000) if first_token_time else 0
                            
                            # Calculate inter-token latencies
                            inter_token_latencies = []
                            if len(token_times) > 1:
                                for i in range(1, len(token_times)):
                                    inter_token_latencies.append((token_times[i] - token_times[i-1]) * 1000)
                            
                            # Combine tokens into full output
                            output = " ".join(tokens)
                            
                            # Evaluate the response if evaluation is enabled
                            evaluation_metrics = {}
                            if workload.get("evaluate", False):
                                # Get the reference based on workload type
                                reference_data = {"reference": None, "facts": []}
                                
                                if workload["name"].startswith("qa") or "factual_qa" in workload["name"]:
                                    reference_data = get_reference_for_question(prompt)
                                elif "logical_reasoning" in workload["name"]:
                                    reference_data = get_reference_for_logical_problem(prompt)
                                elif "code" in workload["name"] or "function_implementation" in workload["name"]:
                                    # Extract language and task from prompt
                                    language = "Python"  # Default
                                    if "language" in workload:
                                        language = workload["language"]
                                    task = prompt
                                    reference_data = get_reference_for_code(task, language)
                                
                                # Evaluate the response
                                if reference_data["reference"] or reference_data["facts"]:
                                    evaluation_metrics = evaluate_response(
                                        output,
                                        reference=reference_data["reference"],
                                        facts=reference_data["facts"]
                                    )
                            
                            # Record request metrics
                            request_data = {
                                "id": request_count,
                                "latency_ms": total_latency_ms,
                                "ttft_ms": ttft_ms,
                                "tokens_in": len(prompt.split()),
                                "tokens_out": len(tokens),
                                "inter_token_latency_ms": statistics.mean(inter_token_latencies) if inter_token_latencies else 0,
                                "token_gen_rate": len(tokens) / (last_token_time - first_token_time) if first_token_time and last_token_time and first_token_time != last_token_time else 0,
                                "error": None,
                            }
                            
                            # Add evaluation metrics if available
                            if evaluation_metrics:
                                request_data["evaluation"] = evaluation_metrics
                                
                            results["requests"].append(request_data)
                
                except Exception as e:
                    request_end = time.time()
                    
                    # Record error
                    results["requests"].append({
                        "id": request_count,
                        "latency_ms": int((request_end - request_start) * 1000),
                        "ttft_ms": 0,
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "inter_token_latency_ms": 0,
                        "token_gen_rate": 0,
                        "error": str(e),
                    })
                
                request_count += 1
                
                # Sleep to maintain QPS
                elapsed = time.time() - request_start
                if elapsed < delay:
                    await asyncio.sleep(delay - elapsed)
        
        # Calculate streaming-specific metrics
        return self._calculate_streaming_metrics(results, workload)
    
    def _calculate_metrics(self, results: Dict, workload: Dict) -> Dict:
        """Calculate metrics for regular workloads."""
        latencies = [r["latency_ms"] for r in results["requests"] if r["error"] is None]
        tokens_in = sum(r["tokens_in"] for r in results["requests"] if r["error"] is None)
        tokens_out = sum(r["tokens_out"] for r in results["requests"] if r["error"] is None)
        errors = sum(1 for r in results["requests"] if r["error"] is not None)
        
        summary = {
            "total_requests": len(results["requests"]),
            "successful_requests": len(results["requests"]) - errors,
            "error_rate": errors / len(results["requests"]) if len(results["requests"]) > 0 else 0,
            "p50_latency_ms": statistics.median(latencies) if latencies else 0,
            "p95_latency_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0),
            "p99_latency_ms": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else (max(latencies) if latencies else 0),
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "total_tokens_in": tokens_in,
            "total_tokens_out": tokens_out,
            "tokens_per_second": tokens_out / workload["duration_s"] if workload["duration_s"] > 0 else 0,
        }
        
        # Add evaluation metrics if available
        if workload.get("evaluate", False):
            # Check if we have evaluation metrics
            eval_requests = [r for r in results["requests"] if r.get("evaluation") is not None]
            if eval_requests:
                # Calculate average for each evaluation metric
                eval_metrics = {}
                for metric in eval_requests[0]["evaluation"].keys():
                    values = [r["evaluation"].get(metric, 0.0) for r in eval_requests]
                    eval_metrics[f"avg_{metric}"] = sum(values) / len(values)
                
                # Add to summary
                summary.update(eval_metrics)
        
        results["summary"] = summary
        return results
    
    def _calculate_streaming_metrics(self, results: Dict, workload: Dict) -> Dict:
        """Calculate metrics for streaming workloads."""
        # Standard metrics
        latencies = [r["latency_ms"] for r in results["requests"] if r["error"] is None]
        tokens_in = sum(r["tokens_in"] for r in results["requests"] if r["error"] is None)
        tokens_out = sum(r["tokens_out"] for r in results["requests"] if r["error"] is None)
        errors = sum(1 for r in results["requests"] if r["error"] is not None)
        
        # Streaming-specific metrics
        ttfts = [r["ttft_ms"] for r in results["requests"] if r["error"] is None and r["ttft_ms"] > 0]
        inter_token_latencies = [r["inter_token_latency_ms"] for r in results["requests"] if r["error"] is None and r["inter_token_latency_ms"] > 0]
        token_gen_rates = [r["token_gen_rate"] for r in results["requests"] if r["error"] is None and r["token_gen_rate"] > 0]
        
        summary = {
            "total_requests": len(results["requests"]),
            "successful_requests": len(results["requests"]) - errors,
            "error_rate": errors / len(results["requests"]) if len(results["requests"]) > 0 else 0,
            "p50_latency_ms": statistics.median(latencies) if latencies else 0,
            "p95_latency_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0),
            "p99_latency_ms": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else (max(latencies) if latencies else 0),
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "total_tokens_in": tokens_in,
            "total_tokens_out": tokens_out,
            "tokens_per_second": tokens_out / workload["duration_s"] if workload["duration_s"] > 0 else 0,
            
            # Streaming-specific metrics
            "p50_ttft_ms": statistics.median(ttfts) if ttfts else 0,
            "p95_ttft_ms": statistics.quantiles(ttfts, n=20)[18] if len(ttfts) >= 20 else (max(ttfts) if ttfts else 0),
            "avg_ttft_ms": statistics.mean(ttfts) if ttfts else 0,
            "avg_inter_token_latency_ms": statistics.mean(inter_token_latencies) if inter_token_latencies else 0,
            "avg_token_gen_rate": statistics.mean(token_gen_rates) if token_gen_rates else 0,
        }
        
        # Add evaluation metrics if available
        if workload.get("evaluate", False):
            # Check if we have evaluation metrics
            eval_requests = [r for r in results["requests"] if r.get("evaluation") is not None]
            if eval_requests:
                # Calculate average for each evaluation metric
                eval_metrics = {}
                for metric in eval_requests[0]["evaluation"].keys():
                    values = [r["evaluation"].get(metric, 0.0) for r in eval_requests]
                    eval_metrics[f"avg_{metric}"] = sum(values) / len(values)
                
                # Add to summary
                summary.update(eval_metrics)
        
        results["summary"] = summary
        return results
    
    def _generate_prompts(self, workload_name: str, target_length: int, count: int) -> List[str]:
        """Generate prompts for a workload."""
        prompts = []
        
        # Check if we have a template-based workload
        if "template" in workload_name:
            parts = workload_name.split("-")
            if len(parts) >= 2:
                template_name = parts[0]
                
                # Try to load template examples
                try:
                    examples_file = None
                    
                    # Look for examples in the templates directory
                    for category in ["reasoning", "coding", "creative", "qa"]:
                        potential_file = os.path.join("harness", "templates", category, f"{template_name}_examples.yaml")
                        if os.path.exists(potential_file):
                            examples_file = potential_file
                            break
                    
                    if examples_file:
                        with open(examples_file, 'r') as f:
                            examples = yaml.safe_load(f)
                            
                        # Generate prompts from examples
                        for i in range(count):
                            example_idx = i % len(examples)
                            example = examples[example_idx]
                            
                            try:
                                # Generate prompt from template
                                prompt = template_utils.generate_prompt(template_name, **example)
                                
                                # Pad or truncate to target length
                                if len(prompt) < target_length:
                                    prompt = prompt.ljust(target_length)
                                else:
                                    prompt = prompt[:target_length]
                                    
                                prompts.append(prompt)
                            except Exception as e:
                                logger.error(f"Error generating prompt from template {template_name}: {e}")
                                # Fall back to default prompt
                                prompts.append(self._generate_default_prompt(workload_name, target_length))
                    else:
                        logger.warning(f"No examples found for template {template_name}, using default prompts")
                        for _ in range(count):
                            prompts.append(self._generate_default_prompt(workload_name, target_length))
                except Exception as e:
                    logger.error(f"Error loading template examples: {e}")
                    for _ in range(count):
                        prompts.append(self._generate_default_prompt(workload_name, target_length))
            else:
                for _ in range(count):
                    prompts.append(self._generate_default_prompt(workload_name, target_length))
        elif workload_name == "qa-short":
            # Use factual_qa template
            try:
                examples_file = os.path.join("harness", "templates", "qa", "factual_qa_examples.yaml")
                with open(examples_file, 'r') as f:
                    examples = yaml.safe_load(f)
                
                for i in range(count):
                    example_idx = i % len(examples)
                    example = examples[example_idx]
                    
                    prompt = template_utils.generate_prompt("factual_qa", **example)
                    
                    # Pad to target length
                    while len(prompt) < target_length:
                        prompt += " Please provide a detailed explanation."
                    
                    prompts.append(prompt[:target_length])
            except Exception as e:
                logger.error(f"Error using factual_qa template: {e}")
                # Fall back to original implementation
                base_prompt = "Answer the following question concisely and accurately: "
                questions = [
                    "What is the capital of France?",
                    "Who wrote the novel '1984'?",
                    "What is the boiling point of water in Celsius?",
                    "What is the largest planet in our solar system?",
                    "Who painted the Mona Lisa?",
                    "What is the chemical symbol for gold?",
                    "What is the tallest mountain in the world?",
                    "What year did World War II end?",
                    "What is the speed of light?",
                    "Who is the current Secretary-General of the United Nations?",
                ]
                
                for i in range(count):
                    question_idx = i % len(questions)
                    prompt = base_prompt + questions[question_idx]
                    
                    # Pad to target length
                    while len(prompt) < target_length:
                        prompt += " Please provide a detailed explanation."
                    
                    prompts.append(prompt[:target_length])
        
        elif workload_name == "code-long":
            # Use function_implementation template
            try:
                examples_file = os.path.join("harness", "templates", "coding", "function_implementation_examples.yaml")
                with open(examples_file, 'r') as f:
                    examples = yaml.safe_load(f)
                
                for i in range(count):
                    example_idx = i % len(examples)
                    example = examples[example_idx]
                    
                    prompt = template_utils.generate_prompt("function_implementation", **example)
                    
                    # Pad to target length
                    while len(prompt) < target_length:
                        prompt += " The function should be efficient and handle edge cases properly."
                    
                    prompts.append(prompt[:target_length])
            except Exception as e:
                logger.error(f"Error using function_implementation template: {e}")
                # Fall back to original implementation
                base_prompt = "Write a Python function that "
                tasks = [
                    "sorts a list of integers using the quicksort algorithm.",
                    "implements a binary search tree with insert, delete, and search operations.",
                    "calculates the Fibonacci sequence up to n terms using dynamic programming.",
                    "performs matrix multiplication for two input matrices.",
                    "implements a simple HTTP server that serves static files.",
                    "parses a CSV file and performs basic data analysis.",
                    "implements a simple neural network with forward propagation.",
                    "creates a REST API using Flask with authentication.",
                    "implements a caching mechanism with LRU policy.",
                    "performs sentiment analysis on a given text using NLTK.",
                ]
                
                for i in range(count):
                    task_idx = i % len(tasks)
                    prompt = base_prompt + tasks[task_idx]
                    
                    # Pad to target length
                    while len(prompt) < target_length:
                        prompt += " The code should be well-documented and optimized for performance. Include error handling and edge cases. Provide examples of how to use the function."
                    
                    prompts.append(prompt[:target_length])
        
        else:
            # Generic prompt
            prompt = "Generate a response to this prompt. " * (target_length // 30)
            prompts = [prompt[:target_length]] * count
        
        return prompts
    
    def _generate_default_prompt(self, workload_name: str, target_length: int) -> str:
        """Generate a default prompt when templates are not available."""
        prompt = f"This is a benchmark prompt for workload {workload_name}. "
        while len(prompt) < target_length:
            prompt += "Please generate a high-quality response. "
        return prompt[:target_length]
    
    async def run_benchmark(self) -> bool:
        """Run the benchmark for all runtimes and workloads."""
        logger.info(f"Starting benchmark run {self.run_id}")
        
        # Create output directory
        output_dir = os.path.join("/tmp", self.run_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Run benchmarks for each runtime
        for runtime in self.config["runtimes"]:
            # Deploy the model
            endpoint = await self.deploy_model(runtime)
            if not endpoint:
                logger.error(f"Failed to deploy model for runtime {runtime}")
                continue
            
            # Warm up the model
            await self.warmup(endpoint)
            
            # Run each workload
            for workload in self.config["workloads"]:
                workload_result = await self.run_workload(endpoint, runtime, workload)
                
                # Store results
                if workload["name"] not in self.results["workloads"]:
                    self.results["workloads"][workload["name"]] = []
                
                self.results["workloads"][workload["name"]].append(workload_result)
        
        # Save results
        self._save_results(output_dir)
        
        # Generate report
        self._generate_report(output_dir)
        
        # Upload artifacts to S3
        if self.s3_client:
            self._upload_artifacts(output_dir)
        
        logger.info(f"Benchmark run {self.run_id} completed")
        return True
    
    def _save_results(self, output_dir: str) -> None:
        """Save benchmark results to disk."""
        # Save raw JSON results
        json_path = os.path.join(output_dir, "raw.json")
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Save CSV summary
        csv_path = os.path.join(output_dir, "summary.csv")
        with open(csv_path, "w") as f:
            # Write header
            f.write("workload,runtime,p50_latency_ms,p95_latency_ms,p99_latency_ms,tokens_per_second,error_rate\n")
            
            # Write data
            for workload_name, workload_results in self.results["workloads"].items():
                for result in workload_results:
                    summary = result["summary"]
                    f.write(f"{workload_name},{result['runtime']},{summary['p50_latency_ms']},{summary['p95_latency_ms']},{summary['p99_latency_ms']},{summary['tokens_per_second']},{summary['error_rate']}\n")
        
        logger.info(f"Results saved to {output_dir}")
    
    def _generate_report(self, output_dir: str) -> None:
        """Generate HTML report from benchmark results."""
        report_path = os.path.join(output_dir, "report.html")
        generate_report(self.results, report_path)
        logger.info(f"Report generated at {report_path}")
    
    def _upload_artifacts(self, output_dir: str) -> None:
        """Upload benchmark artifacts to S3."""
        try:
            # Upload raw results
            self.s3_client.upload_file(
                os.path.join(output_dir, "raw.json"),
                self.s3_bucket,
                f"{self.run_id}/raw.json"
            )
            
            # Upload summary CSV
            self.s3_client.upload_file(
                os.path.join(output_dir, "summary.csv"),
                self.s3_bucket,
                f"{self.run_id}/summary.csv"
            )
            
            # Upload HTML report
            self.s3_client.upload_file(
                os.path.join(output_dir, "report.html"),
                self.s3_bucket,
                f"{self.run_id}/report.html"
            )
            
            logger.info(f"Artifacts uploaded to S3 bucket {self.s3_bucket}")
        except Exception as e:
            logger.error(f"Failed to upload artifacts to S3: {e}")


async def main():
    parser = argparse.ArgumentParser(description="TokenForge Benchmark Runner")
    parser.add_argument("--run-id", type=str, default=f"run_{int(time.time())}", help="Unique ID for this benchmark run")
    parser.add_argument("--config", type=str, required=True, help="Path to benchmark configuration file")
    args = parser.parse_args()
    
    runner = BenchmarkRunner(args.run_id, args.config)
    await runner.run_benchmark()

if __name__ == "__main__":
    asyncio.run(main())