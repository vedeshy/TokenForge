.PHONY: build run test clean dev bench deploy-k8s

# Variables
DOCKER_REGISTRY ?= ghcr.io/tokenforge
VERSION ?= latest

# Build targets
build: build-api build-workers

build-api:
	@echo "Building API server..."
	cd api && go build -o ../bin/api

build-workers:
	@echo "Building worker Docker images..."
	docker build -t $(DOCKER_REGISTRY)/worker-vllm:$(VERSION) workers/worker-vllm
	docker build -t $(DOCKER_REGISTRY)/worker-transformers:$(VERSION) workers/worker-transformers

# Run targets
run: run-api

run-api:
	@echo "Running API server..."
	./bin/api

# Development targets
dev:
	@echo "Starting development environment..."
	docker-compose up -d

dev-down:
	@echo "Stopping development environment..."
	docker-compose down

# Benchmark targets
bench:
	@echo "Running benchmark..."
	python harness/run_bench.py --run-id run_$(shell date +%Y%m%d%H%M%S) --config configs/benchmark.yaml

# Kubernetes targets
deploy-k8s:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f deploy/helm/infra/templates/

# Clean targets
clean:
	@echo "Cleaning up..."
	rm -rf bin/
	docker-compose down --volumes

# Test targets
test:
	@echo "Running tests..."
	go test -v ./...

# Database targets
db-migrate:
	@echo "Running database migrations..."
	psql -h localhost -U postgres -d tokenforge -f db/migrations/0001_init.sql
	psql -h localhost -U postgres -d tokenforge -f db/migrations/0002_status_idx.sql

# Docker targets
docker-push:
	@echo "Pushing Docker images..."
	docker push $(DOCKER_REGISTRY)/worker-vllm:$(VERSION)
	docker push $(DOCKER_REGISTRY)/worker-transformers:$(VERSION)
