#!/bin/bash
set -e

echo "Seeding models for development"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "kubectl is not installed. Please install it first: https://kubernetes.io/docs/tasks/tools/install-kubectl/"
    exit 1
fi

# Check if the tokenforge namespace exists
if ! kubectl get namespace tokenforge &> /dev/null; then
    echo "Namespace tokenforge does not exist. Please run dev_kind_up.sh first."
    exit 1
fi

# Deploy a stub model for testing
echo "Deploying stub model..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-vllm-stub
  namespace: tokenforge
  labels:
    app: worker
    runtime: vllm
    model: stub
spec:
  selector:
    matchLabels:
      app: worker
      runtime: vllm
      model: stub
  template:
    metadata:
      labels:
        app: worker
        runtime: vllm
        model: stub
    spec:
      containers:
      - name: worker
        image: ghcr.io/tokenforge/worker-vllm:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 8001
          name: metrics
        env:
        - name: MODEL_NAME
          value: stub-model
        - name: QUANT
          value: fp16
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: worker-vllm-stub
  namespace: tokenforge
  labels:
    app: worker
    runtime: vllm
    model: stub
spec:
  selector:
    app: worker
    runtime: vllm
    model: stub
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  - port: 8001
    targetPort: 8001
    name: metrics
EOF

# Register the model in the API
echo "Registering model in the API..."
kubectl run -it --rm --restart=Never curl --image=curlimages/curl -- \
  -X POST "http://api:8080/api/v1/deploy" \
  -H "Content-Type: application/json" \
  -d '{"model":"stub-model","runtime":"vllm","quant":"fp16"}'

echo "Model seeding complete!"
