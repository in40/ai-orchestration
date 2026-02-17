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

const ApprovalRequestForm = () => {
  const [formData, setFormData] = useState({
    approval_type: 'code',
    request_title: '',
    request_context: '',
    options: [{label: '', value: ''}],
    urgency: 'medium',
    required_approver_roles: []
  });

  const approverRoles = ['Developer', 'Tech Lead', 'Security Officer', 'Product Manager', 'Executive'];

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleOptionChange = (index, field, value) => {
    const newOptions = [...formData.options];
    newOptions[index][field] = value;
    setFormData(prev => ({
      ...prev,
      options: newOptions
    }));
  };

  const addOption = () => {
    setFormData(prev => ({
      ...prev,
      options: [...prev.options, {label: '', value: ''}]
    }));
  };

  const removeOption = (index) => {
    if (formData.options.length > 1) {
      const newOptions = [...formData.options];
      newOptions.splice(index, 1);
      setFormData(prev => ({
        ...prev,
        options: newOptions
      }));
    }
  };

  const handleRoleToggle = (role) => {
    setFormData(prev => {
      const newRoles = prev.required_approver_roles.includes(role)
        ? prev.required_approver_roles.filter(r => r !== role)
        : [...prev.required_approver_roles, role];
      
      return {
        ...prev,
        required_approver_roles: newRoles
      };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const response = await axios.post('/api/approvals/request', formData);
      alert(`Approval request submitted successfully! ID: ${response.data.request_id}`);
      
      // Reset form
      setFormData({
        approval_type: 'code',
        request_title: '',
        request_context: '',
        options: [{label: '', value: ''}],
        urgency: 'medium',
        required_approver_roles: []
      });
    } catch (error) {
      console.error('Error submitting approval request:', error);
      alert('Failed to submit approval request');
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Request Human Approval
        </Typography>
        
        <form onSubmit={handleSubmit}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth margin="normal">
                <InputLabel>Approval Type</InputLabel>
                <Select
                  name="approval_type"
                  value={formData.approval_type}
                  label="Approval Type"
                  onChange={handleInputChange}
                >
                  <MenuItem value="code">Code</MenuItem>
                  <MenuItem value="architecture">Architecture</MenuItem>
                  <MenuItem value="deployment">Deployment</MenuItem>
                  <MenuItem value="requirement">Requirement</MenuItem>
                  <MenuItem value="security">Security</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth margin="normal">
                <InputLabel>Urgency</InputLabel>
                <Select
                  name="urgency"
                  value={formData.urgency}
                  label="Urgency"
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
                name="request_title"
                label="Request Title"
                fullWidth
                margin="normal"
                value={formData.request_title}
                onChange={handleInputChange}
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                name="request_context"
                label="Request Context"
                fullWidth
                multiline
                rows={4}
                margin="normal"
                value={formData.request_context}
                onChange={handleInputChange}
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                Approval Options
              </Typography>
              {formData.options.map((option, index) => (
                <Grid container spacing={1} key={index} sx={{ mb: 2 }}>
                  <Grid item xs={5}>
                    <TextField
                      label="Option Label"
                      fullWidth
                      value={option.label}
                      onChange={(e) => handleOptionChange(index, 'label', e.target.value)}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={5}>
                    <TextField
                      label="Option Value"
                      fullWidth
                      value={option.value}
                      onChange={(e) => handleOptionChange(index, 'value', e.target.value)}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={2}>
                    <Button 
                      variant="outlined" 
                      color="error" 
                      size="small"
                      onClick={() => removeOption(index)}
                      disabled={formData.options.length <= 1}
                    >
                      Remove
                    </Button>
                  </Grid>
                </Grid>
              ))}
              <Button onClick={addOption} variant="outlined" size="small">
                Add Option
              </Button>
            </Grid>
            
            <Grid item xs={12}>
              <FormControl fullWidth margin="normal">
                <InputLabel>Required Approver Roles</InputLabel>
                <Select
                  multiple
                  value={formData.required_approver_roles}
                  onChange={(e) => setFormData(prev => ({...prev, required_approver_roles: e.target.value}))}
                  input={<OutlinedInput label="Required Approver Roles" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {approverRoles.map((role) => (
                    <MenuItem key={role} value={role}>
                      <Checkbox checked={formData.required_approver_roles.indexOf(role) > -1} />
                      <ListItemText primary={role} />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <Button type="submit" variant="contained" color="primary" fullWidth>
                Submit Approval Request
              </Button>
            </Grid>
          </Grid>
        </form>
      </CardContent>
    </Card>
  );
};

export default ApprovalRequestForm;