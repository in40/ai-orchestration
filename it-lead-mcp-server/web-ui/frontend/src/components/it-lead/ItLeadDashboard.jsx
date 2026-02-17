import React from 'react';
import { Grid } from '@mui/material';
import ApprovalRequestForm from './ApprovalRequestForm';
import RequirementSubmissionForm from './RequirementSubmissionForm';
import FeedbackForm from './FeedbackForm';
import ProjectDashboard from './ProjectDashboard';

const ItLeadDashboard = () => {
  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <ApprovalRequestForm />
      </Grid>
      <Grid item xs={12} md={6}>
        <RequirementSubmissionForm />
      </Grid>
      <Grid item xs={12} md={6}>
        <FeedbackForm />
      </Grid>
      <Grid item xs={12}>
        <ProjectDashboard />
      </Grid>
    </Grid>
  );
};

export default ItLeadDashboard;