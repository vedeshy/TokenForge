package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/tokenforge/llm-infra-bench/db"
)

// BenchmarkRunsHandler returns all benchmark runs
func BenchmarkRunsHandler(dbClient *db.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if dbClient == nil {
			http.Error(w, "Database not available", http.StatusServiceUnavailable)
			return
		}
		
		runs, err := dbClient.GetAllBenchmarkRuns()
		if err != nil {
			http.Error(w, "Failed to retrieve benchmark runs", http.StatusInternalServerError)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(runs)
	}
}

// BenchmarkReportHandler returns the report for a specific benchmark run
func BenchmarkReportHandler(dbClient *db.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if dbClient == nil {
			http.Error(w, "Database not available", http.StatusServiceUnavailable)
			return
		}
		
		runID := chi.URLParam(r, "id")
		if runID == "" {
			http.Error(w, "Missing run ID parameter", http.StatusBadRequest)
			return
		}
		
		// For now, we'll return a mock report
		// In a real implementation, this would fetch the report from the database or S3
		mockReport := map[string]interface{}{
			"run_id": runID,
			"model": "test-model",
			"runtimes": []string{"vllm", "transformers"},
			"start_time": "2025-08-22T10:00:00Z",
			"end_time": "2025-08-22T10:05:00Z",
			"results": []map[string]interface{}{
				{
					"runtime": "vllm",
					"workload": "qa-short",
					"avg_latency_ms": 250.5,
					"p50_latency_ms": 240.2,
					"p95_latency_ms": 320.7,
					"p99_latency_ms": 380.1,
					"throughput_rps": 4.2,
					"tokens_per_second": 45.6,
				},
				{
					"runtime": "transformers",
					"workload": "qa-short",
					"avg_latency_ms": 350.8,
					"p50_latency_ms": 340.5,
					"p95_latency_ms": 420.3,
					"p99_latency_ms": 480.9,
					"throughput_rps": 3.1,
					"tokens_per_second": 32.4,
				},
			},
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(mockReport)
	}
}
