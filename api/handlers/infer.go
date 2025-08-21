package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

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
			// For streaming, we need to proxy the worker's streaming response
			// Set appropriate headers for SSE
			w.Header().Set("Content-Type", "text/event-stream")
			w.Header().Set("Cache-Control", "no-cache")
			w.Header().Set("Connection", "keep-alive")
			w.WriteHeader(workerResp.StatusCode)
			
			// Copy the streaming response directly to the client
			if _, err := w.Write(respBody); err != nil {
				// Connection might be closed by client, just log and return
				return
			}
			
			// If the worker doesn't support streaming but we requested it,
			// convert the response to a streaming format
			if workerResp.Header.Get("Content-Type") != "text/event-stream" {
				// Parse the response
				var resp InferResponse
				if err := json.Unmarshal(respBody, &resp); err != nil {
					http.Error(w, "failed to parse worker response: "+err.Error(), http.StatusInternalServerError)
					return
				}
				
				// Split the output into tokens (words for simplicity)
				tokens := bytes.Fields([]byte(resp.Output))
				
				// Stream each token
				for i, token := range tokens {
					// Create event data
					data := map[string]interface{}{
						"token":   string(token),
						"index":   i,
						"is_last": i == len(tokens)-1,
					}
					
					// Convert to JSON
					eventData, err := json.Marshal(data)
					if err != nil {
						continue
					}
					
					// Write SSE event
					fmt.Fprintf(w, "data: %s\n\n", eventData)
					w.(http.Flusher).Flush()
					
					// Simulate generation time
					time.Sleep(100 * time.Millisecond)
				}
			}
			return
		}

		// Set headers and return response for non-streaming
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(workerResp.StatusCode)
		w.Write(respBody)
	}
}
