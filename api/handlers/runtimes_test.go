package handlers

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestRuntimesHandler(t *testing.T) {
	// Create a temporary directory for test configs
	tempDir, err := os.MkdirTemp("", "tokenforge-test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Create a test runtimes.yaml file
	testConfig := `runtimes:
  - name: test-runtime
    image: test-image:latest
    gpu: 1
    cpu: "2"
    mem: "8Gi"
    env:
      TEST_ENV: "test-value"
`
	err = os.WriteFile(filepath.Join(tempDir, "runtimes.yaml"), []byte(testConfig), 0644)
	if err != nil {
		t.Fatalf("Failed to write test config: %v", err)
	}

	// Create a request to pass to our handler
	req, err := http.NewRequest("GET", "/api/v1/runtimes", nil)
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}

	// Create a ResponseRecorder to record the response
	rr := httptest.NewRecorder()
	handler := RuntimesHandler(tempDir)

	// Call the handler
	handler.ServeHTTP(rr, req)

	// Check the status code
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("Handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	// Check the response body contains our runtime
	response := rr.Body.String()
	if !contains(response, "test-runtime") ||
		!contains(response, "test-image:latest") ||
		!contains(response, "test-value") {
		t.Errorf("Handler response doesn't contain expected runtime: %v", response)
	}
}
