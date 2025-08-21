#!/bin/bash
set -e

echo "Setting up local Kubernetes cluster with Kind"

# Check if Kind is installed
if ! command -v kind &> /dev/null; then
    echo "Kind is not installed. Please install it first: https://kind.sigs.k8s.io/docs/user/quick-start/"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "kubectl is not installed. Please install it first: https://kubernetes.io/docs/tasks/tools/install-kubectl/"
    exit 1
fi

# Create Kind cluster with GPU support (if available)
echo "Creating Kind cluster..."
cat <<EOF | kind create cluster --name tokenforge --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraMounts:
  - hostPath: ./configs
    containerPath: /configs
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF

# Install NVIDIA device plugin (if GPU is available)
if command -v nvidia-smi &> /dev/null; then
    echo "Installing NVIDIA device plugin..."
    kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
fi

# Install Ingress NGINX controller
echo "Installing NGINX ingress controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for ingress controller to be ready
echo "Waiting for NGINX ingress controller to be ready..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# Create namespace
echo "Creating tokenforge namespace..."
kubectl create namespace tokenforge

# Apply Kubernetes manifests
echo "Applying Kubernetes manifests..."
kubectl apply -f deploy/helm/infra/templates/

# Create PostgreSQL and MinIO deployments
echo "Deploying PostgreSQL and MinIO..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: tokenforge
spec:
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          value: postgres
        - name: POSTGRES_DB
          value: tokenforge
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        - name: init-scripts
          mountPath: /docker-entrypoint-initdb.d
      volumes:
      - name: postgres-data
        emptyDir: {}
      - name: init-scripts
        configMap:
          name: postgres-init-scripts
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: tokenforge
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-init-scripts
  namespace: tokenforge
data:
  0001_init.sql: |
    CREATE TABLE runs (
      id TEXT PRIMARY KEY,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      status TEXT NOT NULL,
      model TEXT NOT NULL,
      runtimes TEXT[] NOT NULL,
      config_yaml TEXT NOT NULL,
      html_url TEXT,
      csv_url TEXT,
      raw_url TEXT
    );
  0002_status_idx.sql: |
    CREATE INDEX runs_status_created_idx ON runs(status, created_at DESC);
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: tokenforge
spec:
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
      - name: minio
        image: minio/minio
        args:
        - server
        - /data
        - --console-address
        - ":9001"
        env:
        - name: MINIO_ROOT_USER
          value: minioadmin
        - name: MINIO_ROOT_PASSWORD
          value: minioadmin
        ports:
        - containerPort: 9000
        - containerPort: 9001
        volumeMounts:
        - name: minio-data
          mountPath: /data
      volumes:
      - name: minio-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: minio
  namespace: tokenforge
spec:
  selector:
    app: minio
  ports:
  - port: 9000
    targetPort: 9000
    name: api
  - port: 9001
    targetPort: 9001
    name: console
---
apiVersion: batch/v1
kind: Job
metadata:
  name: minio-setup
  namespace: tokenforge
spec:
  template:
    spec:
      containers:
      - name: mc
        image: minio/mc
        command: ["/bin/sh", "-c"]
        args:
        - |
          sleep 5
          mc config host add myminio http://minio:9000 minioadmin minioadmin
          mc mb myminio/tokenforge-benchmarks
          mc policy set public myminio/tokenforge-benchmarks
      restartPolicy: OnFailure
EOF

# Deploy Prometheus and Grafana
echo "Deploying Prometheus and Grafana..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: tokenforge
spec:
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: prometheus-config
          mountPath: /etc/prometheus/prometheus.yml
          subPath: prometheus.yml
      volumes:
      - name: prometheus-config
        configMap:
          name: prometheus-config
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: tokenforge
spec:
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: tokenforge
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    scrape_configs:
      - job_name: 'api'
        static_configs:
          - targets: ['api:8080']
      - job_name: 'workers'
        kubernetes_sd_configs:
          - role: service
            selectors:
              - role: service
                label: "app=worker"
        relabel_configs:
          - source_labels: [__meta_kubernetes_service_label_app]
            regex: worker
            action: keep
          - source_labels: [__meta_kubernetes_service_label_runtime]
            target_label: runtime
          - source_labels: [__meta_kubernetes_service_label_model]
            target_label: model
          - source_labels: [__address__]
            target_label: __address__
            regex: (.+)(?::\d+)?
            replacement: $1:8001
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: tokenforge
spec:
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_USER
          value: admin
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: admin
        volumeMounts:
        - name: grafana-dashboards
          mountPath: /etc/grafana/provisioning/dashboards
      volumes:
      - name: grafana-dashboards
        configMap:
          name: grafana-dashboards
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: tokenforge
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
  namespace: tokenforge
