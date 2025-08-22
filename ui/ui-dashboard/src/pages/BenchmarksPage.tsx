import { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Grid,
  Paper,
  Box,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  CardHeader,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip
} from '@mui/material';
import { 
  Add as AddIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';
import { benchmarkService, BenchmarkRun, BenchmarkRequest, WorkloadResult, BenchmarkReport } from '../api/benchmarkService';
import { modelService, Model } from '../api/modelService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`benchmark-tabpanel-${index}`}
      aria-labelledby={`benchmark-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export default function BenchmarksPage() {
  const [benchmarkRuns, setBenchmarkRuns] = useState<BenchmarkRun[]>([]);
  const [selectedBenchmark, setSelectedBenchmark] = useState<string | null>(null);
  const [benchmarkReport, setBenchmarkReport] = useState<BenchmarkReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedRuntimes, setSelectedRuntimes] = useState<string[]>([]);
  const [running, setRunning] = useState(false);

  const fetchBenchmarks = async () => {
    try {
      setLoading(true);
      const data = await benchmarkService.getBenchmarkRuns();
      setBenchmarkRuns(data);
      
      if (data.length > 0 && !selectedBenchmark) {
        // Select the most recent completed benchmark
        const completedBenchmarks = data.filter(b => b.status === 'completed');
        if (completedBenchmarks.length > 0) {
          setSelectedBenchmark(completedBenchmarks[0].id);
          fetchBenchmarkReport(completedBenchmarks[0].id);
        }
      }
      
      setError(null);
    } catch (err) {
      console.error('Error fetching benchmarks:', err);
      setError('Failed to fetch benchmarks. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const fetchBenchmarkReport = async (id: string) => {
    try {
      setReportLoading(true);
      const data = await benchmarkService.getBenchmarkReport(id);
      setBenchmarkReport(data);
    } catch (err) {
      console.error('Error fetching benchmark report:', err);
      setError(`Failed to fetch report for benchmark ${id}.`);
    } finally {
      setReportLoading(false);
    }
  };

  const fetchModels = async () => {
    try {
      const data = await modelService.getModels();
      setModels(data);
      if (data.length > 0) {
        setSelectedModel(data[0].name);
      }
    } catch (err) {
      console.error('Error fetching models:', err);
    }
  };

  useEffect(() => {
    fetchBenchmarks();
    fetchModels();
  }, []);

  useEffect(() => {
    if (selectedBenchmark) {
      fetchBenchmarkReport(selectedBenchmark);
    }
  }, [selectedBenchmark]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleBenchmarkChange = (event: any) => {
    setSelectedBenchmark(event.target.value);
  };

  const handleRefresh = () => {
    fetchBenchmarks();
    if (selectedBenchmark) {
      fetchBenchmarkReport(selectedBenchmark);
    }
  };

  const handleOpenDialog = () => {
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
  };

  const handleModelChange = (event: any) => {
    setSelectedModel(event.target.value);
  };

  const handleRuntimesChange = (event: any) => {
    setSelectedRuntimes(event.target.value);
  };

  const handleRunBenchmark = async () => {
    if (!selectedModel || selectedRuntimes.length === 0) {
      return;
    }

    const benchmarkRequest: BenchmarkRequest = {
      model: selectedModel,
      runtimes: selectedRuntimes,
      workloads: [
        {
          name: 'qa-short',
          qps: 2,
          duration_s: 60,
          prompt_len: 256,
          gen_tokens: 128
        },
        {
          name: 'code-long',
          qps: 1,
          duration_s: 120,
          prompt_len: 512,
          gen_tokens: 256
        }
      ]
    };

    try {
      setRunning(true);
      await benchmarkService.runBenchmark(benchmarkRequest);
      handleCloseDialog();
      // Refresh the list after a short delay to allow the benchmark to start
      setTimeout(fetchBenchmarks, 1000);
    } catch (err) {
      console.error('Error running benchmark:', err);
      setError('Failed to run benchmark. Please try again later.');
    } finally {
      setRunning(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'warning';
      case 'failed':
        return 'error';
      case 'pending':
      default:
        return 'default';
    }
  };

  const prepareLatencyChartData = () => {
    if (!benchmarkReport) return [];
    
    // Group by workload
    const workloads = [...new Set(benchmarkReport.results.map(r => r.workload))];
    
    return workloads.map(workload => {
      const workloadResults = benchmarkReport.results.filter(r => r.workload === workload);
      
      const chartData = workloadResults.map(result => ({
        runtime: result.runtime,
        p50: result.p50_latency_ms,
        p95: result.p95_latency_ms,
        p99: result.p99_latency_ms,
        avg: result.avg_latency_ms
      }));
      
      return {
        workload,
        data: chartData
      };
    });
  };

  const prepareThroughputChartData = () => {
    if (!benchmarkReport) return [];
    
    // Group by workload
    const workloads = [...new Set(benchmarkReport.results.map(r => r.workload))];
    
    return workloads.map(workload => {
      const workloadResults = benchmarkReport.results.filter(r => r.workload === workload);
      
      const chartData = workloadResults.map(result => ({
        runtime: result.runtime,
        throughput: result.throughput_rps,
        tokens_per_second: result.tokens_per_second
      }));
      
      return {
        workload,
        data: chartData
      };
    });
  };

  const prepareStreamingChartData = () => {
    if (!benchmarkReport) return [];
    
    // Filter results that have streaming metrics
    const streamingResults = benchmarkReport.results.filter(
      r => r.time_to_first_token_ms !== undefined && r.avg_inter_token_latency_ms !== undefined
    );
    
    if (streamingResults.length === 0) return [];
    
    // Group by workload
    const workloads = [...new Set(streamingResults.map(r => r.workload))];
    
    return workloads.map(workload => {
      const workloadResults = streamingResults.filter(r => r.workload === workload);
      
      const chartData = workloadResults.map(result => ({
        runtime: result.runtime,
        ttft: result.time_to_first_token_ms,
        inter_token_latency: result.avg_inter_token_latency_ms
      }));
      
      return {
        workload,
        data: chartData
      };
    });
  };

  const prepareMemoryChartData = () => {
    if (!benchmarkReport) return [];
    
    // Filter results that have memory profile data
    const memoryResults = benchmarkReport.results.filter(r => r.memory_profile);
    
    if (memoryResults.length === 0) return [];
    
    return memoryResults.map(result => {
      const memoryProfile = result.memory_profile!;
      
      // Convert timestamps to relative seconds
      const startTime = memoryProfile.timestamps[0];
      const relativeTimestamps = memoryProfile.timestamps.map(t => t - startTime);
      
      // Convert memory to MB
      const cpuMemoryMB = memoryProfile.cpu_memory.map(m => m / (1024 * 1024));
      
      // Prepare chart data
      const chartData = relativeTimestamps.map((time, index) => ({
        time,
        cpu: cpuMemoryMB[index],
        gpu: memoryProfile.gpu_memory ? memoryProfile.gpu_memory[index] / (1024 * 1024) : undefined
      }));
      
      return {
        runtime: result.runtime,
        workload: result.workload,
        data: chartData
      };
    });
  };

  const latencyChartData = prepareLatencyChartData();
  const throughputChartData = prepareThroughputChartData();
  const streamingChartData = prepareStreamingChartData();
  const memoryChartData = prepareMemoryChartData();

  return (
    <Container maxWidth="lg">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Benchmarks
        </Typography>
        <Box>
          <Button 
            variant="outlined" 
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            sx={{ mr: 2 }}
          >
            Refresh
          </Button>
          <Button 
            variant="contained" 
            startIcon={<AddIcon />}
            onClick={handleOpenDialog}
          >
            Run Benchmark
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : benchmarkRuns.length === 0 ? (
        <Alert severity="info" sx={{ mb: 3 }}>
          No benchmarks found. Run a benchmark to get started.
        </Alert>
      ) : (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <FormControl fullWidth>
                <InputLabel id="benchmark-select-label">Select Benchmark</InputLabel>
                <Select
                  labelId="benchmark-select-label"
                  id="benchmark-select"
                  value={selectedBenchmark || ''}
                  label="Select Benchmark"
                  onChange={handleBenchmarkChange}
                >
                  {benchmarkRuns.map((run) => (
                    <MenuItem key={run.id} value={run.id}>
                      {run.model} ({run.runtimes.join(', ')}) - {new Date(run.start_time).toLocaleString()} 
                      <Chip 
                        label={run.status} 
                        size="small" 
                        color={getStatusColor(run.status)} 
                        sx={{ ml: 1 }} 
                      />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Paper>
          </Grid>

          {selectedBenchmark && (
            <Grid item xs={12}>
              {reportLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
                  <CircularProgress />
                </Box>
              ) : benchmarkReport ? (
                <Paper>
                  <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Tabs value={tabValue} onChange={handleTabChange} aria-label="benchmark tabs">
                      <Tab label="Latency" />
                      <Tab label="Throughput" />
                      {streamingChartData.length > 0 && <Tab label="Streaming" />}
                      {memoryChartData.length > 0 && <Tab label="Memory" />}
                      <Tab label="Raw Data" />
                    </Tabs>
                  </Box>

                  {/* Latency Tab */}
                  <TabPanel value={tabValue} index={0}>
                    <Typography variant="h6" gutterBottom>
                      Latency Comparison
                    </Typography>
                    
                    {latencyChartData.map((chart, index) => (
                      <Box key={index} sx={{ mt: 4 }}>
                        <Typography variant="subtitle1" gutterBottom>
                          Workload: {chart.workload}
                        </Typography>
                        <ResponsiveContainer width="100%" height={300}>
                          <BarChart data={chart.data}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="runtime" />
                            <YAxis label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }} />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="p50" name="p50 Latency" fill="#8884d8" />
                            <Bar dataKey="p95" name="p95 Latency" fill="#82ca9d" />
                            <Bar dataKey="p99" name="p99 Latency" fill="#ffc658" />
                            <Bar dataKey="avg" name="Avg Latency" fill="#ff8042" />
                          </BarChart>
                        </ResponsiveContainer>
                      </Box>
                    ))}
                  </TabPanel>

                  {/* Throughput Tab */}
                  <TabPanel value={tabValue} index={1}>
                    <Typography variant="h6" gutterBottom>
                      Throughput Comparison
                    </Typography>
                    
                    {throughputChartData.map((chart, index) => (
                      <Box key={index} sx={{ mt: 4 }}>
                        <Typography variant="subtitle1" gutterBottom>
                          Workload: {chart.workload}
                        </Typography>
                        <Grid container spacing={3}>
                          <Grid item xs={12} md={6}>
                            <Typography variant="subtitle2" align="center">
                              Requests per Second
                            </Typography>
                            <ResponsiveContainer width="100%" height={300}>
                              <BarChart data={chart.data}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="runtime" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="throughput" name="Requests/sec" fill="#8884d8" />
                              </BarChart>
                            </ResponsiveContainer>
                          </Grid>
                          <Grid item xs={12} md={6}>
                            <Typography variant="subtitle2" align="center">
                              Tokens per Second
                            </Typography>
                            <ResponsiveContainer width="100%" height={300}>
                              <BarChart data={chart.data}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="runtime" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="tokens_per_second" name="Tokens/sec" fill="#82ca9d" />
                              </BarChart>
                            </ResponsiveContainer>
                          </Grid>
                        </Grid>
                      </Box>
                    ))}
                  </TabPanel>

                  {/* Streaming Tab */}
                  {streamingChartData.length > 0 && (
                    <TabPanel value={tabValue} index={2}>
                      <Typography variant="h6" gutterBottom>
                        Streaming Metrics
                      </Typography>
                      
                      {streamingChartData.map((chart, index) => (
                        <Box key={index} sx={{ mt: 4 }}>
                          <Typography variant="subtitle1" gutterBottom>
                            Workload: {chart.workload}
                          </Typography>
                          <Grid container spacing={3}>
                            <Grid item xs={12} md={6}>
                              <Typography variant="subtitle2" align="center">
                                Time to First Token (ms)
                              </Typography>
                              <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={chart.data}>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis dataKey="runtime" />
                                  <YAxis />
                                  <Tooltip />
                                  <Legend />
                                  <Bar dataKey="ttft" name="TTFT (ms)" fill="#8884d8" />
                                </BarChart>
                              </ResponsiveContainer>
                            </Grid>
                            <Grid item xs={12} md={6}>
                              <Typography variant="subtitle2" align="center">
                                Inter-token Latency (ms)
                              </Typography>
                              <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={chart.data}>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis dataKey="runtime" />
                                  <YAxis />
                                  <Tooltip />
                                  <Legend />
                                  <Bar dataKey="inter_token_latency" name="Inter-token Latency (ms)" fill="#82ca9d" />
                                </BarChart>
                              </ResponsiveContainer>
                            </Grid>
                          </Grid>
                        </Box>
                      ))}
                    </TabPanel>
                  )}

                  {/* Memory Tab */}
                  {memoryChartData.length > 0 && (
                    <TabPanel value={tabValue} index={streamingChartData.length > 0 ? 3 : 2}>
                      <Typography variant="h6" gutterBottom>
                        Memory Usage
                      </Typography>
                      
                      {memoryChartData.map((chart, index) => (
                        <Box key={index} sx={{ mt: 4 }}>
                          <Typography variant="subtitle1" gutterBottom>
                            {chart.runtime} - {chart.workload}
                          </Typography>
                          <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={chart.data}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis 
                                dataKey="time" 
                                label={{ value: 'Time (seconds)', position: 'insideBottomRight', offset: -5 }} 
                              />
                              <YAxis label={{ value: 'Memory (MB)', angle: -90, position: 'insideLeft' }} />
                              <Tooltip />
                              <Legend />
                              <Line type="monotone" dataKey="cpu" name="CPU Memory (MB)" stroke="#8884d8" />
                              {chart.data[0].gpu !== undefined && (
                                <Line type="monotone" dataKey="gpu" name="GPU Memory (MB)" stroke="#82ca9d" />
                              )}
                            </LineChart>
                          </ResponsiveContainer>
                        </Box>
                      ))}
                    </TabPanel>
                  )}

                  {/* Raw Data Tab */}
                  <TabPanel value={tabValue} index={
                    2 + (streamingChartData.length > 0 ? 1 : 0) + (memoryChartData.length > 0 ? 1 : 0)
                  }>
                    <Typography variant="h6" gutterBottom>
                      Raw Benchmark Data
                    </Typography>
                    
                    <TableContainer component={Paper}>
                      <Table>
                        <TableHead>
                          <TableRow>
                            <TableCell>Runtime</TableCell>
                            <TableCell>Workload</TableCell>
                            <TableCell>Avg Latency (ms)</TableCell>
                            <TableCell>p50 (ms)</TableCell>
                            <TableCell>p95 (ms)</TableCell>
                            <TableCell>p99 (ms)</TableCell>
                            <TableCell>Throughput (req/s)</TableCell>
                            <TableCell>Tokens/sec</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {benchmarkReport.results.map((result, index) => (
                            <TableRow key={index}>
                              <TableCell>{result.runtime}</TableCell>
                              <TableCell>{result.workload}</TableCell>
                              <TableCell>{result.avg_latency_ms.toFixed(2)}</TableCell>
                              <TableCell>{result.p50_latency_ms.toFixed(2)}</TableCell>
                              <TableCell>{result.p95_latency_ms.toFixed(2)}</TableCell>
                              <TableCell>{result.p99_latency_ms.toFixed(2)}</TableCell>
                              <TableCell>{result.throughput_rps.toFixed(2)}</TableCell>
                              <TableCell>{result.tokens_per_second.toFixed(2)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </TabPanel>
                </Paper>
              ) : (
                <Alert severity="warning">
                  No report available for the selected benchmark.
                </Alert>
              )}
            </Grid>
          )}
        </Grid>
      )}

      {/* Run Benchmark Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog}>
        <DialogTitle>Run New Benchmark</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="normal">
            <InputLabel id="model-select-label">Model</InputLabel>
            <Select
              labelId="model-select-label"
              id="model-select"
              value={selectedModel}
              label="Model"
              onChange={handleModelChange}
            >
              {models.map((model) => (
                <MenuItem key={model.name} value={model.name}>
                  {model.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth margin="normal">
            <InputLabel id="runtime-select-label">Runtimes</InputLabel>
            <Select
              labelId="runtime-select-label"
              id="runtime-select"
              multiple
              value={selectedRuntimes}
              label="Runtimes"
              onChange={handleRuntimesChange}
            >
              {models.find(m => m.name === selectedModel)?.supported_runtimes.map((runtime) => (
                <MenuItem key={runtime} value={runtime}>
                  {runtime}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button 
            onClick={handleRunBenchmark} 
            variant="contained" 
            disabled={!selectedModel || selectedRuntimes.length === 0 || running}
          >
            {running ? <CircularProgress size={24} /> : 'Run Benchmark'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
