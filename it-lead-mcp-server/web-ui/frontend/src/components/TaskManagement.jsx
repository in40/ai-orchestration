import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  CircularProgress,
  Alert,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, History as HistoryIcon, Delete as DeleteIcon } from '@mui/icons-material';
import axios from 'axios';

const TaskManagement = () => {
  const [tasks, setTasks] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openTaskDialog, setOpenTaskDialog] = useState(false);
  const [openHistoryDialog, setOpenHistoryDialog] = useState(false);
  const [selectedTaskHistory, setSelectedTaskHistory] = useState(null);
  const [taskForm, setTaskForm] = useState({
    title: '',
    description: '',
    assignee: '',
    priority: 'medium',
    dueDate: ''
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [tasksResponse, agentsResponse] = await Promise.all([
          axios.get('/api/tasks'),
          axios.get('/api/agents')
        ]);
        
        setTasks(tasksResponse.data);
        setAgents(agentsResponse.data);
        setError(null);
      } catch (err) {
        setError('Failed to load tasks or agents');
        console.error('Error loading tasks or agents:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleAddTask = () => {
    setTaskForm({
      title: '',
      description: '',
      assignee: '',
      priority: 'medium',
      dueDate: ''
    });
    setOpenTaskDialog(true);
  };

  const handleCloseTaskDialog = () => {
    setOpenTaskDialog(false);
  };

  const handleTaskSubmit = async () => {
    try {
      await axios.post('/api/tasks/assign', {
        task_id: `task-${Date.now()}`,
        title: taskForm.title,
        description: taskForm.description,
        assignee: taskForm.assignee,
        priority: taskForm.priority,
        due_date: taskForm.dueDate
      });
      
      // Refresh tasks
      const response = await axios.get('/api/tasks');
      setTasks(response.data);
      
      handleCloseTaskDialog();
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

  const handleViewHistory = async (taskId) => {
    try {
      const response = await axios.get(`/api/tasks/${taskId}/history`);
      setSelectedTaskHistory(response.data);
      setOpenHistoryDialog(true);
    } catch (err) {
      console.error('Error loading task history:', err);
      alert('Failed to load task history');
    }
  };

  const handleCloseHistoryDialog = () => {
    setOpenHistoryDialog(false);
    setSelectedTaskHistory(null);
  };

  const handleDelete = async (taskId) => {
    if (!window.confirm("Are you sure?")) return;
    try {
      await axios.post('/api/tasks/delete', { task_id: taskId });
      setTasks(prevTasks => prevTasks.filter(task => task.id !== taskId));
    } catch (err) {
      console.error("Error deleting task:", err);
      alert("Failed to delete task");
    }
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

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">Task Management</Typography>
          <Button 
            variant="contained" 
            startIcon={<AddIcon />}
            onClick={handleAddTask}
          >
            Add Task
          </Button>
        </Box>
      </Grid>

      <Grid item xs={12}>
        <Card>
          <CardContent>
            <TableContainer component={Paper}>
              <Table sx={{ minWidth: 650 }} aria-label="tasks table">
                <TableHead>
                  <TableRow>
                    <TableCell>Title</TableCell>
                    <TableCell>Assignee</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Priority</TableCell>
                    <TableCell>Progress</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tasks.map((task) => (
                    <TableRow
                      key={task.id}
                      sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                    >
                      <TableCell component="th" scope="row">
                        {task.title}
                      </TableCell>
                      <TableCell>{task.assignee}</TableCell>
                      <TableCell>
                        <Chip 
                          label={task.status} 
                          size="small" 
                          color={
                            task.status === 'completed' ? 'success' : 
                            task.status === 'in-progress' ? 'info' : 
                            task.status === 'pending' ? 'warning' : 'default'
                          } 
                        />
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={task.priority} 
                          size="small" 
                          color={
                            task.priority === 'critical' ? 'error' : 
                            task.priority === 'high' ? 'warning' : 
                            task.priority === 'medium' ? 'info' : 'default'
                          } 
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
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
                      </TableCell>
                      <TableCell align="right">
                      <IconButton 
                        color="primary" 
                        aria-label="view history"
                        onClick={() => handleViewHistory(task.id)}
                      >
                        <HistoryIcon />
                      </IconButton>
                      <IconButton 
                        color="error" 
                        aria-label="delete task"
                        onClick={() => handleDelete(task.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Task Creation Dialog */}
      <Dialog open={openTaskDialog} onClose={handleCloseTaskDialog}>
        <DialogTitle>Create New Task</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Enter the details for the new task.
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
            <InputLabel>Assign To</InputLabel>
            <Select
              name="assignee"
              value={taskForm.assignee}
              label="Assign To"
              onChange={handleInputChange}
            >
              {agents.map((agent, idx) => (
                <MenuItem key={idx} value={agent.name}>{agent.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          
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
          <Button onClick={handleTaskSubmit} variant="contained">Create Task</Button>
        </DialogActions>
      </Dialog>

      {/* Task History Dialog */}
      <Dialog 
        open={openHistoryDialog} 
        onClose={handleCloseHistoryDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Task History</DialogTitle>
        <DialogContent>
          {selectedTaskHistory && (
            <Box>
              <Typography variant="h6" gutterBottom>
                {selectedTaskHistory.title}
              </Typography>
              
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="textSecondary">Task ID</Typography>
                  <Typography variant="body1">{selectedTaskHistory.task_id}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="textSecondary">Current Status</Typography>
                  <Chip 
                    label={selectedTaskHistory.current_status} 
                    size="small"
                    color={
                      selectedTaskHistory.current_status === 'completed' ? 'success' :
                      selectedTaskHistory.current_status === 'in_progress' ? 'info' :
                      selectedTaskHistory.current_status === 'received' ? 'warning' : 'default'
                    }
                  />
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="textSecondary">Assigned To</Typography>
                  <Typography variant="body1">{selectedTaskHistory.assigned_to}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="textSecondary">Submitter</Typography>
                  <Typography variant="body1">
                    {selectedTaskHistory.submitter} ({selectedTaskHistory.submitter_type})
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="textSecondary">Transport Channel</Typography>
                  <Typography variant="body1">{selectedTaskHistory.transport_channel}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="textSecondary">Created At</Typography>
                  <Typography variant="body1">
                    {selectedTaskHistory.created_at ? 
                      new Date(selectedTaskHistory.created_at).toLocaleString() : 
                      'N/A'}
                  </Typography>
                </Grid>
              </Grid>

              <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
                Status History ({selectedTaskHistory.status_history?.length || 0} changes)
              </Typography>

              {selectedTaskHistory.status_history && selectedTaskHistory.status_history.length > 0 ? (
                <Box>
                  {selectedTaskHistory.status_history.map((entry, index) => (
                    <Paper 
                      key={index} 
                      sx={{ 
                        p: 2, 
                        mb: 1,
                        borderLeft: 4,
                        borderColor: 
                          entry.status === 'completed' ? 'success.main' :
                          entry.status === 'in_progress' ? 'info.main' :
                          entry.status === 'received' ? 'warning.main' : 'grey.500'
                      }}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Chip 
                          label={entry.status} 
                          size="small"
                          color={
                            entry.status === 'completed' ? 'success' :
                            entry.status === 'in_progress' ? 'info' :
                            entry.status === 'received' ? 'warning' : 'default'
                          }
                        />
                        <Typography variant="caption" color="textSecondary">
                          {entry.datetime ? new Date(entry.datetime).toLocaleString() : `Timestamp: ${entry.timestamp}`}
                        </Typography>
                      </Box>
                      {entry.reason && (
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          {entry.reason}
                        </Typography>
                      )}
                    </Paper>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="textSecondary">
                  No status history available
                </Typography>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseHistoryDialog}>Close</Button>
        </DialogActions>
      </Dialog>
    </Grid>
  );
};

export default TaskManagement;