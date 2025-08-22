#!/usr/bin/env python3
"""
Test script for running a benchmark with all advanced features.
"""

import sys
import os
import argparse
import asyncio
import json
from datetime import datetime

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.run_bench import BenchmarkRunner

async def run_test_benchmark(config_file):
    """Run a test benchmark using the specified config file."""
    print(f"\n=== Running Test Benchmark with {config_file} ===\n")
    
    # Create a unique run ID
    run_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create and run the benchmark
    runner = BenchmarkRunner(run_id, config_file)
    success = await runner.run_benchmark()
    
    if success:
        print(f"\nBenchmark completed successfully!")
        print(f"Results saved to /tmp/{run_id}/")
        
        # Print a summary of the results
        print("\nBenchmark Summary:")
        for workload_name, workload_results in runner.results["workloads"].items():
            print(f"\nWorkload: {workload_name}")
            for result in workload_results:
                print(f"  Runtime: {result['runtime']}")
                print(f"  p50 Latency: {result['summary']['p50_latency_ms']:.2f} ms")
                print(f"  Tokens/sec: {result['summary']['tokens_per_second']:.2f}")
                
                # Print evaluation metrics if available
                eval_metrics = [k for k in result['summary'].keys() if k.startswith('avg_') and 
                               ('rouge' in k or 'bleu' in k or 'factual' in k)]
                if eval_metrics:
                    print("  Quality Metrics:")
                    for metric in eval_metrics:
                        print(f"    {metric}: {result['summary'][metric]:.4f}")
                
                # Print memory profiling info if available
                if "memory_profile" in result:
                    profile = result["memory_profile"]
                    if "cpu_memory" in profile and profile["cpu_memory"]:
                        max_mem = max(profile["cpu_memory"]) / (1024 * 1024)
                        print(f"  Peak Memory: {max_mem:.2f} MB")
    else:
        print(f"\nBenchmark failed!")

def main():
    """Main function to run the test benchmark."""
    parser = argparse.ArgumentParser(description="Test advanced benchmarking features")
    parser.add_argument("--config", type=str, default="harness/workloads/template_benchmark.yaml",
                        help="Path to benchmark configuration file")
    args = parser.parse_args()
    
    # Check if the config file exists
    if not os.path.exists(args.config):
        print(f"Error: Config file {args.config} not found!")
        print("Available configs:")
        for config in [
            "harness/workloads/template_benchmark.yaml",
            "harness/workloads/evaluation_benchmark.yaml",
            "harness/workloads/memory_benchmark.yaml"
        ]:
            if os.path.exists(config):
                print(f"  - {config}")
        return
    
    # Run the benchmark
    asyncio.run(run_test_benchmark(args.config))

if __name__ == "__main__":
    main()
