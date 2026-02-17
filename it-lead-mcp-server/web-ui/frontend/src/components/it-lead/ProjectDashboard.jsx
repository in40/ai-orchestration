import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Box,
  Grid,
  CircularProgress,
  Alert
} from '@mui/material';
import axios from 'axios';

const ProjectDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    dashboard_view: 'manager',
    time_range: 'week',
    project_filters: [],
    custom_metrics: []
  });

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.post('/api/dashboard/view', filters);
      setDashboardData(response.data);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Load initial dashboard data
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error">{error}</Alert>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Project Dashboard
        </Typography>
        
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth margin="normal">
              <InputLabel>Dashboard View</InputLabel>
              <Select
                name="dashboard_view"
                value={filters.dashboard_view}
                label="Dashboard View"
                onChange={handleFilterChange}
              >
                <MenuItem value="executive">Executive</MenuItem>
                <MenuItem value="manager">Manager</MenuItem>
                <MenuItem value="technical">Technical</MenuItem>
                <MenuItem value="quality">Quality</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <FormControl fullWidth margin="normal">
              <InputLabel>Time Range</InputLabel>
              <Select
                name="time_range"
                value={filters.time_range}
                label="Time Range"
                onChange={handleFilterChange}
              >
                <MenuItem value="week">Week</MenuItem>
                <MenuItem value="month">Month</MenuItem>
                <MenuItem value="quarter">Quarter</MenuItem>
                <MenuItem value="custom">Custom</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={6} display="flex" alignItems="end">
            <Button 
              variant="contained" 
              onClick={fetchDashboardData}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Refresh Dashboard'}
            </Button>
          </Grid>
        </Grid>
        
        {dashboardData ? (
          <Box>
            <Typography variant="h6">Dashboard Data</Typography>
            <pre>{JSON.stringify(dashboardData, null, 2)}</pre>
          </Box>
        ) : (
          <Typography>No dashboard data available</Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default ProjectDashboard;