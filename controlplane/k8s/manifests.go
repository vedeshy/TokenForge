package k8s

import (
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/intstr"
)

// buildDeploymentManifest creates a Kubernetes Deployment manifest for a worker
func buildDeploymentManifest(namespace, name, model, runtime, quant string, runtimeConfig *RuntimeConfig, modelConfig *ModelConfig) *appsv1.Deployment {
	replicas := int32(1)

	// Create labels
	labels := map[string]string{
		"app":     "worker",
		"runtime": runtime,
		"model":   slugify(model),
	}

	// Create environment variables
	env := []corev1.EnvVar{
		{
			Name:  "MODEL_NAME",
			Value: model,
		},
		{
			Name:  "MODEL_HASH",
			Value: modelConfig.Hash,
		},
		{
			Name:  "QUANT",
			Value: quant,
		},
	}

	// Add runtime-specific environment variables
	for k, v := range runtimeConfig.Env {
		env = append(env, corev1.EnvVar{
			Name:  k,
			Value: v,
		})
	}

	// Create resource requirements
	resources := corev1.ResourceRequirements{
		Limits: corev1.ResourceList{
			corev1.ResourceCPU:    resource.MustParse(runtimeConfig.CPU),
			corev1.ResourceMemory: resource.MustParse(runtimeConfig.Mem),
		},
		Requests: corev1.ResourceList{
			corev1.ResourceCPU:    resource.MustParse(runtimeConfig.CPU),
			corev1.ResourceMemory: resource.MustParse(runtimeConfig.Mem),
		},
	}

	// Add GPU if required
	if runtimeConfig.GPU > 0 {
		resources.Limits["nvidia.com/gpu"] = resource.MustParse(fmt.Sprintf("%d", runtimeConfig.GPU))
		resources.Requests["nvidia.com/gpu"] = resource.MustParse(fmt.Sprintf("%d", runtimeConfig.GPU))
	}

	// Create deployment
	return &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
			Labels:    labels,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: labels,
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: labels,
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:            "worker",
							Image:           runtimeConfig.Image,
							ImagePullPolicy: corev1.PullIfNotPresent,
							Env:             env,
							Resources:       resources,
							Ports: []corev1.ContainerPort{
								{
									Name:          "http",
									ContainerPort: 8000,
									Protocol:      corev1.ProtocolTCP,
								},
							},
							ReadinessProbe: &corev1.Probe{
								ProbeHandler: corev1.ProbeHandler{
									HTTPGet: &corev1.HTTPGetAction{
										Path: "/healthz",
										Port: intstr.FromInt(8000),
									},
								},
								InitialDelaySeconds: 10,
								PeriodSeconds:       5,
								TimeoutSeconds:      2,
								SuccessThreshold:    1,
								FailureThreshold:    3,
							},
						},
					},
				},
			},
		},
	}
}

// buildServiceManifest creates a Kubernetes Service manifest for a worker
func buildServiceManifest(namespace, name, deploymentName string) *corev1.Service {
	// Create labels
	labels := map[string]string{
		"app": "worker",
	}

	// Create service
	return &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
			Labels:    labels,
		},
		Spec: corev1.ServiceSpec{
			Selector: map[string]string{
				"app":  "worker",
				"name": deploymentName,
			},
			Ports: []corev1.ServicePort{
				{
					Name:       "http",
					Port:       8000,
					TargetPort: intstr.FromInt(8000),
					Protocol:   corev1.ProtocolTCP,
				},
			},
			Type: corev1.ServiceTypeClusterIP,
		},
	}
}
