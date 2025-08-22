package db

import (
	"context"
	"time"
)

// BenchmarkRun represents a benchmark run in the database
type BenchmarkRun struct {
	ID        string    `json:"id"`
	Model     string    `json:"model"`
	Runtimes  []string  `json:"runtimes"`
	Status    string    `json:"status"`
	StartTime time.Time `json:"start_time"`
	EndTime   time.Time `json:"end_time,omitempty"`
	Workloads []struct {
		Name      string `json:"name"`
		QPS       int    `json:"qps"`
		DurationS int    `json:"duration_s"`
		PromptLen int    `json:"prompt_len"`
		GenTokens int    `json:"gen_tokens"`
		Stream    bool   `json:"stream,omitempty"`
	} `json:"workloads"`
}

// GetAllBenchmarkRuns returns all benchmark runs
func (c *Client) GetAllBenchmarkRuns() ([]BenchmarkRun, error) {
	if c == nil || c.db == nil {
		return nil, ErrNotConnected
	}

	// For now, we'll return mock data
	// In a real implementation, this would query the database
	mockRuns := []BenchmarkRun{
		{
			ID:        "run-001",
			Model:     "meta-llama/Llama-3-8b-instruct",
			Runtimes:  []string{"vllm", "transformers"},
			Status:    "completed",
			StartTime: time.Now().Add(-24 * time.Hour),
			EndTime:   time.Now().Add(-23 * time.Hour),
			Workloads: []struct {
				Name      string `json:"name"`
				QPS       int    `json:"qps"`
				DurationS int    `json:"duration_s"`
				PromptLen int    `json:"prompt_len"`
				GenTokens int    `json:"gen_tokens"`
				Stream    bool   `json:"stream,omitempty"`
			}{
				{
					Name:      "qa-short",
					QPS:       2,
					DurationS: 60,
					PromptLen: 256,
					GenTokens: 128,
				},
				{
					Name:      "code-long",
					QPS:       1,
					DurationS: 120,
					PromptLen: 512,
					GenTokens: 256,
				},
			},
		},
		{
			ID:        "run-002",
			Model:     "meta-llama/Llama-3-8b-instruct",
			Runtimes:  []string{"vllm"},
			Status:    "completed",
			StartTime: time.Now().Add(-12 * time.Hour),
			EndTime:   time.Now().Add(-11 * time.Hour),
			Workloads: []struct {
				Name      string `json:"name"`
				QPS       int    `json:"qps"`
				DurationS int    `json:"duration_s"`
				PromptLen int    `json:"prompt_len"`
				GenTokens int    `json:"gen_tokens"`
				Stream    bool   `json:"stream,omitempty"`
			}{
				{
					Name:      "qa-streaming",
					QPS:       1,
					DurationS: 60,
					PromptLen: 256,
					GenTokens: 128,
					Stream:    true,
				},
			},
		},
	}

	return mockRuns, nil
}
