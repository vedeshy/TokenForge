"""
Memory profiling utilities for TokenForge.
"""

import os
import time
import threading
import tracemalloc
import psutil
from typing import Dict, List, Any, Optional, Union, Callable
from functools import wraps

# Try to import GPU monitoring libraries
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_PYNVML = True
except (ImportError, Exception):
    HAS_PYNVML = False

class MemoryProfiler:
    """Memory profiler for tracking CPU and GPU memory usage."""
    
    def __init__(self, interval: float = 0.1, track_gpu: bool = True):
        """
        Initialize memory profiler.
        
        Args:
            interval: Sampling interval in seconds
            track_gpu: Whether to track GPU memory
        """
        self.interval = interval
        self.track_gpu = track_gpu and (HAS_TORCH or HAS_PYNVML)
        self.running = False
        self.thread = None
        self.process = psutil.Process(os.getpid())
        self.samples = {
            "timestamps": [],
            "cpu_memory": [],
            "gpu_memory": []
        }
        
        # Initialize tracemalloc
        tracemalloc.start()
    
    def start(self):
        """Start memory profiling."""
        if self.running:
            return
        
        self.running = True
        self.samples = {
            "timestamps": [],
            "cpu_memory": [],
            "gpu_memory": []
        }
        
        # Start profiling thread
        self.thread = threading.Thread(target=self._profile_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self) -> Dict[str, Any]:
        """
        Stop memory profiling.
        
        Returns:
            Dictionary of memory samples
        """
        if not self.running:
            return self.samples
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        
        # Get peak memory usage
        current, peak = tracemalloc.get_traced_memory()
        self.samples["peak_traced_memory"] = peak
        
        # Stop tracemalloc
        tracemalloc.stop()
        
        return self.samples
    
    def _profile_loop(self):
        """Internal loop for memory profiling."""
        while self.running:
            try:
                # Record timestamp
                self.samples["timestamps"].append(time.time())
                
                # Get CPU memory usage
                cpu_memory = self.process.memory_info().rss
                self.samples["cpu_memory"].append(cpu_memory)
                
                # Get GPU memory usage if available
                if self.track_gpu:
                    gpu_memory = get_gpu_memory_usage()
                    
                    # If GPU is available, extract total allocated memory
                    if "gpu_available" not in gpu_memory or gpu_memory["gpu_available"] is not False:
                        # Extract a single value for total GPU memory used
                        total_gpu_memory = 0
                        for key, value in gpu_memory.items():
                            if "allocated" in key or "used" in key:
                                total_gpu_memory += value
                        
                        self.samples["gpu_memory"].append(total_gpu_memory)
                    else:
                        # No GPU available
                        self.samples["gpu_memory"].append(0)
                
                # Sleep for the specified interval
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error in memory profiling: {e}")
                break

def get_memory_usage() -> Dict[str, int]:
    """
    Get current memory usage.
    
    Returns:
        Dictionary with memory usage information
    """
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # Get tracemalloc info if active
    traced_memory = (0, 0)
    if tracemalloc.is_tracing():
        traced_memory = tracemalloc.get_traced_memory()
    
    return {
        "rss": memory_info.rss,  # Resident Set Size
        "vms": memory_info.vms,  # Virtual Memory Size
        "shared": getattr(memory_info, "shared", 0),  # Shared memory
        "traced_current": traced_memory[0],  # Current traced memory
        "traced_peak": traced_memory[1],  # Peak traced memory
    }

def get_gpu_memory_usage() -> Dict[str, int]:
    """
    Get current GPU memory usage.
    
    Returns:
        Dictionary with GPU memory usage information
    """
    result = {}
    
    # Try PyTorch first
    if HAS_TORCH and torch.cuda.is_available():
        try:
            for i in range(torch.cuda.device_count()):
                result[f"gpu_{i}_allocated"] = torch.cuda.memory_allocated(i)
                result[f"gpu_{i}_reserved"] = torch.cuda.memory_reserved(i)
            return result
        except Exception as e:
            print(f"Error getting PyTorch GPU memory: {e}")
    
    # Try NVML as fallback
    if HAS_PYNVML:
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                result[f"gpu_{i}_used"] = info.used
                result[f"gpu_{i}_total"] = info.total
            return result
        except Exception as e:
            print(f"Error getting NVML GPU memory: {e}")
    
    # No GPU info available
    return {"gpu_available": False}

def profile_memory(func=None, *, interval: float = 0.1, track_gpu: bool = True):
    """
    Decorator for memory profiling a function.
    
    Args:
        func: Function to profile
        interval: Sampling interval in seconds
        track_gpu: Whether to track GPU memory
        
    Returns:
        Wrapped function that profiles memory usage
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Start profiling
            profiler = MemoryProfiler(interval=interval, track_gpu=track_gpu)
            profiler.start()
            
            try:
                # Call the function
                result = f(*args, **kwargs)
                
                # Add memory profile to the result if it's a dict
                memory_profile = profiler.stop()
                if isinstance(result, dict):
                    result["memory_profile"] = memory_profile
                
                return result
            finally:
                # Make sure profiling is stopped
                profiler.stop()
        
        return wrapper
    
    # Handle both @profile_memory and @profile_memory(interval=0.5)
    if func is None:
        return decorator
    else:
        return decorator(func)
