FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

WORKDIR /app

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY metrics.py .

# Expose ports
EXPOSE 8000 8001

# Set environment variables
ENV MODEL_NAME="meta-llama/Llama-3-8b-instruct"
ENV QUANT="fp16"
ENV MAX_MODEL_LEN="8192"

# Run the server
CMD ["python3", "server.py"]
