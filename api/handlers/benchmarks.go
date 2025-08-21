package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os/exec"
	"path/filepath"

	"github.com/go-chi/chi/v5"
	"github.com/tokenforge/llm-infra-bench/db"
)

// BenchmarkRunRequest represents the benchmark run request
// It uses the same structure as configs/benchmark.yaml
type BenchmarkRunRequest struct {
	Model     string   `json:"model"`
	Runtimes  []string `json:"runtimes"`
	Workloads []struct {
		Name      string `json:"name"`
		QPS       int    `json:"qps"`
		DurationS int    `json:"duration_s"`
		PromptLen int    `json:"prompt_len"`
		GenTokens int    `json:"gen_tokens"`
	} `json:"workloads"`
}

type BenchmarkRunResponse struct {
	ID     string `json:"id"`
	Status string `json:"status"`
}

type BenchmarkStatusResponse struct {
	ID      string `json:"id"`
	Status  string `json:"status"`
	Summary struct {
		Model     string   `json:"model"`
		Runtimes  []string `json:"runtimes"`
		Artifacts struct {
			HTML string `json:"html"`
			CSV  string `json:"csv"`
			Raw  string `json:"raw"`
		} `json:"artifacts"`
	} `json:"summary"`
}

// BenchmarkRunHandler handles benchmark run requests
func BenchmarkRunHandler(dbClient *db.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req BenchmarkRunRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		// Validate request
		if req.Model == "" || len(req.Runtimes) == 0 || len(req.Workloads) == 0 {
			http.Error(w, "model, runtimes, and workloads are required", http.StatusBadRequest)
			return
		}

		// Generate a unique run ID
		runID := fmt.Sprintf("run_%06d", dbClient.GetNextRunID())

		// Save benchmark config to temporary YAML
		configPath := filepath.Join("/tmp", runID+".yaml")
		// TODO: Write config to file

		// Create run record in database
		err := dbClient.CreateRun(r.Context(), runID, "queued", req.Model, req.Runtimes, configPath)
		if err != nil {
			http.Error(w, "failed to create run record: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// Start benchmark process in background
		go func() {
			cmd := exec.Command("python", "harness/run_bench.py", "--run-id", runID, "--config", configPath)
			// TODO: Handle command execution and update run status
			_ = cmd.Run()
		}()

		// Return response
		resp := BenchmarkRunResponse{
			ID:     runID,
			Status: "queued",
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusAccepted)
		json.NewEncoder(w).Encode(resp)
	}
}

// BenchmarkStatusHandler handles benchmark status requests
func BenchmarkStatusHandler(dbClient *db.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		runID := chi.URLParam(r, "id")
		if runID == "" {
			http.Error(w, "run ID is required", http.StatusBadRequest)
			return
		}

		// Get run status from database
		run, err := dbClient.GetRun(r.Context(), runID)
		if err != nil {
			http.Error(w, "failed to get run status: "+err.Error(), http.StatusInternalServerError)
			return
		}

		if run == nil {
			http.Error(w, "run not found", http.StatusNotFound)
			return
		}

		// Prepare response
		resp := BenchmarkStatusResponse{
			ID:     runID,
			Status: run.Status,
		}
		resp.Summary.Model = run.Model
		resp.Summary.Runtimes = run.Runtimes
		resp.Summary.Artifacts.HTML = run.HTMLUrl
		resp.Summary.Artifacts.CSV = run.CSVUrl
		resp.Summary.Artifacts.Raw = run.RawUrl

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(resp)
	}
}
