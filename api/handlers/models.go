package handlers

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type ModelsConfig struct {
	Models []struct {
		Name  string `json:"name" yaml:"name"`
		Quant string `json:"quant" yaml:"quant"`
		Hash  string `json:"hash" yaml:"hash"`
	} `json:"models" yaml:"models"`
}

// ModelsHandler returns the configured models from YAML
func ModelsHandler(configPath string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Read models config file
		data, err := os.ReadFile(filepath.Join(configPath, "models.yaml"))
		if err != nil {
			http.Error(w, "failed to read models config: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// Parse YAML
		var config ModelsConfig
		if err := yaml.Unmarshal(data, &config); err != nil {
			http.Error(w, "failed to parse models config: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// Return as JSON
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(config)
	}
}
