package controlplane

import (
	"context"
	"fmt"
	"time"

	"github.com/tokenforge/llm-infra-bench/controlplane/k8s"
)

// Controller manages the deployment and lifecycle of worker instances
type Controller struct {
	registry *Registry
}

// NewController creates a new controller
func NewController(registry *Registry) *Controller {
	return &Controller{
		registry: registry,
	}
}

// DeployModel deploys a model with the specified runtime and waits for it to be ready
func (c *Controller) DeployModel(ctx context.Context, model, runtime, quant string) (string, error) {
	// Check if model is already deployed with this runtime
	if serviceURL, found := c.registry.Get(model, runtime); found {
		// Check if the service is healthy
		// TODO: Add health check
		return serviceURL, nil
	}

	// Deploy the model
	serviceURL, namespace, deploymentName, serviceName, err := k8s.DeployWorker(ctx, model, runtime, quant)
	if err != nil {
		return "", fmt.Errorf("failed to deploy worker: %w", err)
	}

	// Register the service
	c.registry.Set(model, runtime, serviceURL)

	// Wait for the service to be ready
	err = c.waitForReady(ctx, namespace, deploymentName, serviceName)
	if err != nil {
		return "", fmt.Errorf("deployment failed to become ready: %w", err)
	}

	return serviceURL, nil
}

// waitForReady polls the deployment until it's ready or times out
func (c *Controller) waitForReady(ctx context.Context, namespace, deploymentName, serviceName string) error {
	// Create a timeout context
	ctx, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()

	// Poll until ready
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(5 * time.Second):
			ready, err := k8s.IsDeploymentReady(ctx, namespace, deploymentName)
			if err != nil {
				return err
			}
			if ready {
				return nil
			}
		}
	}
}
