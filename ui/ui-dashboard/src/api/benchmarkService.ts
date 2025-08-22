import apiClient from './apiClient';

export interface Workload {
  name: string;
  qps: number;
  duration_s: number;
  prompt_len: number;
  gen_tokens: number;
  stream?: boolean;
  evaluate?: boolean;
  profile_memory?: boolean;
}

export interface BenchmarkRequest {
  model: string;
  runtimes: string[];
  workloads: Workload[];
}

export interface BenchmarkRun {
  id: string;
  model: string;
  runtimes: string[];
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  workloads: Workload[];
}

export interface WorkloadResult {
  runtime: string;
  workload: string;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  throughput_rps: number;
  tokens_per_second: number;
  time_to_first_token_ms?: number;
  avg_inter_token_latency_ms?: number;
  avg_bleu?: number;
  avg_rougeL?: number;
  avg_factual_accuracy?: number;
  memory_profile?: {
    timestamps: number[];
    cpu_memory: number[];
    gpu_memory?: number[];
  };
}

export interface BenchmarkReport {
  run_id: string;
  model: string;
  runtimes: string[];
  start_time: string;
  end_time: string;
  results: WorkloadResult[];
}

export const benchmarkService = {
  runBenchmark: async (request: BenchmarkRequest): Promise<BenchmarkRun> => {
    const response = await apiClient.post('/benchmarks/run', request);
    return response.data;
  },
  
  getBenchmarkRun: async (id: string): Promise<BenchmarkRun> => {
    const response = await apiClient.get(`/benchmarks/run/${id}`);
    return response.data;
  },
  
  getBenchmarkRuns: async (): Promise<BenchmarkRun[]> => {
    const response = await apiClient.get('/benchmarks/runs');
    return response.data;
  },
  
  getBenchmarkReport: async (id: string): Promise<BenchmarkReport> => {
    const response = await apiClient.get(`/benchmarks/report/${id}`);
    return response.data;
  }
};

export default benchmarkService;
