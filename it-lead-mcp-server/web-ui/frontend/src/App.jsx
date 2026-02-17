import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Dashboard from './components/Dashboard';
import TeamMembers from './components/TeamMembers';
import TaskManagement from './components/TaskManagement';
import AgentDetail from './components/AgentDetail';
import ItLeadDashboard from './components/it-lead/ItLeadDashboard';
import Navigation from './components/Navigation';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#e57373',
    },
    background: {
      default: '#f5f5f5',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Navigation>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/team" element={<TeamMembers />} />
          <Route path="/tasks" element={<TaskManagement />} />
          <Route path="/it-lead" element={<ItLeadDashboard />} />
          <Route path="/agent/:agentName" element={<AgentDetail />} />
        </Routes>
      </Navigation>
    </ThemeProvider>
  );
}

export default App;