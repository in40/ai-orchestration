import React from 'react';
import { Box, Typography } from '@mui/material';

// Unified page header for every dashboard tab: title left, actions right.
// Same typography (h4) and spacing (mb 3) across all routes.
const PageHeader = ({ title, children }) => (
  <Box
    sx={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: 2,
      mb: 3,
    }}
  >
    <Typography variant="h4">{title}</Typography>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {children}
    </Box>
  </Box>
);

export default PageHeader;
