import { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Grid,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Box,
  Alert,
  CircularProgress,
  Snackbar
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import DeploymentStatusCard from '../components/DeploymentStatusCard';
import { deploymentService, DeploymentStatus, DeploymentRequest } from '../api/deploymentService';
import { modelService, Model } from '../api/modelService';

export default function DeploymentsPage() {
  const [deployments, setDeployments] = useState<DeploymentStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedRuntime, setSelectedRuntime] = useState('');
  const [selectedQuant, setSelectedQuant] = useState('');
  const [deploying, setDeploying] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  const fetchDeployments = async () => {
    try {
      setLoading(true);
      const data = await deploymentService.getDeployments();
      setDeployments(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching deployments:', err);
      setError('Failed to fetch deployments. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const fetchModels = async () => {
    try {
      const data = await modelService.getModels();
      setModels(data);
    } catch (err) {
      console.error('Error fetching models:', err);
      setError('Failed to fetch models. Please try again later.');
    }
  };

  useEffect(() => {
    fetchDeployments();
    fetchModels();
  }, []);

  const handleRefreshDeployment = () => {
    fetchDeployments();
  };

  const handleOpenDialog = () => {
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedModel('');
    setSelectedRuntime('');
    setSelectedQuant('');
  };

  const handleModelChange = (event: any) => {
    setSelectedModel(event.target.value);
    setSelectedRuntime('');
    setSelectedQuant('');
  };

  const getSupportedRuntimes = () => {
    if (!selectedModel) return [];
    const model = models.find(m => m.name === selectedModel);
    return model ? model.supported_runtimes : [];
  };

  const getQuantizationOptions = () => {
    if (!selectedModel) return [];
    const model = models.find(m => m.name === selectedModel);
    return model ? model.quantization : [];
  };

  const handleDeployModel = async () => {
    if (!selectedModel || !selectedRuntime || !selectedQuant) {
      setSnackbarMessage('Please fill in all fields');
      setSnackbarOpen(true);
      return;
    }

    const deployRequest: DeploymentRequest = {
      model: selectedModel,
      runtime: selectedRuntime,
      quant: selectedQuant
    };

    try {
      setDeploying(true);
      await deploymentService.deployModel(deployRequest);
      setSnackbarMessage('Deployment started successfully');
      setSnackbarOpen(true);
      handleCloseDialog();
      fetchDeployments();
    } catch (err) {
      console.error('Error deploying model:', err);
      setSnackbarMessage('Failed to deploy model. Please try again later.');
      setSnackbarOpen(true);
    } finally {
      setDeploying(false);
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Model Deployments
        </Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />}
          onClick={handleOpenDialog}
        >
          Deploy Model
        </Button>
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
      ) : deployments.length === 0 ? (
        <Alert severity="info" sx={{ mb: 3 }}>
          No deployments found. Deploy a model to get started.
        </Alert>
      ) : (
        <Grid container spacing={3}>
          {deployments.map((deployment) => (
            <Grid item xs={12} md={6} key={`${deployment.model}-${deployment.runtime}`}>
              <DeploymentStatusCard 
                deployment={deployment} 
                onRefresh={handleRefreshDeployment} 
              />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Deploy Model Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog}>
        <DialogTitle>Deploy Model</DialogTitle>
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

          <FormControl fullWidth margin="normal" disabled={!selectedModel}>
            <InputLabel id="runtime-select-label">Runtime</InputLabel>
            <Select
              labelId="runtime-select-label"
              id="runtime-select"
              value={selectedRuntime}
              label="Runtime"
              onChange={(e) => setSelectedRuntime(e.target.value)}
            >
              {getSupportedRuntimes().map((runtime) => (
                <MenuItem key={runtime} value={runtime}>
                  {runtime}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth margin="normal" disabled={!selectedModel}>
            <InputLabel id="quant-select-label">Quantization</InputLabel>
            <Select
              labelId="quant-select-label"
              id="quant-select"
              value={selectedQuant}
              label="Quantization"
              onChange={(e) => setSelectedQuant(e.target.value)}
            >
              {getQuantizationOptions().map((quant) => (
                <MenuItem key={quant} value={quant}>
                  {quant}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button 
            onClick={handleDeployModel} 
            variant="contained" 
            disabled={!selectedModel || !selectedRuntime || !selectedQuant || deploying}
          >
            {deploying ? <CircularProgress size={24} /> : 'Deploy'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
      />
    </Container>
  );
}
