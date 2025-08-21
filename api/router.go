package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/tokenforge/llm-infra-bench/api/handlers"
	"github.com/tokenforge/llm-infra-bench/controlplane"
	"github.com/tokenforge/llm-infra-bench/db"
)

func setupRouter() http.Handler {
	r := chi.NewRouter()

	// Create registry
	registry := controlplane.NewRegistry()

	// Create DB client
	ctx := context.Background()
	dbClient, err := db.NewClient(ctx)
	if err != nil {
		log.Printf("Warning: Failed to connect to database: %v", err)
		dbClient = nil
	}

	// Config path
	configPath := os.Getenv("CONFIG_PATH")
	if configPath == "" {
		configPath = "configs"
	}

	// Middleware
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)

	// Prometheus metrics endpoint
	r.Handle("/metrics", promhttp.Handler())

	// Health check
	r.Get("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	})

	// API routes
	r.Route("/api/v1", func(r chi.Router) {
		r.Post("/deploy", handlers.DeployHandler(registry))
		r.Post("/infer", handlers.InferHandler(registry))

		r.Route("/benchmarks", func(r chi.Router) {
			r.Post("/run", handlers.BenchmarkRunHandler(dbClient))
			r.Get("/run/{id}", handlers.BenchmarkStatusHandler(dbClient))
		})

		r.Get("/models", handlers.ModelsHandler(configPath))
		r.Get("/runtimes", handlers.RuntimesHandler(configPath))
	})

	return r
}
