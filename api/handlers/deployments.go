package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/tokenforge/llm-infra-bench/controlplane"
)

// DeploymentStatus represents the status of a model deployment
type DeploymentStatus struct {
	Model     string    `json:"model"`
	Runtime   string    `json:"runtime"`
	Quant     string    `json:"quant"`
	Status    string    `json:"status"`
	Endpoint  string    `json:"endpoint,omitempty"`
	Error     string    `json:"error,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// DeploymentsHandler returns all current deployments
func DeploymentsHandler(registry *controlplane.Registry) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		deployments := []DeploymentStatus{}
		
		// Get all deployments from the registry
		for _, entry := range registry.GetAll() {
			deployment := DeploymentStatus{
				Model:     entry.Model,
				Runtime:   entry.Runtime,
				Quant:     entry.Quant,
				Status:    entry.Status,
				Endpoint:  entry.ServiceURL,
				CreatedAt: entry.CreatedAt,
				UpdatedAt: entry.UpdatedAt,
			}
			
			deployments = append(deployments, deployment)
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(deployments)
	}
}

// DeploymentStatusHandler returns the status of a specific deployment
func DeploymentStatusHandler(registry *controlplane.Registry) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		model := chi.URLParam(r, "model")
		runtime := chi.URLParam(r, "runtime")
		
		if model == "" || runtime == "" {
			http.Error(w, "Missing model or runtime parameter", http.StatusBadRequest)
			return
		}
		
		entry, ok := registry.Get(model, runtime)
		if !ok {
			http.Error(w, "Deployment not found", http.StatusNotFound)
			return
		}
		
		deployment := DeploymentStatus{
			Model:     entry.Model,
			Runtime:   entry.Runtime,
			Quant:     entry.Quant,
			Status:    entry.Status,
			Endpoint:  entry.ServiceURL,
			CreatedAt: entry.CreatedAt,
			UpdatedAt: entry.UpdatedAt,
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(deployment)
	}
}
