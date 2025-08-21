package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/tokenforge/llm-infra-bench/controlplane"
	"github.com/tokenforge/llm-infra-bench/controlplane/k8s"
)

type DeployRequest struct {
	Model   string `json:"model"`
	Runtime string `json:"runtime"`
	Quant   string `json:"quant"`
}

type DeployResponse struct {
	Endpoint   string    `json:"endpoint"`
	Status     string    `json:"status"`
	DeployedAt time.Time `json:"deployed_at"`
	K8s        struct {
		Namespace  string `json:"namespace"`
		Deployment string `json:"deployment"`
		Service    string `json:"service"`
	} `json:"k8s"`
}

// DeployHandler handles model deployment requests
func DeployHandler(registry *controlplane.Registry) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req DeployRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		// Validate request
		if req.Model == "" || req.Runtime == "" {
			http.Error(w, "model and runtime are required", http.StatusBadRequest)
			return
		}

		// Create deployment
		serviceURL, namespace, deploymentName, serviceName, err := k8s.DeployWorker(r.Context(), req.Model, req.Runtime, req.Quant)
		if err != nil {
			http.Error(w, "failed to deploy worker: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// Register the service in registry
		registry.Set(req.Model, req.Runtime, serviceURL)

		// Prepare response
		resp := DeployResponse{
			Endpoint:   serviceURL,
			Status:     "deploying", // Initial status
			DeployedAt: time.Now(),
		}
		resp.K8s.Namespace = namespace
		resp.K8s.Deployment = deploymentName
		resp.K8s.Service = serviceName

		// TODO: Poll for readiness and update status to "ready" when available

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(resp)
	}
}
