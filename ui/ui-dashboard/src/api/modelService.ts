import apiClient from './apiClient';

export interface Model {
  name: string;
  description?: string;
  provider: string;
  size: string;
  quantization: string[];
  supported_runtimes: string[];
}

export const modelService = {
  getModels: async (): Promise<Model[]> => {
    const response = await apiClient.get('/models');
    return response.data;
  },
  
  getModel: async (name: string): Promise<Model> => {
    const response = await apiClient.get(`/models/${name}`);
    return response.data;
  }
};

export default modelService;
