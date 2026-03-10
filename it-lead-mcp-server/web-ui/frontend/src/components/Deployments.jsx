import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Link
} from '@mui/material';
import {
  Launch as LaunchIcon,
  Refresh as RefreshIcon,
  Dns as ServerIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import axios from 'axios';

const Deployments = () => {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');

  const fetchDeployments = async (filter = 'all') => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`/api/deployments?status_filter=${filter}`);
      setDeployments(response.data || []);
    } catch (err) {
      setError('Failed to load deployments');
      console.error('Error loading deployments:', err);
      setDeployments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments(statusFilter);
  }, [statusFilter]);

  const handleRefresh = () => {
    fetchDeployments(statusFilter);
  };

  const handleStartDeployment = async (taskId) => {
    try {
      await axios.post(`/api/deployments/${taskId}/start`);
      alert(`Deployment ${taskId} started successfully`);
      fetchDeployments(statusFilter);
    } catch (err) {
      console.error("Error starting deployment:", err);
      alert(`Failed to start deployment: ${err.response?.data?.detail || 'Unknown error'}`);
    }
  };

  const handleStopDeployment = async (taskId) => {
    if (!window.confirm(`Stop deployment ${taskId}?`)) return;
    try {
      await axios.post(`/api/deployments/${taskId}/stop`);
      alert(`Deployment ${taskId} stopped successfully`);
      fetchDeployments(statusFilter);
    } catch (err) {
      console.error("Error stopping deployment:", err);
      alert(`Failed to stop deployment: ${err.response?.data?.detail || 'Unknown error'}`);
    }
  };

  const handleDeleteDeployment = async (taskId) => {
    if (!window.confirm(`Delete deployment ${taskId}? This action cannot be undone.`)) return;
    try {
      await axios.delete(`/api/deployments/${taskId}`);
      alert(`Deployment ${taskId} deleted successfully`);
      fetchDeployments(statusFilter);
    } catch (err) {
      console.error("Error deleting deployment:", err);
      alert(`Failed to delete deployment: ${err.response?.data?.detail || 'Unknown error'}`);
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'running':
        return <CheckCircleIcon color="success" fontSize="small" />;
      case 'stopped':
        return <ErrorIcon color="error" fontSize="small" />;
      case 'pending':
        return <WarningIcon color="warning" fontSize="small" />;
      default:
        return <ServerIcon color="action" fontSize="small" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'running':
        return 'success';
      case 'stopped':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  const openDeployment = (url) => {
    if (url) {
      window.open(url, '_blank');
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" gutterBottom>
          Deployments
        </Typography>
        <Box display="flex" gap={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="stopped">Stopped</MenuItem>
            </Select>
          </FormControl>
          <IconButton onClick={handleRefresh} color="primary">
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <CheckCircleIcon color="success" />
                <Typography variant="h6">
                  {deployments.filter(d => d.status === 'running').length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Running
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <ErrorIcon color="error" />
                <Typography variant="h6">
                  {deployments.filter(d => d.status === 'stopped').length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Stopped
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <ServerIcon color="action" />
                <Typography variant="h6">
                  {deployments.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Deployments Table */}
      {deployments.length === 0 ? (
        <Alert severity="info">
          No deployments found. Deploy a task to see it here.
        </Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Task ID</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Deployment URL</TableCell>
                <TableCell>Host Port</TableCell>
                <TableCell>Container Port</TableCell>
                <TableCell>Docker Image</TableCell>
                <TableCell>Created At</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {deployments.map((deployment, index) => (
                <TableRow key={deployment.task_id || index} hover>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {deployment.task_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={getStatusIcon(deployment.status)}
                      label={deployment.status || 'unknown'}
                      color={getStatusColor(deployment.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {deployment.deployment_url ? (
                      <Link
                        href={deployment.deployment_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ fontSize: '0.875rem' }}
                      >
                        {deployment.deployment_url}
                      </Link>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        N/A
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>{deployment.host_port || 'N/A'}</TableCell>
                  <TableCell>{deployment.container_port || 'N/A'}</TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 150 }}>
                      {deployment.docker_image || 'N/A'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {deployment.created_at 
                        ? new Date(deployment.created_at).toLocaleString()
                        : 'N/A'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => openDeployment(deployment.deployment_url)}
                        disabled={!deployment.deployment_url}
                        title="Open deployed application"
                      >
                        <LaunchIcon />
                      </IconButton>
                      {deployment.status === 'stopped' && (
                        <IconButton
                          size="small"
                          color="success"
                          onClick={() => handleStartDeployment(deployment.task_id)}
                          title="Start deployment"
                        >
                          <PlayIcon />
                        </IconButton>
                      )}
                      {deployment.status === 'running' && (
                        <IconButton
                          size="small"
                          color="warning"
                          onClick={() => handleStopDeployment(deployment.task_id)}
                          title="Stop deployment"
                        >
                          <StopIcon />
                        </IconButton>
                      )}
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteDeployment(deployment.task_id)}
                        title="Delete deployment"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default Deployments;
