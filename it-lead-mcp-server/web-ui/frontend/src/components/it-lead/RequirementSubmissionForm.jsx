import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Box,
  Grid,
  Chip,
  OutlinedInput,
  ListItemText,
  Checkbox
} from '@mui/material';
import axios from 'axios';

const RequirementSubmissionForm = () => {
  const [formData, setFormData] = useState({
    requirement_type: 'functional',
    requirement_text: '',
    priority: 'medium',
    acceptance_criteria: [''],
    attachments: [],
    stakeholder_context: ''
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleCriteriaChange = (index, value) => {
    const newCriteria = [...formData.acceptance_criteria];
    newCriteria[index] = value;
    setFormData(prev => ({
      ...prev,
      acceptance_criteria: newCriteria
    }));
  };

  const addCriterion = () => {
    setFormData(prev => ({
      ...prev,
      acceptance_criteria: [...prev.acceptance_criteria, '']
    }));
  };

  const removeCriterion = (index) => {
    if (formData.acceptance_criteria.length > 1) {
      const newCriteria = [...formData.acceptance_criteria];
      newCriteria.splice(index, 1);
      setFormData(prev => ({
        ...prev,
        acceptance_criteria: newCriteria
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const response = await axios.post('/api/requirements/submit', formData);
      alert(`Requirement submitted successfully! ID: ${response.data.requirement_id}`);
      
      // Reset form
      setFormData({
        requirement_type: 'functional',
        requirement_text: '',
        priority: 'medium',
        acceptance_criteria: [''],
        attachments: [],
        stakeholder_context: ''
      });
    } catch (error) {
      console.error('Error submitting requirement:', error);
      alert('Failed to submit requirement');
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Submit Requirement
        </Typography>
        
        <form onSubmit={handleSubmit}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth margin="normal">
                <InputLabel>Requirement Type</InputLabel>
                <Select
                  name="requirement_type"
                  value={formData.requirement_type}
                  label="Requirement Type"
                  onChange={handleInputChange}
                >
                  <MenuItem value="functional">Functional</MenuItem>
                  <MenuItem value="non_functional">Non-Functional</MenuItem>
                  <MenuItem value="security">Security</MenuItem>
                  <MenuItem value="performance">Performance</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth margin="normal">
                <InputLabel>Priority</InputLabel>
                <Select
                  name="priority"
                  value={formData.priority}
                  label="Priority"
                  onChange={handleInputChange}
                >
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="critical">Critical</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                name="requirement_text"
                label="Requirement Text"
                fullWidth
                multiline
                rows={4}
                margin="normal"
                value={formData.requirement_text}
                onChange={handleInputChange}
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                Acceptance Criteria
              </Typography>
              {formData.acceptance_criteria.map((criterion, index) => (
                <Grid container spacing={1} key={index} sx={{ mb: 2 }}>
                  <Grid item xs={10}>
                    <TextField
                      label={`Criterion ${index + 1}`}
                      fullWidth
                      value={criterion}
                      onChange={(e) => handleCriteriaChange(index, e.target.value)}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={2}>
                    <Button 
                      variant="outlined" 
                      color="error" 
                      size="small"
                      onClick={() => removeCriterion(index)}
                      disabled={formData.acceptance_criteria.length <= 1}
                    >
                      Remove
                    </Button>
                  </Grid>
                </Grid>
              ))}
              <Button onClick={addCriterion} variant="outlined" size="small">
                Add Criterion
              </Button>
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                name="stakeholder_context"
                label="Stakeholder Context"
                fullWidth
                multiline
                rows={3}
                margin="normal"
                value={formData.stakeholder_context}
                onChange={handleInputChange}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Button type="submit" variant="contained" color="primary" fullWidth>
                Submit Requirement
              </Button>
            </Grid>
          </Grid>
        </form>
      </CardContent>
    </Card>
  );
};

export default RequirementSubmissionForm;