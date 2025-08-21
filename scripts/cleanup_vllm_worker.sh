#!/bin/bash

echo "Stopping and removing vLLM worker container"
docker stop tokenforge-vllm-worker || true
docker rm tokenforge-vllm-worker || true

echo "Cleanup complete"
