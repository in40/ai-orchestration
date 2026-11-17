import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  const seenIds = useRef(new Set());
  const primed = useRef(false);

  // short two-tone chirp via WebAudio (no audio assets needed)
  const beep = () => {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      const ctx = new Ctx();
      if (ctx.state === 'suspended') return; // needs a prior user gesture
      [880, 1245].forEach((f, i) => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.connect(g); g.connect(ctx.destination);
        o.frequency.value = f; g.gain.value = 0.08;
        o.start(ctx.currentTime + i * 0.18); o.stop(ctx.currentTime + i * 0.18 + 0.15);
      });
    } catch (e) { /* audio unavailable */ }
  };

  const systemNotify = (fresh) => {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;
    const n = new Notification(
      `Пайплайн задаёт вопросы: ${fresh.length}`, {
        body: fresh.map(q => `${q.field}: ${q.question}`).join('\n').slice(0, 300),
        tag: 'clarification',
      });
    n.onclick = () => { window.focus(); window.location.href = '/tasks'; n.close(); };
  };

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

  // system notification for NEW questions while the tab is in the background
  useEffect(() => {
    const fresh = items.filter(i => !seenIds.current.has(i.id));
    items.forEach(i => seenIds.current.add(i.id));
    if (!primed.current) { primed.current = true; return; } // skip load-time backlog
    if (fresh.length && document.hidden) { beep(); systemNotify(fresh); }
  }, [items]);

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
        {'Notification' in window && Notification.permission === 'default' && (
          <MenuItem onClick={() => { Notification.requestPermission(); setAnchor(null); }}
            sx={{ whiteSpace: 'normal', color: 'primary.main' }}>
            🔔 Включить системные уведомления (звук + всплывающее окно)
          </MenuItem>
        )}
        {'Notification' in window && Notification.permission === 'denied' && (
          <MenuItem disabled sx={{ whiteSpace: 'normal', fontSize: 12 }}>
            Системные уведомления заблокированы в настройках браузера
          </MenuItem>
        )}
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