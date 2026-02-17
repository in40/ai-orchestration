import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Chip,
  Avatar,
  Box,
  Button,
  CircularProgress,
  Alert,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { formatDistanceToNow } from 'date-fns';

const AgentDetail = () => {
  const { agentName } = useParams();
  const navigate = useNavigate();
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openTaskDialog, setOpenTaskDialog] = useState(false);
  const [taskForm, setTaskForm] = useState({
    title: '',
    description: '',
    priority: 'medium',
    dueDate: ''
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`/api/agents/${encodeURIComponent(agentName)}`);
        setAgent(response.data);
        setError(null);
      } catch (err) {
        setError('Failed to load agent details');
        console.error('Error loading agent details:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [agentName]);

  const handleAssignTask = () => {
    setOpenTaskDialog(true);
  };

  const handleCloseTaskDialog = () => {
    setOpenTaskDialog(false);
    setTaskForm({
      title: '',
      description: '',
      priority: 'medium',
      dueDate: ''
    });
  };

  const handleTaskSubmit = async () => {
    try {
      await axios.post('/api/tasks/assign', {
        task_id: `task-${Date.now()}`,
        title: taskForm.title,
        description: taskForm.description,
        assignee: agentName,
        priority: taskForm.priority,
        due_date: taskForm.dueDate
      });
      
      handleCloseTaskDialog();
      // Optionally show success message
    } catch (err) {
      console.error('Error assigning task:', err);
      alert('Failed to assign task');
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setTaskForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

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

  if (!agent) {
    return (
      <Alert severity="warning">Agent not found</Alert>
    );
  }

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Avatar sx={{ 
                bgcolor: agent.status === 'online' ? 'success.main' : 'grey.500', 
                width: 80, 
                height: 80,
                mr: 3 
              }}>
                {agent.name.charAt(0)}
              </Avatar>
              <Box>
                <Typography variant="h4">{agent.name}</Typography>
                <Chip 
                  label={agent.status} 
                  size="large" 
                  color={agent.status === 'online' ? 'success' : 'default'} 
                />
                <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
                  Last seen: {formatDistanceToNow(new Date(agent.last_seen), { addSuffix: true })}
                </Typography>
                {agent.uptime && (
                  <Typography variant="body2" color="text.secondary">
                    Uptime: {agent.uptime}
                  </Typography>
                )}
                {agent.version && (
                  <Typography variant="body2" color="text.secondary">
                    Version: {agent.version}
                  </Typography>
                )}
              </Box>
            </Box>
            
            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
              <Button 
                variant="contained" 
                onClick={handleAssignTask}
              >
                Assign Task
              </Button>
              <Button 
                variant="outlined" 
                onClick={() => navigate('/team')}
              >
                Back to Team
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Capabilities</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {agent.capabilities.map((capability, idx) => (
                <Chip key={idx} label={capability} size="small" variant="outlined" />
              ))}
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Current Status</Typography>
            <Typography variant="body1">
              <strong>Status:</strong> {agent.status}
            </Typography>
            <Typography variant="body1">
              <strong>Last Seen:</strong> {new Date(agent.last_seen).toLocaleString()}
            </Typography>
            {agent.uptime && (
              <Typography variant="body1">
                <strong>Uptime:</strong> {agent.uptime}
              </Typography>
            )}
            {agent.version && (
              <Typography variant="body1">
                <strong>Version:</strong> {agent.version}
              </Typography>
            )}
          </CardContent>
        </Card>
      </Grid>

      {/* Task Assignment Dialog */}
      <Dialog open={openTaskDialog} onClose={handleCloseTaskDialog}>
        <DialogTitle>Assign Task to {agent.name}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Fill in the details for the task you want to assign to {agent.name}.
          </DialogContentText>
          
          <TextField
            autoFocus
            margin="dense"
            name="title"
            label="Task Title"
            type="text"
            fullWidth
            variant="outlined"
            value={taskForm.title}
            onChange={handleInputChange}
            sx={{ mt: 2 }}
          />
          
          <TextField
            margin="dense"
            name="description"
            label="Description"
            type="text"
            fullWidth
            multiline
            rows={4}
            variant="outlined"
            value={taskForm.description}
            onChange={handleInputChange}
          />
          
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Priority</InputLabel>
            <Select
              name="priority"
              value={taskForm.priority}
              label="Priority"
              onChange={handleInputChange}
            >
              <MenuItem value="low">Low</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="high">High</MenuItem>
              <MenuItem value="critical">Critical</MenuItem>
            </Select>
          </FormControl>
          
          <TextField
            margin="dense"
            name="dueDate"
            label="Due Date"
            type="date"
            fullWidth
            variant="outlined"
            value={taskForm.dueDate}
            onChange={handleInputChange}
            InputLabelProps={{
              shrink: true,
            }}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseTaskDialog}>Cancel</Button>
          <Button onClick={handleTaskSubmit} variant="contained">Assign Task</Button>
        </DialogActions>
      </Dialog>
    </Grid>
  );
};

export default AgentDetail;