package controlplane

import (
	"fmt"
	"sync"
)

// Registry is a thread-safe registry for mapping models and runtimes to service URLs
type Registry struct {
	mu    sync.RWMutex
	store map[string]string
}

// NewRegistry creates a new registry
func NewRegistry() *Registry {
	return &Registry{
		store: make(map[string]string),
	}
}

// makeKey creates a unique key for a model and runtime pair
func makeKey(model, runtime string) string {
	return fmt.Sprintf("%s::%s", model, runtime)
}

// Set adds or updates a mapping for a model and runtime to a service URL
func (r *Registry) Set(model, runtime, serviceURL string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.store[makeKey(model, runtime)] = serviceURL
}

// Get retrieves the service URL for a model and runtime pair
func (r *Registry) Get(model, runtime string) (string, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	url, found := r.store[makeKey(model, runtime)]
	return url, found
}

// Delete removes a mapping for a model and runtime pair
func (r *Registry) Delete(model, runtime string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.store, makeKey(model, runtime))
}

// List returns all registered model and runtime pairs with their service URLs
func (r *Registry) List() map[string]string {
	r.mu.RLock()
	defer r.mu.RUnlock()

	result := make(map[string]string)
	for k, v := range r.store {
		result[k] = v
	}
	return result
}
