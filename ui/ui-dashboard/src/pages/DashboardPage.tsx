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
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material';
import { 
  Memory as MemoryIcon, 
  Speed as SpeedIcon, 
  Code as CodeIcon 
} from '@mui/icons-material';
import { deploymentService, DeploymentStatus } from '../api/deploymentService';
import { benchmarkService, BenchmarkRun } from '../api/benchmarkService';

export default function DashboardPage() {
  const [deployments, setDeployments] = useState<DeploymentStatus[]>([]);
  const [recentBenchmarks, setRecentBenchmarks] = useState<BenchmarkRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [deploymentsData, benchmarksData] = await Promise.all([
        deploymentService.getDeployments(),
        benchmarkService.getBenchmarkRuns()
      ]);
      
      setDeployments(deploymentsData);
      setRecentBenchmarks(benchmarksData.slice(0, 5)); // Get the 5 most recent benchmark runs
      setError(null);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to fetch dashboard data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    
    // Set up a refresh interval (every 30 seconds)
    const intervalId = setInterval(fetchDashboardData, 30000);
    
    // Clean up the interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  const activeDeployments = deployments.filter(d => d.status === 'ready').length;
  const pendingDeployments = deployments.filter(d => ['pending', 'deploying'].includes(d.status)).length;
  const failedDeployments = deployments.filter(d => d.status === 'failed').length;

  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
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
      ) : (
        <>
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {/* Summary Cards */}
            <Grid item xs={12} md={4}>
              <Paper
                sx={{
                  p: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  height: 140,
                  bgcolor: 'success.light',
                  color: 'white'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <MemoryIcon sx={{ mr: 1 }} />
                  <Typography component="h2" variant="h6">
                    Active Deployments
                  </Typography>
                </Box>
                <Typography component="p" variant="h3">
                  {activeDeployments}
                </Typography>
                <Typography variant="body2">
                  {pendingDeployments} pending, {failedDeployments} failed
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper
                sx={{
                  p: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  height: 140,
                  bgcolor: 'primary.light',
                  color: 'white'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <SpeedIcon sx={{ mr: 1 }} />
                  <Typography component="h2" variant="h6">
                    Recent Benchmarks
                  </Typography>
                </Box>
                <Typography component="p" variant="h3">
                  {recentBenchmarks.length}
                </Typography>
                <Typography variant="body2">
                  {recentBenchmarks.filter(b => b.status === 'completed').length} completed
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper
                sx={{
                  p: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  height: 140,
                  bgcolor: 'info.light',
                  color: 'white'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <CodeIcon sx={{ mr: 1 }} />
                  <Typography component="h2" variant="h6">
                    Available Models
                  </Typography>
                </Box>
                <Typography component="p" variant="h3">
                  {/* This would ideally be fetched from the API */}
                  3
                </Typography>
                <Typography variant="body2">
                  Ready for deployment
                </Typography>
              </Paper>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            {/* Active Deployments */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Active Deployments" />
                <CardContent>
                  {deployments.filter(d => d.status === 'ready').length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      No active deployments found.
                    </Typography>
                  ) : (
                    <List>
                      {deployments
                        .filter(d => d.status === 'ready')
                        .map((deployment) => (
                          <div key={`${deployment.model}-${deployment.runtime}`}>
                            <ListItem>
                              <ListItemText
                                primary={deployment.model}
                                secondary={`Runtime: ${deployment.runtime}, Quant: ${deployment.quant}`}
                              />
                            </ListItem>
                            <Divider component="li" />
                          </div>
                        ))}
                    </List>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Recent Benchmarks */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Recent Benchmarks" />
                <CardContent>
                  {recentBenchmarks.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      No recent benchmarks found.
                    </Typography>
                  ) : (
                    <List>
                      {recentBenchmarks.map((benchmark) => (
                        <div key={benchmark.id}>
                          <ListItem>
                            <ListItemText
                              primary={benchmark.model}
                              secondary={`Status: ${benchmark.status}, Runtimes: ${benchmark.runtimes.join(', ')}`}
                            />
                          </ListItem>
                          <Divider component="li" />
                        </div>
                      ))}
                    </List>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Container>
  );
}
