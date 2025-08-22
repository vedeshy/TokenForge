#!/usr/bin/env python3
"""
Test script for memory profiling.
"""

import sys
import os
import time
import json
import numpy as np
import matplotlib.pyplot as plt

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.profiling import MemoryProfiler, get_memory_usage, get_gpu_memory_usage
from harness.profiling.memory import profile_memory

def test_memory_usage_functions():
    """Test the memory usage functions."""
    print("\n=== Testing Memory Usage Functions ===\n")
    
    # Test get_memory_usage
    print("Current memory usage:")
    memory = get_memory_usage()
    for key, value in memory.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for subkey, subvalue in value.items():
                print(f"    {subkey}: {subvalue / (1024 * 1024):.2f} MB")
        else:
            print(f"  {key}: {value / (1024 * 1024):.2f} MB")
    
    # Test get_gpu_memory_usage if available
    print("\nGPU memory usage (if available):")
    try:
        gpu_memory = get_gpu_memory_usage()
        if "gpu_available" in gpu_memory and not gpu_memory["gpu_available"]:
            print("  No GPU available")
        else:
            for key, value in gpu_memory.items():
                print(f"  {key}: {value / (1024 * 1024):.2f} MB")
    except Exception as e:
        print(f"  Error getting GPU memory: {e}")

def memory_intensive_function():
    """A function that uses a lot of memory for testing."""
    # Create a large array to use memory
    large_array = np.zeros((1000, 1000, 10), dtype=np.float32)
    
    # Do some operations to prevent optimization
    for i in range(10):
        large_array += np.random.random((1000, 1000, 10)).astype(np.float32)
        time.sleep(0.1)
    
    return large_array.mean()

@profile_memory
def test_memory_decorator():
    """Test the memory profiling decorator."""
    print("\n=== Testing Memory Profiling Decorator ===\n")
    print("Running memory-intensive function with decorator...")
    result = memory_intensive_function()
    print(f"Function result: {result}")
    return {"result": result}

def test_memory_profiler_class():
    """Test the MemoryProfiler class."""
    print("\n=== Testing MemoryProfiler Class ===\n")
    
    # Create a profiler
    profiler = MemoryProfiler(interval=0.1)
    
    # Start profiling
    print("Starting memory profiling...")
    profiler.start()
    
    # Run some memory-intensive operations
    print("Running memory-intensive operations...")
    arrays = []
    for i in range(5):
        arrays.append(np.random.random((500, 500)))
        print(f"  Created array {i+1}")
        time.sleep(0.3)
    
    # Stop profiling
    print("Stopping memory profiling...")
    profile = profiler.stop()
    
    # Print summary
    print("\nMemory profile summary:")
    print(f"  Samples: {len(profile['timestamps'])}")
    if profile['cpu_memory']:
        min_mem = min(profile['cpu_memory']) / (1024 * 1024)
        max_mem = max(profile['cpu_memory']) / (1024 * 1024)
        print(f"  CPU memory range: {min_mem:.2f} MB - {max_mem:.2f} MB")
    
    # Plot the memory profile
    if profile['timestamps'] and profile['cpu_memory']:
        plt.figure(figsize=(10, 6))
        plt.plot([t - profile['timestamps'][0] for t in profile['timestamps']], 
                 [m / (1024 * 1024) for m in profile['cpu_memory']])
        plt.title('Memory Usage Over Time')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Memory Usage (MB)')
        plt.grid(True)
        
        # Save the plot
        plot_file = 'memory_profile_test.png'
        plt.savefig(plot_file)
        print(f"\nMemory profile plot saved to {plot_file}")

def test_memory_profiling_workflow():
    """Test the complete memory profiling workflow."""
    print("\n=== Testing Complete Memory Profiling Workflow ===\n")
    
    # Create a profiler with a specific interval
    profiler = MemoryProfiler(interval=0.2, track_gpu=True)
    
    try:
        # Start profiling
        print("Starting memory profiling...")
        profiler.start()
        
        # Simulate a workload
        print("Simulating a workload...")
        data = []
        for i in range(3):
            print(f"  Step {i+1}: Allocating memory...")
            # Allocate some memory
            data.append(np.random.random((1000, 1000)))
            time.sleep(0.5)
            
            print(f"  Step {i+1}: Processing data...")
            # Process the data
            for j in range(3):
                data[i] = data[i] * 1.01
                time.sleep(0.1)
        
        # Stop profiling and get results
        print("Stopping memory profiling...")
        profile = profiler.stop()
        
        # Save the profile to a file
        profile_file = 'memory_profile.json'
        with open(profile_file, 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            serializable_profile = {
                'timestamps': profile['timestamps'],
                'cpu_memory': [int(m) for m in profile['cpu_memory']],
                'gpu_memory': [int(m) if m else 0 for m in profile.get('gpu_memory', [])]
            }
            json.dump(serializable_profile, f, indent=2)
        
        print(f"Memory profile saved to {profile_file}")
        
        # Print some statistics
        print("\nMemory profile statistics:")
        print(f"  Duration: {profile['timestamps'][-1] - profile['timestamps'][0]:.2f} seconds")
        print(f"  Samples: {len(profile['timestamps'])}")
        if profile['cpu_memory']:
            min_mem = min(profile['cpu_memory']) / (1024 * 1024)
            max_mem = max(profile['cpu_memory']) / (1024 * 1024)
            avg_mem = sum(profile['cpu_memory']) / len(profile['cpu_memory']) / (1024 * 1024)
            print(f"  CPU memory: min={min_mem:.2f} MB, avg={avg_mem:.2f} MB, max={max_mem:.2f} MB")
    
    finally:
        # Make sure profiling is stopped
        if profiler.running:
            profiler.stop()

if __name__ == "__main__":
    test_memory_usage_functions()
    result = test_memory_decorator()
    if "memory_profile" in result:
        print(f"Memory profile captured by decorator: {len(result['memory_profile']['timestamps'])} samples")
    test_memory_profiler_class()
    test_memory_profiling_workflow()
    print("\nMemory profiling tests completed!")
