package handlers

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type RuntimesConfig struct {
	Runtimes []struct {
		Name  string            `json:"name" yaml:"name"`
		Image string            `json:"image" yaml:"image"`
		GPU   int               `json:"gpu" yaml:"gpu"`
		CPU   string            `json:"cpu" yaml:"cpu"`
		Mem   string            `json:"mem" yaml:"mem"`
		Env   map[string]string `json:"env" yaml:"env"`
	} `json:"runtimes" yaml:"runtimes"`
}

// RuntimesHandler returns the configured runtimes from YAML
func RuntimesHandler(configPath string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Read runtimes config file
		data, err := os.ReadFile(filepath.Join(configPath, "runtimes.yaml"))
		if err != nil {
			http.Error(w, "failed to read runtimes config: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// Parse YAML
		var config RuntimesConfig
		if err := yaml.Unmarshal(data, &config); err != nil {
			http.Error(w, "failed to parse runtimes config: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// Return as JSON
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(config)
	}
}
