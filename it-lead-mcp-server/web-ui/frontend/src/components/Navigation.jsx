import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box, Container } from '@mui/material';
import { Link, useLocation } from 'react-router-dom';

const Navigation = ({ children }) => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <>
      <AppBar position="static">
        <Container maxWidth="xl">
          <Toolbar disableGutters>
            <Typography
              variant="h6"
              noWrap
              component="div"
              sx={{ mr: 2, display: { xs: 'none', md: 'flex' } }}
            >
              MCP Agent Dashboard
            </Typography>

            <Box sx={{ flexGrow: 1, display: { xs: 'flex', md: 'none' } }}>
              <Typography
                variant="h6"
                noWrap
                component="div"
                sx={{ flexGrow: 1 }}
              >
                MCP
              </Typography>
            </Box>

            <Box sx={{ flexGrow: 1 }} />

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                component={Link}
                to="/"
                variant={isActive('/') ? 'outlined' : 'text'}
                color="inherit"
              >
                Dashboard
              </Button>
              <Button
                component={Link}
                to="/team"
                variant={isActive('/team') ? 'outlined' : 'text'}
                color="inherit"
              >
                Team
              </Button>
              <Button
                component={Link}
                to="/tasks"
                variant={isActive('/tasks') ? 'outlined' : 'text'}
                color="inherit"
              >
                Tasks
              </Button>
              <Button
                component={Link}
                to="/it-lead"
                variant={isActive('/it-lead') ? 'outlined' : 'text'}
                color="inherit"
              >
                IT Lead
              </Button>
            </Box>
          </Toolbar>
        </Container>
      </AppBar>
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        {children}
      </Container>
    </>
  );
};

export default Navigation;