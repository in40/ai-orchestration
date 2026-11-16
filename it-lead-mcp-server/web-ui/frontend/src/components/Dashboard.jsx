import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Avatar,
  Box,
  CircularProgress,
  Alert
} from '@mui/material';
import axios from 'axios';
import { useWebSocket } from '../hooks/useWebSocket';

const Dashboard = () => {
  const [agents, setAgents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // WebSocket hook for real-time updates
  const { sendMessage, lastMessage } = useWebSocket('ws://localhost:8000/ws');

  useEffect(() => {
    // Load initial data - use dynamic planner endpoint for all agents from registry
    const loadData = async () => {
      try {
        setLoading(true);
        const [agentsResponse, tasksResponse] = await Promise.all([
          axios.get('/api/planner/agents'),
          axios.get('/api/tasks')
        ]);

        // Extract agents from the response (handles both formats)
        const agentsData = agentsResponse.data.success 
          ? agentsResponse.data.agents || []
          : agentsResponse.data;
        setAgents(agentsData);
        setTasks(tasksResponse.data);
        setError(null);
      } catch (err) {
        setError('Failed to load data');
        console.error('Error loading dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();

    // Request agent list via WebSocket
    sendMessage({ type: 'get_agents' });
  }, []);

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      if (lastMessage.type === 'agent_list') {
        setAgents(lastMessage.data);
      } else if (lastMessage.type === 'task_assigned' || lastMessage.type === 'task_updated') {
        // Refresh tasks when updates come through WebSocket
        axios.get('/api/tasks').then(response => {
          setTasks(response.data);
        });
      }
    }
  }, [lastMessage]);

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

  // Calculate stats
  const onlineAgents = agents.filter(agent => agent.status === 'online').length;
  const activeTasks = tasks.filter(task => task.status !== 'completed').length;
  const completedTasks = tasks.filter(task => task.status === 'completed').length;

  return (
    <Grid container spacing={3}>
      {/* Stats Cards */}
      <Grid item xs={12} sm={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" color="textSecondary">Online Agents</Typography>
            <Typography variant="h4">{onlineAgents}/{agents.length}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" color="textSecondary">Active Tasks</Typography>
            <Typography variant="h4">{activeTasks}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" color="textSecondary">Completed Tasks</Typography>
            <Typography variant="h4">{completedTasks}</Typography>
          </CardContent>
        </Card>
      </Grid>

      {/* Active Tasks Section */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h5" gutterBottom>Active Tasks</Typography>
            {tasks.filter(task => task.status !== 'completed').map((task, index) => (
              <Box key={index} sx={{ mb: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
                <Typography variant="subtitle1">{task.title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Assigned to: {task.assignee} | Priority: {task.priority}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                  <Box sx={{ width: '100%', mr: 1 }}>
                    <div style={{ height: 8, backgroundColor: '#e0e0e0', borderRadius: 4 }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${task.progress}%`,
                          backgroundColor: task.priority === 'high' ? '#f44336' : task.priority === 'medium' ? '#ff9800' : '#4caf50',
                          borderRadius: 4
                        }}
                      />
                    </div>
                  </Box>
                  <Typography variant="body2">{task.progress}%</Typography>
                </Box>
              </Box>
            ))}
          </CardContent>
        </Card>
      </Grid>

      {/* Team Members Section */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h5" gutterBottom>Team Members</Typography>
            {agents.map((agent, index) => (
              <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 2, p: 1 }}>
                <Avatar sx={{
                  bgcolor: agent.status === 'online' ? 'success.main' : 'grey.500',
                  width: 32,
                  height: 32,
                  mr: 2
                }}>
                  {agent.name.charAt(0)}
                </Avatar>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="subtitle1">{agent.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Status: {agent.status} | Last seen: {new Date(agent.last_seen).toLocaleTimeString()}
                  </Typography>
                </Box>
                <Chip
                  label={agent.status}
                  size="small"
                  color={agent.status === 'online' ? 'success' : 'default'}
                />
              </Box>
            ))}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default Dashboard;
