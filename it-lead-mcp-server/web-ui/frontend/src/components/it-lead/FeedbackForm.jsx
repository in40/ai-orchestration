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
  Grid
} from '@mui/material';
import axios from 'axios';

const FeedbackForm = () => {
  const [formData, setFormData] = useState({
    feedback_target: 'code',
    feedback_type: 'constructive',
    feedback_content: '',
    target_reference: '',
    suggested_improvement: '',
    priority: 'medium'
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const response = await axios.post('/api/feedback/provide', formData);
      alert(`Feedback provided successfully! ID: ${response.data.feedback_id}`);
      
      // Reset form
      setFormData({
        feedback_target: 'code',
        feedback_type: 'constructive',
        feedback_content: '',
        target_reference: '',
        suggested_improvement: '',
        priority: 'medium'
      });
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert('Failed to submit feedback');
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Provide Feedback
        </Typography>
        
        <form onSubmit={handleSubmit}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth margin="normal">
                <InputLabel>Feedback Target</InputLabel>
                <Select
                  name="feedback_target"
                  value={formData.feedback_target}
                  label="Feedback Target"
                  onChange={handleInputChange}
                >
                  <MenuItem value="code">Code</MenuItem>
                  <MenuItem value="documentation">Documentation</MenuItem>
                  <MenuItem value="architecture">Architecture</MenuItem>
                  <MenuItem value="test">Test</MenuItem>
                  <MenuItem value="process">Process</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth margin="normal">
                <InputLabel>Feedback Type</InputLabel>
                <Select
                  name="feedback_type"
                  value={formData.feedback_type}
                  label="Feedback Type"
                  onChange={handleInputChange}
                >
                  <MenuItem value="positive">Positive</MenuItem>
                  <MenuItem value="constructive">Constructive</MenuItem>
                  <MenuItem value="critical">Critical</MenuItem>
                  <MenuItem value="suggestion">Suggestion</MenuItem>
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
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                name="target_reference"
                label="Target Reference (optional)"
                fullWidth
                margin="normal"
                value={formData.target_reference}
                onChange={handleInputChange}
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                name="feedback_content"
                label="Feedback Content"
                fullWidth
                multiline
                rows={4}
                margin="normal"
                value={formData.feedback_content}
                onChange={handleInputChange}
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                name="suggested_improvement"
                label="Suggested Improvement (optional)"
                fullWidth
                multiline
                rows={3}
                margin="normal"
                value={formData.suggested_improvement}
                onChange={handleInputChange}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Button type="submit" variant="contained" color="primary" fullWidth>
                Submit Feedback
              </Button>
            </Grid>
          </Grid>
        </form>
      </CardContent>
    </Card>
  );
};

export default FeedbackForm;