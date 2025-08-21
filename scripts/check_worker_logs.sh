#!/bin/bash

echo "Checking vLLM worker logs"
docker logs -f tokenforge-vllm-worker
