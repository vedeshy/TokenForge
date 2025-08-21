package handlers

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestModelsHandler(t *testing.T) {
	// Create a temporary directory for test configs
	tempDir, err := os.MkdirTemp("", "tokenforge-test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Create a test models.yaml file
	testConfig := `models:
  - name: test-model
    quant: fp16
    hash: sha256:test-hash
`
	err = os.WriteFile(filepath.Join(tempDir, "models.yaml"), []byte(testConfig), 0644)
	if err != nil {
		t.Fatalf("Failed to write test config: %v", err)
	}

	// Create a request to pass to our handler
	req, err := http.NewRequest("GET", "/api/v1/models", nil)
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}

	// Create a ResponseRecorder to record the response
	rr := httptest.NewRecorder()
	handler := ModelsHandler(tempDir)

	// Call the handler
	handler.ServeHTTP(rr, req)

	// Check the status code
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("Handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	// Check the response body contains our model
	response := rr.Body.String()
	if !contains(response, "test-model") || !contains(response, "fp16") || !contains(response, "sha256:test-hash") {
		t.Errorf("Handler response doesn't contain expected model: %v", response)
	}
}

func contains(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