data:
  dashboard.json: |
    {
      "annotations": {
        "list": [
          {
            "builtIn": 1,
            "datasource": {
              "type": "grafana",
              "uid": "-- Grafana --"
            },
            "enable": true,
            "hide": true,
            "iconColor": "rgba(0, 211, 255, 1)",
            "name": "Annotations & Alerts",
            "type": "dashboard"
          }
        ]
      },
      "editable": true,
      "fiscalYearStartMonth": 0,
      "graphTooltip": 0,
      "id": 1,
      "links": [],
      "liveNow": false,
      "panels": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "color": {
                "mode": "palette-classic"
              },
              "custom": {
                "axisCenteredZero": false,
                "axisColorMode": "text",
                "axisLabel": "",
                "axisPlacement": "auto",
                "barAlignment": 0,
                "drawStyle": "line",
                "fillOpacity": 0.1,
                "gradientMode": "none",
                "hideFrom": {
                  "legend": false,
                  "tooltip": false,
                  "viz": false
                },
                "lineInterpolation": "linear",
                "lineWidth": 1,
                "pointSize": 5,
                "scaleDistribution": {
                  "type": "linear"
                },
                "showPoints": "auto",
                "spanNulls": false,
                "stacking": {
                  "group": "A",
                  "mode": "none"
                },
                "thresholdsStyle": {
                  "mode": "off"
                }
              },
              "mappings": [],
              "thresholds": {
                "mode": "absolute",
                "steps": [
                  {
                    "color": "green",
                    "value": null
                  },
                  {
                    "color": "red",
                    "value": 80
                  }
                ]
              },
              "unit": "ms"
            },
            "overrides": []
          },
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "id": 1,
          "options": {
            "legend": {
              "calcs": [
                "mean",
                "max",
                "min"
              ],
              "displayMode": "table",
              "placement": "bottom",
              "showLegend": true
            },
            "tooltip": {
              "mode": "single",
              "sort": "none"
            }
          },
          "targets": [
            {
              "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
              },
              "editorMode": "code",
              "expr": "histogram_quantile(0.95, sum(rate(inference_latency_ms_bucket{runtime=\"$runtime\"}[5m])) by (le, runtime))",
              "legendFormat": "{{runtime}}",
              "range": true,
              "refId": "A"
            }
          ],
          "title": "p95 Inference Latency",
          "type": "timeseries"
        }
      ],
      "refresh": "10s",
      "schemaVersion": 38,
      "style": "dark",
      "tags": [],
      "templating": {
        "list": [
          {
            "current": {
              "selected": false,
              "text": "vllm",
              "value": "vllm"
            },
            "datasource": {
              "type": "prometheus",
              "uid": "prometheus"
            },
            "definition": "label_values(runtime)",
            "hide": 0,
            "includeAll": false,
            "label": "Runtime",
            "multi": false,
            "name": "runtime",
            "options": [],
            "query": {
              "query": "label_values(runtime)",
              "refId": "StandardVariableQuery"
            },
            "refresh": 1,
            "regex": "",
            "skipUrlSync": false,
            "sort": 0,
            "type": "query"
          }
        ]
      },
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "timepicker": {},
      "timezone": "",
      "title": "LLM Inference Dashboard",
      "uid": "llm-inference",
      "version": 1,
      "weekStart": ""
    }
EOF

# Deploy API server
echo "Deploying API server..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: tokenforge
spec:
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: ghcr.io/tokenforge/api:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          value: postgres://postgres:postgres@postgres:5432/tokenforge
        - name: S3_ENDPOINT
          value: http://minio:9000
        - name: AWS_ACCESS_KEY_ID
          value: minioadmin
        - name: AWS_SECRET_ACCESS_KEY
          value: minioadmin
        - name: S3_BUCKET
          value: tokenforge-benchmarks
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: tokenforge
spec:
  selector:
    app: api
  ports:
  - port: 8080
    targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: tokenforge
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api
            port:
              number: 8080
EOF

echo "Setup complete! Your local Kubernetes cluster is ready."
echo "You can access the API at http://localhost/api/v1"
echo "Grafana is available at http://localhost:3000 (admin/admin)"
echo "MinIO console is available at http://localhost:9001 (minioadmin/minioadmin)"
