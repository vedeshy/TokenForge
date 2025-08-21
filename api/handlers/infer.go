package handlers

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"

	"github.com/tokenforge/llm-infra-bench/controlplane"
)

type InferRequest struct {
	Model       string  `json:"model"`
	Runtime     string  `json:"runtime"`
	Prompt      string  `json:"prompt"`
	MaxTokens   int     `json:"max_tokens"`
	Temperature float64 `json:"temperature"`
	TopP        float64 `json:"top_p"`
	Stream      bool    `json:"stream"`
}

type InferResponse struct {
	Output      string `json:"output"`
	LatencyMs   int    `json:"latency_ms"`
	TokensIn    int    `json:"tokens_in"`
	TokensOut   int    `json:"tokens_out"`
	RuntimeMeta struct {
		Engine  string `json:"engine"`
		Version string `json:"version"`
		Cuda    string `json:"cuda"`
		Gpu     string `json:"gpu"`
	} `json:"runtime_meta"`
}

// InferHandler handles inference requests
func InferHandler(registry *controlplane.Registry) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req InferRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		// Validate request
		if req.Model == "" || req.Runtime == "" || req.Prompt == "" {
			http.Error(w, "model, runtime, and prompt are required", http.StatusBadRequest)
			return
		}

		// Get worker endpoint from registry
		workerURL, found := registry.Get(req.Model, req.Runtime)
		if !found {
			http.Error(w, "model not deployed with specified runtime", http.StatusNotFound)
			return
		}

		// Prepare worker request
		workerReq := map[string]interface{}{
			"prompt":      req.Prompt,
			"max_tokens":  req.MaxTokens,
			"temperature": req.Temperature,
			"top_p":       req.TopP,
			"stream":      req.Stream,
		}

		reqBody, err := json.Marshal(workerReq)
		if err != nil {
			http.Error(w, "failed to encode request: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// Forward request to worker
		workerResp, err := http.Post(workerURL+"/infer", "application/json", bytes.NewBuffer(reqBody))
		if err != nil {
			http.Error(w, "failed to connect to worker: "+err.Error(), http.StatusServiceUnavailable)
			return
		}
		defer workerResp.Body.Close()

		// Read worker response
		respBody, err := io.ReadAll(workerResp.Body)
		if err != nil {
			http.Error(w, "failed to read worker response: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// If streaming is enabled, handle differently
		if req.Stream {
			// TODO: Implement streaming response
			http.Error(w, "streaming not yet implemented", http.StatusNotImplemented)
			return
		}

		// Set headers and return response
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(workerResp.StatusCode)
		w.Write(respBody)
	}
}
