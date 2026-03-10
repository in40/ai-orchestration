import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Avatar,
  Box,
  Button,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Divider
} from '@mui/material';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { formatDistanceToNow } from 'date-fns';

const TeamMembers = () => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tabValue, setTabValue] = useState(0);

  // Load agents from registry using dynamic discovery
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Use the new dynamic planning endpoint to get all agents from registry
        const response = await axios.get('/api/planner/agents');
        
        if (response.data.success) {
          setAgents(response.data.agents || []);
          setError(null);
        } else {
          setError('Failed to load team members');
        }
      } catch (err) {
        setError('Failed to load team members from registry');
        console.error('Error loading team members:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
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
    <Grid container spacing={3}>
      {agents.map((agent, index) => (
        <Grid item xs={12} md={6} lg={4} key={index}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ 
                  bgcolor: agent.status === 'online' ? 'success.main' : 'grey.500', 
                  width: 56, 
                  height: 56,
                  mr: 2 
                }}>
                  {agent.name.charAt(0)}
                </Avatar>
                <Box>
                  <Typography variant="h6">{agent.name}</Typography>
                  <Chip 
                    label={agent.status} 
                    size="small" 
                    color={agent.status === 'online' ? 'success' : 'default'} 
                  />
                </Box>
              </Box>
              
              <Typography variant="body2" color="text.secondary" paragraph>
                Last seen: {formatDistanceToNow(new Date(agent.last_seen), { addSuffix: true })}
              </Typography>
              
              <Typography variant="subtitle2" gutterBottom>Capabilities:</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {/* Handle both formats: array of strings or array of objects */}
                {agent.capabilities && agent.capabilities.slice(0, 5).map((capability, idx) => {
                  const capabilityName = typeof capability === 'string' ? capability : capability.name;
                  return <Chip key={idx} label={capabilityName} size="small" variant="outlined" />;
                })}
                {agent.capabilities && agent.capabilities.length > 5 && (
                  <Chip label={`+${agent.capabilities.length - 5} more`} size="small" variant="outlined" />
                )}
              </Box>
              
              <Button 
                component={Link} 
                to={`/agent/${encodeURIComponent(agent.name)}`}
                variant="contained" 
                fullWidth
              >
                View Details
              </Button>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default TeamMembers;