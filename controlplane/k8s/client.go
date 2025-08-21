package k8s

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
)

// Client is a wrapper around the Kubernetes client
type Client struct {
	clientset *kubernetes.Clientset
}

// RuntimeConfig represents a runtime configuration from YAML
type RuntimeConfig struct {
	Name  string            `yaml:"name"`
	Image string            `yaml:"image"`
	GPU   int               `yaml:"gpu"`
	CPU   string            `yaml:"cpu"`
	Mem   string            `yaml:"mem"`
	Env   map[string]string `yaml:"env"`
}

// ModelConfig represents a model configuration from YAML
type ModelConfig struct {
	Name  string `yaml:"name"`
	Quant string `yaml:"quant"`
	Hash  string `yaml:"hash"`
}

// RuntimesConfig is the top-level structure for runtimes.yaml
type RuntimesConfig struct {
	Runtimes []RuntimeConfig `yaml:"runtimes"`
}

// ModelsConfig is the top-level structure for models.yaml
type ModelsConfig struct {
	Models []ModelConfig `yaml:"models"`
}

// NewClient creates a new Kubernetes client
func NewClient() (*Client, error) {
	var config *rest.Config
	var err error

	// Try in-cluster config first
	config, err = rest.InClusterConfig()
	if err != nil {
		// Fall back to kubeconfig
		kubeconfig := filepath.Join(homedir.HomeDir(), ".kube", "config")
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("failed to create k8s config: %w", err)
		}
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8s client: %w", err)
	}

	return &Client{
		clientset: clientset,
	}, nil
}

// DeployWorker deploys a worker for the specified model and runtime
func DeployWorker(ctx context.Context, model, runtime, quant string) (string, string, string, string, error) {
	// Create a client
	client, err := NewClient()
	if err != nil {
		return "", "", "", "", err
	}

	// Load runtime and model configs
	runtimeConfig, err := client.loadRuntimeConfig(runtime)
	if err != nil {
		return "", "", "", "", err
	}

	modelConfig, err := client.loadModelConfig(model)
	if err != nil {
		return "", "", "", "", err
	}

	// Set namespace
	namespace := "default"

	// Generate names
	modelSlug := slugify(model)
	deploymentName := fmt.Sprintf("worker-%s-%s", runtime, modelSlug)
	serviceName := deploymentName

	// Create deployment
	_, err = client.createDeployment(ctx, namespace, deploymentName, model, runtime, quant, runtimeConfig, modelConfig)
	if err != nil {
		return "", "", "", "", err
	}

	// Create service
	_, err = client.createService(ctx, namespace, serviceName, deploymentName)
	if err != nil {
		return "", "", "", "", err
	}

	// Construct service URL
	serviceURL := fmt.Sprintf("http://%s.%s.svc.cluster.local:8000", serviceName, namespace)

	return serviceURL, namespace, deploymentName, serviceName, nil
}

// IsDeploymentReady checks if a deployment is ready
func IsDeploymentReady(ctx context.Context, namespace, deploymentName string) (bool, error) {
	client, err := NewClient()
	if err != nil {
		return false, err
	}

	deployment, err := client.clientset.AppsV1().Deployments(namespace).Get(ctx, deploymentName, metav1.GetOptions{})
	if err != nil {
		return false, err
	}

	return deployment.Status.ReadyReplicas == *deployment.Spec.Replicas, nil
}

// loadRuntimeConfig loads the runtime configuration from YAML
func (c *Client) loadRuntimeConfig(runtime string) (*RuntimeConfig, error) {
	data, err := os.ReadFile("configs/runtimes.yaml")
	if err != nil {
		return nil, fmt.Errorf("failed to read runtimes config: %w", err)
	}

	var config RuntimesConfig
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse runtimes config: %w", err)
	}

	for _, r := range config.Runtimes {
		if r.Name == runtime {
			return &r, nil
		}
	}

	return nil, fmt.Errorf("runtime %s not found in config", runtime)
}

// loadModelConfig loads the model configuration from YAML
func (c *Client) loadModelConfig(model string) (*ModelConfig, error) {
	data, err := os.ReadFile("configs/models.yaml")
	if err != nil {
		return nil, fmt.Errorf("failed to read models config: %w", err)
	}

	var config ModelsConfig
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse models config: %w", err)
	}

	for _, m := range config.Models {
		if m.Name == model {
			return &m, nil
		}
	}

	return nil, fmt.Errorf("model %s not found in config", model)
}

// createDeployment creates a Kubernetes deployment for a worker
func (c *Client) createDeployment(ctx context.Context, namespace, name, model, runtime, quant string, runtimeConfig *RuntimeConfig, modelConfig *ModelConfig) (*appsv1.Deployment, error) {
	// Create deployment spec
	deployment := buildDeploymentManifest(namespace, name, model, runtime, quant, runtimeConfig, modelConfig)

	// Create deployment
	return c.clientset.AppsV1().Deployments(namespace).Create(ctx, deployment, metav1.CreateOptions{})
}

// createService creates a Kubernetes service for a worker
func (c *Client) createService(ctx context.Context, namespace, name, deploymentName string) (*corev1.Service, error) {
	// Create service spec
	service := buildServiceManifest(namespace, name, deploymentName)

	// Create service
	return c.clientset.CoreV1().Services(namespace).Create(ctx, service, metav1.CreateOptions{})
}

// slugify converts a model name to a valid Kubernetes resource name
func slugify(name string) string {
	// Replace slashes with dashes
	slug := strings.ReplaceAll(name, "/", "-")
	// Replace dots with dashes
	slug = strings.ReplaceAll(slug, ".", "-")
	// Convert to lowercase
	slug = strings.ToLower(slug)
	return slug
}
