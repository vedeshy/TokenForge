import apiClient from './apiClient';

export interface DeploymentRequest {
  model: string;
  runtime: string;
  quant: string;
}

export interface DeploymentStatus {
  model: string;
  runtime: string;
  quant: string;
  status: 'pending' | 'deploying' | 'ready' | 'failed';
  endpoint?: string;
  error?: string;
  created_at: string;
  updated_at: string;
}

export const deploymentService = {
  deployModel: async (request: DeploymentRequest): Promise<DeploymentStatus> => {
    const response = await apiClient.post('/deploy', request);
    return response.data;
  },
  
  getDeployments: async (): Promise<DeploymentStatus[]> => {
    const response = await apiClient.get('/deployments');
    return response.data;
  },
  
  getDeploymentStatus: async (model: string, runtime: string): Promise<DeploymentStatus> => {
    const response = await apiClient.get(`/deployments/${model}/${runtime}`);
    return response.data;
  }
};

export default deploymentService;
