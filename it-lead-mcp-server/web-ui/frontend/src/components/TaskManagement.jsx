import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
  IconButton,
  Drawer,
  Link
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, History as HistoryIcon, Delete as DeleteIcon, OpenInNew as OpenInNewIcon, Close as CloseIcon, Description as DescriptionIcon } from '@mui/icons-material';
import axios from 'axios';

// Import enhanced AddTaskForm component
import AddTaskForm from './enhanced/AddTaskForm';

const TaskManagement = () => {
  const [tasks, setTasks] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openTaskDialog, setOpenTaskDialog] = useState(false);
  const [openHistoryDialog, setOpenHistoryDialog] = useState(false);
  const [selectedTaskHistory, setSelectedTaskHistory] = useState(null);
  const [openFilePreview, setOpenFilePreview] = useState(false);
  const [previewFileContent, setPreviewFileContent] = useState('');
  const [previewFileName, setPreviewFileName] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  // Enhanced task form state with all required fields for MCP integration
  const [enhancedTaskData, setEnhancedTaskData] = useState({
    title: '',
    description: '',
    assignee: 'IT Lead',  // Default to IT Lead for intelligent routing
    priority: 'medium',
    dueDate: '',
    tags: [],
    context: {},
    dependencies: []
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

  // Open the enhanced task dialog with default values
  const handleAddTask = () => {
    setEnhancedTaskData({
      title: '',
      description: '',
      assignee: 'IT Lead',
      priority: 'medium',
      dueDate: '',
      tags: [],
      context: {},
      dependencies: []
    });
    setOpenTaskDialog(true);
  };

  const handleCloseTaskDialog = () => {
    setOpenTaskDialog(false);
  };

  // Submit enhanced task with full metadata
  const handleEnhancedTaskSubmit = async (taskData) => {
    try {
      await axios.post('/api/tasks/assign', {
        ...taskData,
        id: taskData.id || `task-${Date.now()}`
      });

      // Refresh tasks from server to show assigned status and routing results
      const response = await axios.get('/api/tasks');
      setTasks(response.data);

      handleCloseTaskDialog();
    } catch (err) {
      console.error('Error assigning task:', err);
      alert(`Failed to assign task: ${err.response?.data?.error || 'Unknown error'}`);
    }
  };

  // Update enhanced form field
  const handleEnhancedInputChange = (field) => (e) => {
    setEnhancedTaskData(prev => ({
      ...prev,
      [field]: e.target.value
    }));
  };

  // Legacy: keep for any existing references, redirects to enhanced version
  const handleInputChange = handleEnhancedInputChange;

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

  const handleOpenFilePreview = async (task) => {
    try {
      setPreviewLoading(true);
      const taskId = task.task_id || task.id;
      const filename = 'result.md'; // Default to result.md for Markdown files
      
      const response = await axios.get(`/api/tasks/${taskId}/files/${filename}`);
      setPreviewFileContent(response.data.content);
      setPreviewFileName(response.data.filename || filename);
      setOpenFilePreview(true);
    } catch (err) {
      console.error('Error loading file preview:', err);
      alert('Failed to load file preview');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCloseFilePreview = () => {
    setOpenFilePreview(false);
    setPreviewFileContent('');
    setPreviewFileName('');
  };

  const handleDelete = async (taskId) => {
    if (!window.confirm("Are you sure?")) return;
    try {
      await axios.post('/api/tasks/delete', { task_id: taskId });
      // Refresh tasks from server
      const response = await axios.get('/api/tasks');
      setTasks(response.data);
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
                      {/* View Result Button - shows for completed tasks with git_url */}
                      {task.git_url && (task.status === 'done' || task.status === 'completed') && (
                        <IconButton
                          color="success"
                          aria-label="view result"
                          onClick={() => {
                            const taskId = task.id;
                            // Try to determine file extension from git_url or default to .py
                            let ext = '.py';
                            if (task.git_url.includes('.html')) ext = '.html';
                            else if (task.git_url.includes('.md')) ext = '.md';
                            else if (task.git_url.includes('.js')) ext = '.js';
                            
                            // Extract task UUID from git_url
                            const uuidMatch = task.git_url.match(/results\/([a-f0-9-]+)\//);
                            const taskUuid = uuidMatch ? uuidMatch[1] : taskId;
                            
                            // Option 1: Direct Git server link (if Git server has HTTP access)
                            // const gitServerUrl = `http://192.168.51.187/results/${taskUuid}/result${ext}`;
                            
                            // Option 2: Web UI backend proxy (works if Web UI server is accessible)
                            // Get current host (works from any computer accessing the Web UI)
                            const currentHost = window.location.origin;
                            const resultUrl = `${currentHost}/api/git/files/${taskUuid}/result${ext}`;
                            
                            window.open(resultUrl, '_blank');
                          }}
                          title="View Generated Code"
                        >
                          <DescriptionIcon />
                        </IconButton>
                      )}
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

      {/* Enhanced Add Task Form Dialog */}
      <AddTaskForm
        open={openTaskDialog}
        onClose={handleCloseTaskDialog}
        onSubmit={handleEnhancedTaskSubmit}
        agents={agents}
      />


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
                {selectedTaskHistory.storage_type && (
                  <Grid item xs={6}>
                    <Typography variant="subtitle2" color="textSecondary">Storage Type</Typography>
                    <Chip
                      label={selectedTaskHistory.storage_type}
                      size="small"
                      color={selectedTaskHistory.storage_type === 'git' ? 'success' : 'default'}
                    />
                  </Grid>
                )}
                {selectedTaskHistory.git_url && (
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" color="textSecondary">Result Location</Typography>
                    
                    {/* Direct Git Server Link (if Git server has HTTP interface) */}
                    <Box sx={{ mt: 1, p: 1, bgcolor: 'primary.light', borderRadius: 1 }}>
                      <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: 0.5 }}>
                        Git Server (SSH):
                      </Typography>
                      <Typography variant="body2" sx={{ wordBreak: 'break-all', fontFamily: 'monospace' }}>
                        {selectedTaskHistory.git_url}
                      </Typography>
                    </Box>
                    
                    {/* Web UI HTTP Access */}
                    <Box sx={{ mt: 1, p: 1, bgcolor: 'success.light', borderRadius: 1 }}>
                      <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: 0.5 }}>
                        HTTP Access (via Web UI):
                      </Typography>
                      <Link
                        href={`${window.location.origin}/api/git/files/${selectedTaskHistory.task_id}/result.py`}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ wordBreak: 'break-all', display: 'block', mb: 1 }}
                      >
                        {window.location.origin}/api/git/files/{selectedTaskHistory.task_id}/result.py
                      </Link>
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<OpenInNewIcon />}
                        href={`${window.location.origin}/api/git/files/${selectedTaskHistory.task_id}/result.py`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Open in New Tab
                      </Button>
                    </Box>
                    
                    {/* Action Buttons */}
                    <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<DescriptionIcon />}
                        onClick={() => handleOpenFilePreview(selectedTaskHistory)}
                      >
                        Preview
                      </Button>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<OpenInNewIcon />}
                        href={selectedTaskHistory.git_url.replace('ssh://', 'http://').replace(/:\d+/, '')}
                        target="_blank"
                        rel="noopener noreferrer"
                        disabled={!selectedTaskHistory.git_url.includes('192.168.51')}
                      >
                        Git Server Web
                      </Button>
                    </Box>
                  </Grid>
                )}
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

      {/* File Preview Drawer */}
      <Drawer
        anchor="right"
        open={openFilePreview}
        onClose={handleCloseFilePreview}
        PaperProps={{
          sx: { width: '60%', maxWidth: '800px' }
        }}
      >
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <DescriptionIcon color="primary" />
            <Typography variant="h6">{previewFileName}</Typography>
          </Box>
          <IconButton onClick={handleCloseFilePreview} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        <Box sx={{ p: 3, overflow: 'auto', height: 'calc(100% - 70px)' }}>
          {previewLoading ? (
            <Box display="flex" justifyContent="center" alignItems="center" height="200px">
              <CircularProgress />
            </Box>
          ) : previewFileContent ? (
            <Box
              sx={{
                '& h1': { fontSize: '2em', fontWeight: 600, mt: 3, mb: 2 },
                '& h2': { fontSize: '1.5em', fontWeight: 600, mt: 2.5, mb: 1.5 },
                '& h3': { fontSize: '1.25em', fontWeight: 600, mt: 2, mb: 1 },
                '& p': { mb: 1.5, lineHeight: 1.7 },
                '& code': {
                  backgroundColor: '#f5f5f5',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  fontFamily: 'monospace',
                  fontSize: '0.9em'
                },
                '& pre': {
                  backgroundColor: '#f6f8fa',
                  padding: 2,
                  borderRadius: 1,
                  overflow: 'auto',
                  '& code': {
                    backgroundColor: 'transparent',
                    padding: 0
                  }
                },
                '& ul, & ol': { mb: 1.5, pl: 3 },
                '& li': { mb: 0.5 },
                '& blockquote': {
                  borderLeft: 4,
                  borderColor: 'divider',
                  pl: 2,
                  my: 2,
                  color: 'text.secondary'
                },
                '& table': {
                  borderCollapse: 'collapse',
                  width: '100%',
                  mb: 2,
                  '& th, & td': {
                    border: 1,
                    borderColor: 'divider',
                    p: 1,
                    textAlign: 'left'
                  },
                  '& th': { backgroundColor: 'action.hover' }
                },
                '& hr': { my: 3 },
                '& a': { color: 'primary.main', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }
              }}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {previewFileContent}
              </ReactMarkdown>
            </Box>
          ) : (
            <Typography variant="body2" color="textSecondary">
              No content available
            </Typography>
          )}
        </Box>
      </Drawer>
    </Grid>
  );
};

export default TaskManagement;