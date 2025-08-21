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
from report import generate_report

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
            
            if data["status"] == "ready":
                logger.info(f"Deployment ready at {endpoint}")
                return endpoint
            else:
                logger.error(f"Deployment failed: {data}")
                return None
    
    async def warmup(self, endpoint: str, count: int = 200) -> bool:
        """Warm up the model with a number of requests."""
        logger.info(f"Warming up model with {count} requests")
        
        async with httpx.AsyncClient(timeout=30) as client:
            for i in range(count):
                try:
                    response = await client.post(
                        f"{endpoint}/infer",
                        json={
                            "prompt": "Hello, world!",
                            "max_tokens": 10,
                            "temperature": 0.0,
                            "top_p": 1.0,
                            "stream": False,
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Warmup request {i} failed: {response.text}")
                except Exception as e:
                    logger.warning(f"Warmup request {i} failed: {e}")
                
                if i % 10 == 0:
                    logger.info(f"Warmup progress: {i}/{count}")
        
        logger.info("Warmup complete")
        return True
    
    async def run_workload(self, endpoint: str, runtime: str, workload: Dict) -> Dict:
        """Run a single workload against a model endpoint."""
        logger.info(f"Running workload {workload['name']} against {runtime}")
        
        # Generate prompts based on workload parameters
        prompts = self._generate_prompts(workload["name"], workload["prompt_len"], 100)
        
        # Prepare results
        results = {
            "name": workload["name"],
            "runtime": runtime,
            "qps": workload["qps"],
            "duration_s": workload["duration_s"],
            "prompt_len": workload["prompt_len"],
            "gen_tokens": workload["gen_tokens"],
            "requests": [],
        }
        
        # Calculate delay between requests to achieve target QPS
        delay = 1.0 / workload["qps"]
        
        # Run the workload
        start_time = time.time()
        end_time = start_time + workload["duration_s"]
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
                        
                        # Record request metrics
                        results["requests"].append({
                            "id": request_count,
                            "latency_ms": data["latency_ms"],
                            "tokens_in": data["tokens_in"],
                            "tokens_out": data["tokens_out"],
                            "error": None,
                        })
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
        latencies = [r["latency_ms"] for r in results["requests"] if r["error"] is None]
        tokens_in = sum(r["tokens_in"] for r in results["requests"] if r["error"] is None)
        tokens_out = sum(r["tokens_out"] for r in results["requests"] if r["error"] is None)
        errors = sum(1 for r in results["requests"] if r["error"] is not None)
        
        results["summary"] = {
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
        
        logger.info(f"Workload {workload['name']} complete: {results['summary']['successful_requests']} successful requests, {results['summary']['error_rate']*100:.2f}% error rate")
        
        return results
    
    def _generate_prompts(self, workload_name: str, target_length: int, count: int) -> List[str]:
        """Generate prompts for a workload."""
        prompts = []
        
        if workload_name == "qa-short":
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
            
            for _ in range(count):
                question_idx = _ % len(questions)
                prompt = base_prompt + questions[question_idx]
                
                # Pad to target length
                while len(prompt) < target_length:
                    prompt += " Please provide a detailed explanation."
                
                prompts.append(prompt[:target_length])
        
        elif workload_name == "code-long":
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
            
            for _ in range(count):
                task_idx = _ % len(tasks)
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
    
    async def run_benchmark(self) -> bool:
        """Run the benchmark for all runtimes and workloads."""
        logger.info(f"Starting benchmark run {self.run_id}")
        
        for runtime in self.config["runtimes"]:
            # Deploy model with this runtime
            endpoint = await self.deploy_model(runtime)
            if not endpoint:
                logger.error(f"Failed to deploy model with runtime {runtime}")
                continue
            
            # Warm up the model
            if not await self.warmup(endpoint):
                logger.error(f"Failed to warm up model with runtime {runtime}")
                continue
            
            # Run each workload
            for workload in self.config["workloads"]:
                workload_results = await self.run_workload(endpoint, runtime, workload)
                
                # Store results
                if workload["name"] not in self.results["workloads"]:
                    self.results["workloads"][workload["name"]] = []
                
                self.results["workloads"][workload["name"]].append(workload_results)
        
        # Save results
        return await self.save_results()
    
    async def save_results(self) -> bool:
        """Save benchmark results to S3 and generate report."""
        logger.info("Saving benchmark results")
        
        # Create directory for results
        os.makedirs(f"/tmp/{self.run_id}", exist_ok=True)
        
        # Save raw JSON results
        raw_path = f"/tmp/{self.run_id}/raw.json"
        with open(raw_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Generate CSV summary
        csv_path = f"/tmp/{self.run_id}/summary.csv"
        self._generate_csv(csv_path)
        
        # Generate HTML report
        html_path = f"/tmp/{self.run_id}/report.html"
        generate_report(self.results, html_path)
        
        # Upload to S3
        if self.s3_client:
            try:
                # Upload raw JSON
                self.s3_client.upload_file(
                    raw_path,
                    self.s3_bucket,
                    f"runs/{self.run_id}/raw.json",
                    ExtraArgs={"ContentType": "application/json"}
                )
                raw_url = f"s3://{self.s3_bucket}/runs/{self.run_id}/raw.json"
                
                # Upload CSV
                self.s3_client.upload_file(
                    csv_path,
                    self.s3_bucket,
                    f"runs/{self.run_id}/summary.csv",
                    ExtraArgs={"ContentType": "text/csv"}
                )
                csv_url = f"s3://{self.s3_bucket}/runs/{self.run_id}/summary.csv"
                
                # Upload HTML
                self.s3_client.upload_file(
                    html_path,
                    self.s3_bucket,
                    f"runs/{self.run_id}/report.html",
                    ExtraArgs={"ContentType": "text/html"}
                )
                html_url = f"s3://{self.s3_bucket}/runs/{self.run_id}/report.html"
                
                logger.info(f"Uploaded results to S3: {raw_url}")
                
                # Update run status in database
                await self._update_run_status("complete", html_url, csv_url, raw_url)
                
                return True
            except Exception as e:
                logger.error(f"Failed to upload results to S3: {e}")
                await self._update_run_status("failed")
                return False
        else:
            logger.warning("S3 client not initialized, skipping upload")
            await self._update_run_status("complete")
            return True
    
    def _generate_csv(self, path: str) -> None:
        """Generate CSV summary of benchmark results."""
        with open(path, "w") as f:
            # Write header
            f.write("workload,runtime,p50_latency_ms,p95_latency_ms,tokens_per_second,error_rate\n")
            
            # Write data
            for workload_name, workload_results in self.results["workloads"].items():
                for result in workload_results:
                    f.write(f"{workload_name},{result['runtime']},")
                    f.write(f"{result['summary']['p50_latency_ms']},")
                    f.write(f"{result['summary']['p95_latency_ms']},")
                    f.write(f"{result['summary']['tokens_per_second']},")
                    f.write(f"{result['summary']['error_rate']}\n")
    
    async def _update_run_status(self, status: str, html_url: str = None, csv_url: str = None, raw_url: str = None) -> None:
        """Update run status in database via API."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.api_url}/benchmarks/run/{self.run_id}/update",
                    json={
                        "status": status,
                        "html_url": html_url,
                        "csv_url": csv_url,
                        "raw_url": raw_url,
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to update run status: {response.text}")
        except Exception as e:
            logger.error(f"Failed to update run status: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Run LLM benchmarks")
    parser.add_argument("--run-id", required=True, help="Unique ID for this benchmark run")
    parser.add_argument("--config", required=True, help="Path to benchmark configuration YAML")
    args = parser.parse_args()
    
    runner = BenchmarkRunner(args.run_id, args.config)
    await runner.run_benchmark()

if __name__ == "__main__":
    asyncio.run(main())
