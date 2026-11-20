import React, { useState } from 'react';
import { Button, Grid } from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import ApprovalRequestForm from './ApprovalRequestForm';
import RequirementSubmissionForm from './RequirementSubmissionForm';
import FeedbackForm from './FeedbackForm';
import ProjectDashboard from './ProjectDashboard';
import PageHeader from '../PageHeader';

const ItLeadDashboard = () => {
  // bumping the key remounts ProjectDashboard -> refetches its data
  const [dashKey, setDashKey] = useState(0);

  return (
    <>
      <PageHeader title="IT Lead">
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => setDashKey((k) => k + 1)}
        >
          Refresh
        </Button>
      </PageHeader>
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
          <ProjectDashboard key={dashKey} />
        </Grid>
      </Grid>
    </>
  );
};

export default ItLeadDashboard;
