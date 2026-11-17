import React, { useState, useEffect, useCallback } from 'react';
import {
  AppBar, Toolbar, Typography, Button, Box, Container,
  IconButton, Badge, Menu, MenuItem,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField
} from '@mui/material';
import { NotificationsNone as BellIcon } from '@mui/icons-material';
import { Link, useLocation } from 'react-router-dom';
import axios from 'axios';

// Requestor bell: the pipeline pauses with status awaiting_input when the
// planner/QA lack critical details; pending questions come from IT Lead.
const ClarificationBell = () => {
  const [items, setItems] = useState([]);
  const [anchor, setAnchor] = useState(null);
  const [answering, setAnswering] = useState(null);
  const [draft, setDraft] = useState({});
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const r = await axios.get('/api/clarifications/pending');
      setItems(r.data.clarifications || []);
    } catch (e) { /* backend hiccup: keep the last snapshot */ }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 15000);
    return () => clearInterval(t);
  }, [refresh]);

  const byTask = {};
  items.forEach(i => { (byTask[i.task_id] = byTask[i.task_id] || []).push(i); });
  const groups = Object.entries(byTask);

  const openAnswer = (tid, qs) => {
    setAnchor(null);
    setAnswering({ task_id: tid, questions: qs });
    setDraft(Object.fromEntries(qs.map(q => [q.field, ''])));
  };

  const submit = async () => {
    setBusy(true);
    try {
      await axios.post(`/api/tasks/${answering.task_id}/clarify`, { answers: draft });
      setAnswering(null);
      refresh();
    } catch (e) {
      alert('Failed to send answers: ' + (e.response?.data?.detail || e.message));
    }
    setBusy(false);
  };

  return (
    <>
      <IconButton color="inherit" aria-label="clarification requests"
        onClick={(e) => { setAnchor(e.currentTarget); refresh(); }}>
        <Badge badgeContent={items.length} color="error">
          <BellIcon />
        </Badge>
      </IconButton>
      <Menu anchorEl={anchor} open={!!anchor} onClose={() => setAnchor(null)}
        PaperProps={{ sx: { maxWidth: 400 } }}>
        {groups.length === 0 && <MenuItem disabled>No pending questions</MenuItem>}
        {groups.map(([tid, qs]) => (
          <MenuItem key={tid} onClick={() => openAnswer(tid, qs)}
            sx={{ whiteSpace: 'normal', py: 1, display: 'block' }}>
            <Typography variant="subtitle2" sx={{ fontFamily: 'monospace', fontSize: 12 }}>
              {tid}
            </Typography>
            {qs.map(q => (
              <Typography key={q.id} variant="body2" color="text.secondary">
                <b>{q.field}</b>: {q.question}
              </Typography>
            ))}
          </MenuItem>
        ))}
      </Menu>
      <Dialog open={!!answering} onClose={() => setAnswering(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Typography variant="h6" component="span">Answer: </Typography>
          <Typography variant="subtitle2" component="span" sx={{ fontFamily: 'monospace' }}>
            {answering?.task_id}
          </Typography>
        </DialogTitle>
        <DialogContent dividers>
          {answering?.questions.map(q => (
            <Box key={q.id} sx={{ mb: 2 }}>
              <Typography variant="subtitle2">{q.field}</Typography>
              <Typography variant="body2">{q.question}</Typography>
              {!!q.why && (
                <Typography variant="caption" color="text.secondary" display="block">
                  {q.why}
                </Typography>
              )}
              <TextField fullWidth size="small" sx={{ mt: 1 }}
                value={draft[q.field] || ''}
                onChange={e => setDraft(d => ({ ...d, [q.field]: e.target.value }))} />
            </Box>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAnswering(null)}>Cancel</Button>
          <Button variant="contained" disabled={busy ||
            !Object.values(draft).some(v => v.trim())} onClick={submit}>
            Send answers
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

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

            <ClarificationBell />

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
                to="/deployments"
                variant={isActive('/deployments') ? 'outlined' : 'text'}
                color="inherit"
              >
                Deployments
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