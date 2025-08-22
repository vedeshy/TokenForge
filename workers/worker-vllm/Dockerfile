# Build stage
FROM nvidia/cuda:12.2.0-devel-ubuntu22.04 as builder

WORKDIR /app

# Install Python and build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt -v

# Final stage
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

WORKDIR /app

# Install Python runtime
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/lib/python3/dist-packages /usr/lib/python3/dist-packages

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
