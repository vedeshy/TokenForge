import apiClient from './apiClient';

export interface InferenceRequest {
  model: string;
  runtime: string;
  prompt: string;
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  stream?: boolean;
}

export interface InferenceResponse {
  output: string;
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
  runtime_meta: Record<string, any>;
}

export const inferenceService = {
  infer: async (request: InferenceRequest): Promise<InferenceResponse> => {
    const response = await apiClient.post('/infer', request);
    return response.data;
  },
  
  streamInfer: async (request: InferenceRequest, onToken: (token: string) => void, onComplete: (response: InferenceResponse) => void): Promise<void> => {
    const response = await apiClient.post('/infer', {
      ...request,
      stream: true
    }, {
      responseType: 'text',
      onDownloadProgress: (progressEvent) => {
        const text = progressEvent.event.target.responseText;
        const lines = text.split('\n').filter(line => line.trim() !== '');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.substring(6);
            if (data === '[DONE]') {
              // Stream completed
              break;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.token) {
                onToken(parsed.token);
              }
            } catch (e) {
              console.error('Error parsing SSE data', e);
            }
          }
        }
      }
    });
    
    onComplete(response.data);
  }
};

export default inferenceService;
