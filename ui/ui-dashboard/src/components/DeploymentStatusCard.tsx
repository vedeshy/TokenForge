import { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  CircularProgress,
  Collapse,
  IconButton
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { DeploymentStatus } from '../api/deploymentService';

interface DeploymentStatusCardProps {
  deployment: DeploymentStatus;
  onRefresh: () => void;
}

export default function DeploymentStatusCard({ deployment, onRefresh }: DeploymentStatusCardProps) {
  const [expanded, setExpanded] = useState(false);

  const handleExpandClick = () => {
    setExpanded(!expanded);
  };

  const getStatusIcon = () => {
    switch (deployment.status) {
      case 'ready':
        return <CheckCircleIcon sx={{ color: 'success.main' }} />;
      case 'failed':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      case 'pending':
      case 'deploying':
        return <PendingIcon sx={{ color: 'warning.main' }} />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (deployment.status) {
      case 'ready':
        return 'success';
      case 'failed':
        return 'error';
      case 'pending':
      case 'deploying':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="h6" component="div">
            {deployment.model}
          </Typography>
          <Chip 
            icon={getStatusIcon()} 
            label={deployment.status} 
            color={getStatusColor()} 
            size="small" 
          />
        </Box>
        
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Runtime: {deployment.runtime}
        </Typography>
        
        <Typography variant="body2" color="text.secondary">
          Quantization: {deployment.quant}
        </Typography>
        
        {deployment.status === 'deploying' && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
            <CircularProgress size={20} sx={{ mr: 1 }} />
            <Typography variant="body2">Deployment in progress...</Typography>
          </Box>
        )}
      </CardContent>
      
      <CardActions disableSpacing>
        <Button 
          size="small" 
          startIcon={<RefreshIcon />}
          onClick={onRefresh}
        >
          Refresh
        </Button>
        
        <IconButton
          onClick={handleExpandClick}
          aria-expanded={expanded}
          aria-label="show more"
          sx={{ ml: 'auto', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
          <ExpandMoreIcon />
        </IconButton>
      </CardActions>
      
      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <CardContent>
          <Typography variant="subtitle2">Details:</Typography>
          
          {deployment.endpoint && (
            <Typography variant="body2" paragraph>
              Endpoint: {deployment.endpoint}
            </Typography>
          )}
          
          {deployment.error && (
            <Typography variant="body2" color="error" paragraph>
              Error: {deployment.error}
            </Typography>
          )}
          
          <Typography variant="body2">
            Created: {new Date(deployment.created_at).toLocaleString()}
          </Typography>
          
          <Typography variant="body2">
            Last Updated: {new Date(deployment.updated_at).toLocaleString()}
          </Typography>
        </CardContent>
      </Collapse>
    </Card>
  );
}
