import { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Grid,
  Paper,
  TextField,
  Button,
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  CircularProgress,
  Card,
  CardContent,
  Alert,
  Snackbar,
  Divider,
  FormControlLabel,
  Switch
} from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import { deploymentService, DeploymentStatus } from '../api/deploymentService';
import { inferenceService, InferenceRequest, InferenceResponse } from '../api/inferenceService';

export default function InferencePage() {
  const [deployments, setDeployments] = useState<DeploymentStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedRuntime, setSelectedRuntime] = useState('');
  const [prompt, setPrompt] = useState('');
  const [maxTokens, setMaxTokens] = useState(128);
  const [temperature, setTemperature] = useState(0.7);
  const [topP, setTopP] = useState(0.95);
  const [streaming, setStreaming] = useState(false);
  const [inferenceResult, setInferenceResult] = useState<string | null>(null);
  const [inferenceMetadata, setInferenceMetadata] = useState<Partial<InferenceResponse> | null>(null);
  const [inferring, setInferring] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  const fetchDeployments = async () => {
    try {
      setLoading(true);
      const data = await deploymentService.getDeployments();
      const readyDeployments = data.filter(d => d.status === 'ready');
      setDeployments(readyDeployments);
      
      if (readyDeployments.length > 0) {
        setSelectedModel(readyDeployments[0].model);
        setSelectedRuntime(readyDeployments[0].runtime);
      }
      
      setError(null);
    } catch (err) {
      console.error('Error fetching deployments:', err);
      setError('Failed to fetch deployments. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
  }, []);

  const handlePromptChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setPrompt(event.target.value);
  };

  const handleMaxTokensChange = (event: Event, newValue: number | number[]) => {
    setMaxTokens(newValue as number);
  };

  const handleTemperatureChange = (event: Event, newValue: number | number[]) => {
    setTemperature(newValue as number);
  };

  const handleTopPChange = (event: Event, newValue: number | number[]) => {
    setTopP(newValue as number);
  };

  const handleStreamingChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setStreaming(event.target.checked);
  };

  const handleModelRuntimeChange = (event: any) => {
    const value = event.target.value;
    const [model, runtime] = value.split('|');
    setSelectedModel(model);
    setSelectedRuntime(runtime);
  };

  const handleInference = async () => {
    if (!selectedModel || !selectedRuntime || !prompt) {
      setSnackbarMessage('Please fill in all required fields');
      setSnackbarOpen(true);
      return;
    }

    const inferenceRequest: InferenceRequest = {
      model: selectedModel,
      runtime: selectedRuntime,
      prompt,
      max_tokens: maxTokens,
      temperature,
      top_p: topP,
      stream: streaming
    };

    try {
      setInferring(true);
      setInferenceResult('');
      setInferenceMetadata(null);

      if (streaming) {
        let streamedText = '';
        
        await inferenceService.streamInfer(
          inferenceRequest,
          (token) => {
            streamedText += token;
            setInferenceResult(streamedText);
          },
          (response) => {
            setInferenceMetadata({
              latency_ms: response.latency_ms,
              tokens_in: response.tokens_in,
              tokens_out: response.tokens_out,
              runtime_meta: response.runtime_meta
            });
          }
        );
      } else {
        const response = await inferenceService.infer(inferenceRequest);
        setInferenceResult(response.output);
        setInferenceMetadata({
          latency_ms: response.latency_ms,
          tokens_in: response.tokens_in,
          tokens_out: response.tokens_out,
          runtime_meta: response.runtime_meta
        });
      }
    } catch (err) {
      console.error('Error during inference:', err);
      setSnackbarMessage('Failed to run inference. Please try again later.');
      setSnackbarOpen(true);
    } finally {
      setInferring(false);
    }
  };

  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom>
        Interactive Inference
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : deployments.length === 0 ? (
        <Alert severity="info" sx={{ mb: 3 }}>
          No active deployments found. Please deploy a model first.
        </Alert>
      ) : (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Inference Settings
              </Typography>
              
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth margin="normal">
                    <InputLabel id="model-runtime-select-label">Model & Runtime</InputLabel>
                    <Select
                      labelId="model-runtime-select-label"
                      id="model-runtime-select"
                      value={`${selectedModel}|${selectedRuntime}`}
                      label="Model & Runtime"
                      onChange={handleModelRuntimeChange}
                    >
                      {deployments.map((deployment) => (
                        <MenuItem 
                          key={`${deployment.model}|${deployment.runtime}`} 
                          value={`${deployment.model}|${deployment.runtime}`}
                        >
                          {deployment.model} ({deployment.runtime})
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={streaming}
                        onChange={handleStreamingChange}
                        name="streaming"
                        color="primary"
                      />
                    }
                    label="Enable streaming"
                    sx={{ mt: 2 }}
                  />
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <Typography gutterBottom>
                    Max Tokens: {maxTokens}
                  </Typography>
                  <Slider
                    value={maxTokens}
                    onChange={handleMaxTokensChange}
                    min={1}
                    max={1024}
                    step={1}
                    valueLabelDisplay="auto"
                    aria-labelledby="max-tokens-slider"
                  />
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <Typography gutterBottom>
                    Temperature: {temperature.toFixed(2)}
                  </Typography>
                  <Slider
                    value={temperature}
                    onChange={handleTemperatureChange}
                    min={0}
                    max={2}
                    step={0.01}
                    valueLabelDisplay="auto"
                    aria-labelledby="temperature-slider"
                  />
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <Typography gutterBottom>
                    Top-P: {topP.toFixed(2)}
                  </Typography>
                  <Slider
                    value={topP}
                    onChange={handleTopPChange}
                    min={0}
                    max={1}
                    step={0.01}
                    valueLabelDisplay="auto"
                    aria-labelledby="top-p-slider"
                  />
                </Grid>
              </Grid>
            </Paper>
          </Grid>
          
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Prompt
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={4}
                variant="outlined"
                placeholder="Enter your prompt here..."
                value={prompt}
                onChange={handlePromptChange}
              />
              <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={inferring ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
                  onClick={handleInference}
                  disabled={inferring || !prompt}
                >
                  {inferring ? 'Running...' : 'Run Inference'}
                </Button>
              </Box>
            </Paper>
          </Grid>
          
          {inferenceResult !== null && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Result
                  </Typography>
                  <Paper 
                    elevation={0} 
                    sx={{ 
                      p: 2, 
                      bgcolor: 'grey.100', 
                      minHeight: '100px',
                      whiteSpace: 'pre-wrap',
                      fontFamily: 'monospace'
                    }}
                  >
                    {inferenceResult || (inferring ? 'Generating...' : '')}
                  </Paper>
                  
                  {inferenceMetadata && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="subtitle2" gutterBottom>
                        Metadata:
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={4}>
                          <Typography variant="body2">
                            Latency: {inferenceMetadata.latency_ms} ms
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="body2">
                            Input Tokens: {inferenceMetadata.tokens_in}
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="body2">
                            Output Tokens: {inferenceMetadata.tokens_out}
                          </Typography>
                        </Grid>
                      </Grid>
                    </>
                  )}
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      )}

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
      />
    </Container>
  );
}
