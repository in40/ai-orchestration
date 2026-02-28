import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  FormHelperText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import {
  Add as AddIcon,
  ExpandMore as ExpandMoreIcon,
  SmartToy as SmartToyIcon,
  Route as RouteIcon,
  Code as CodeIcon,
  DocumentScanner as DocumentIcon,
  Schedule as ScheduleIcon,
  AttachFile as AttachFileIcon
} from '@mui/icons-material';

const AddTaskForm = ({ 
  open, 
  onClose, 
  onSubmit, 
  agents 
}) => {
  const [taskData, setTaskData] = useState({
    title: '',
    description: '',
    assignee: 'IT Lead', // Default to IT Lead for intelligent routing
    priority: 'medium',
    dueDate: '',
    tags: [],
    attachments: [],
    context: {},
    dependencies: []
  });

  const [errors, setErrors] = useState({});
  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    routing: false,
    metadata: false
  });
  const [availableAgents, setAvailableAgents] = useState([]);

  useEffect(() => {
    if (agents && agents.length > 0) {
      // Filter and sort agents by capability relevance
      const sortedAgents = [...agents].sort((a, b) => {
        // IT Lead should always be first for routing decisions
        if (a.name.toLowerCase().includes('lead')) return -1;
        if (b.name.toLowerCase().includes('lead')) return 1;
        return 0;
      });
      setAvailableAgents(sortedAgents);
    }
  }, [agents]);

  const validateForm = () => {
    const newErrors = {};
    
    if (!taskData.title.trim()) {
      newErrors.title = 'Task title is required';
    } else if (taskData.title.length < 3) {
      newErrors.title = 'Title must be at least 3 characters';
    }
    
    if (!taskData.description.trim()) {
      newErrors.description = 'Description is required';
    } else if (taskData.description.length < 10) {
      newErrors.description = 'Description must be at least 10 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    // Build complete task object with all metadata
    const fullTaskData = {
      ...taskData,
      task_id: `task-${Date.now()}`,
      submitted_at: new Date().toISOString(),
      context: {
        ...(taskData.context || {}),
        tags: taskData.tags,
        attachments: taskData.attachments.map(a => ({
          name: a.name || 'unnamed',
          type: a.type || 'text/plain'
        }))
      }
    };

    onSubmit(fullTaskData);
  };

  const handleChange = (field) => (e) => {
    setTaskData(prev => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleSelectChange = (field) => (e) => {
    const value = typeof e.target.value === 'string' ? e.target.value : e.target.value.join(',');
    setTaskData(prev => ({ ...prev, [field]: e.target.value }));
  };

  const handleCheckboxChange = (value) => {
    setTaskData(prev => ({
      ...prev,
      tags: prev.tags.includes(value)
        ? prev.tags.filter(t => t !== value)
        : [...prev.tags, value]
    }));
  };

  const toggleAccordion = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Available agent roles for assignment
  const availableAgentRoles = [
    { id: 'IT Lead', name: 'IT Lead', capabilities: ['assign_task', 'route_to_specialist', 'llm_planning'] },
    { id: 'Implementation Engineer', name: 'Implementation Engineer', capabilities: ['implement_feature', 'generate_code', 'refactor_code'] },
    { id: 'Requirements Engineer', name: 'Requirements Engineer', capabilities: ['analyze_requirements', 'validate_requirements', 'resolve_ambiguity'] },
    { id: 'Code Reviewer', name: 'Code Reviewer', capabilities: ['review_code', 'check_style_compliance'] },
    { id: 'QA Test Engineer', name: 'QA Test Engineer', capabilities: ['generate_test_suite', 'run_tests', 'quality_assurance'] },
    { id: 'Security Engineer', name: 'Security Engineer', capabilities: ['perform_security_analysis', 'vulnerability_scan'] },
    { id: 'DevOps Engineer', name: 'DevOps Engineer', capabilities: ['orchestrate_deployments', 'configure_infrastructure'] }
  ];

  // Priority options
  const priorityOptions = [
    { value: 'low', label: 'Low', color: 'default' },
    { value: 'medium', label: 'Medium', color: 'info' },
    { value: 'high', label: 'High', color: 'warning' },
    { value: 'critical', label: 'Critical', color: 'error' }
  ];

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AddIcon color="primary" />
          <Typography variant="h6">Create New Task</Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        {/* Basic Information */}
        <Accordion 
          expanded={expandedSections.basic} 
          onChange={() => toggleAccordion('basic')}
          sx={{ mb: 2 }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SmartToyIcon fontSize="small" color="primary" />
              <Typography>Basic Information</Typography>
            </Box>
          </AccordionSummary>
          
          <AccordionDetails>
            <TextField
              fullWidth
              margin="dense"
              name="title"
              label="Task Title *"
              type="text"
              variant="outlined"
              value={taskData.title}
              onChange={handleChange('title')}
              error={!!errors.title}
              helperText={errors.title}
              placeholder="e.g., Implement user authentication feature"
            />

            <TextField
              fullWidth
              margin="dense"
              name="description"
              label="Description *"
              type="text"
              variant="outlined"
              multiline
              rows={4}
              value={taskData.description}
              onChange={handleChange('description')}
              error={!!errors.description}
              helperText={errors.description}
              placeholder="e.g., Implement JWT-based authentication with refresh tokens..."
            />

            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
              <FormControl fullWidth>
                <InputLabel>Priority</InputLabel>
                <Select
                  name="priority"
                  value={taskData.priority}
                  label="Priority"
                  onChange={handleSelectChange('priority')}
                >
                  {priorityOptions.map(opt => (
                    <MenuItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                fullWidth
                margin="dense"
                name="dueDate"
                label="Due Date (Optional)"
                type="date"
                variant="outlined"
                value={taskData.dueDate}
                onChange={handleChange('dueDate')}
                InputLabelProps={{ shrink: true }}
              />
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* Routing Configuration */}
        <Accordion 
          expanded={expandedSections.routing} 
          onChange={() => toggleAccordion('routing')}
          sx={{ mb: 2 }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <RouteIcon fontSize="small" color="warning" />
              <Typography>Routing & Assignment</Typography>
            </Box>
          </AccordionSummary>
          
          <AccordionDetails>
            <FormControl fullWidth margin="dense">
              <InputLabel>Assign To (Initial)</InputLabel>
              <Select
                name="assignee"
                value={taskData.assignee}
                label="Assign To (Initial)"
                onChange={handleSelectChange('assignee')}
              >
                {availableAgentRoles.map(agent => (
                  <MenuItem key={agent.id} value={agent.id}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SmartToyIcon fontSize="small" />
                      <span>{agent.name}</span>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
              <FormHelperText>
                IT Lead will intelligently route this task to the appropriate agent based on content analysis
              </FormHelperText>
            </FormControl>

            {/* Tags for categorization */}
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>Tags (Optional)</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                {['bug', 'feature', 'refactor', 'documentation', 'security', 'performance'].map(tag => (
                  <Checkbox
                    key={tag}
                    checked={taskData.tags.includes(tag)}
                    onChange={() => handleCheckboxChange(tag)}
                    label={tag.charAt(0).toUpperCase() + tag.slice(1)}
                    size="small"
                  />
                ))}
              </Box>
            </Box>

            {/* Dependencies */}
            <TextField
              fullWidth
              margin="dense"
              name="dependencies"
              label="Dependencies (Optional)"
              type="text"
              variant="outlined"
              multiline
              rows={2}
              value={taskData.dependencies.join(', ')}
              onChange={(e) => setTaskData(prev => ({
                ...prev,
                dependencies: e.target.value.split(',').map(d => d.trim()).filter(Boolean)
              }))}
              placeholder="e.g., task-123, feature-auth"
            />
          </AccordionDetails>
        </Accordion>

        {/* Additional Context */}
        <Accordion 
          expanded={expandedSections.metadata} 
          onChange={() => toggleAccordion('metadata')}
          sx={{ mb: 2 }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <DocumentIcon fontSize="small" color="action" />
              <Typography>Additional Context & Metadata</Typography>
            </Box>
          </AccordionSummary>
          
          <AccordionDetails>
            {/* Code Diff / Attachments */}
            <TextField
              fullWidth
              margin="dense"
              name="codeDiff"
              label="Code Diff / Technical Details (Optional)"
              type="text"
              variant="outlined"
              multiline
              rows={3}
              value={taskData.context?.code_diff || ''}
              onChange={(e) => setTaskData(prev => ({
                ...prev,
                context: { ...prev.context, code_diff: e.target.value }
              }))}
              placeholder="Paste code diff or technical specifications here..."
            />

            {/* Programming Language */}
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                margin="dense"
                name="language"
                label="Programming Language (Optional)"
                type="text"
                variant="outlined"
                value={taskData.context?.programming_language || ''}
                onChange={(e) => setTaskData(prev => ({
                  ...prev,
                  context: { ...prev.context, programming_language: e.target.value }
                }))}
              />
              
              <TextField
                fullWidth
                margin="dense"
                name="framework"
                label="Framework / Library (Optional)"
                type="text"
                variant="outlined"
                value={taskData.context?.framework || ''}
                onChange={(e) => setTaskData(prev => ({
                  ...prev,
                  context: { ...prev.context, framework: e.target.value }
                }))}
              />
            </Box>

            {/* Acceptance Criteria */}
            <TextField
              fullWidth
              margin="dense"
              name="acceptanceCriteria"
              label="Acceptance Criteria (Optional)"
              type="text"
              variant="outlined"
              multiline
              rows={3}
              value={taskData.context?.acceptance_criteria || ''}
              onChange={(e) => setTaskData(prev => ({
                ...prev,
                context: { ...prev.context, acceptance_criteria: e.target.value }
              }))}
              placeholder="Each criterion on a new line..."
            />

            {/* Business Context */}
            <TextField
              fullWidth
              margin="dense"
              name="businessContext"
              label="Business Context (Optional)"
              type="text"
              variant="outlined"
              multiline
              rows={2}
              value={taskData.context?.business_context || ''}
              onChange={(e) => setTaskData(prev => ({
                ...prev,
                context: { ...prev.context, business_context: e.target.value }
              }))}
            />
          </AccordionDetails>
        </Accordion>

        {/* Agent Status Summary */}
        <Box sx={{ mt: 3 }}>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="subtitle2" color="textSecondary">
            Available Agents ({availableAgents.length})
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
            {availableAgentRoles.map(agent => (
              <Card 
                key={agent.id} 
                variant="outlined" 
                sx={{ 
                  minWidth: 150,
                  opacity: taskData.assignee === agent.id ? 1 : 0.7
                }}
              >
                <CardContent>
                  <Typography variant="body2" fontWeight="bold">{agent.name}</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                    <SmartToyIcon fontSize="small" />
                    <Typography variant="caption">
                      {agent.capabilities.length} capabilities
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 3 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button 
          onClick={handleSubmit}
          variant="contained"
          startIcon={<AddIcon />}
          disabled={!taskData.title || !taskData.description}
        >
          Submit Task
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddTaskForm;
