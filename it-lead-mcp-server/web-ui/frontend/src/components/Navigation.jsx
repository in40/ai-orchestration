import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  AppBar, Toolbar, Typography, Button, Box, Container,
  IconButton, Badge, Menu, MenuItem,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  Checkbox, FormControlLabel, Chip
} from '@mui/material';
import { NotificationsNone as BellIcon } from '@mui/icons-material';
import { Link, useLocation } from 'react-router-dom';
import axios from 'axios';

// Requestor bell: the pipeline pauses with status awaiting_input when the
// planner/QA lack critical details; pending questions come from IT Lead.
const ClarificationBell = () => {
  const [items, setItems] = useState([]);
  const [digest, setDigest] = useState(null);
  const [proposals, setProposals] = useState([]);
  const [selffix, setSelffix] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const seenAlerts = useRef(null);
  const [sfDiff, setSfDiff] = useState({});
  const [fixDialog, setFixDialog] = useState(false);
  const [fixText, setFixText] = useState('');
  const [fixBusy, setFixBusy] = useState(false);
  const seenProposals = useRef(null);
  const seenDigest = useRef(null);
  const seenSelffix = useRef(null);
  const [anchor, setAnchor] = useState(null);
  const [answering, setAnswering] = useState(null);
  const [draft, setDraft] = useState({});
  const [flags, setFlags] = useState({});
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
    try {
      const d = await axios.get('/api/retro/latest');
      setDigest(d.data && d.data.digest ? d.data : null);
    } catch (e) { /* ignore */ }
    try {
      const p = await axios.get('/api/retro/proposals');
      setProposals((p.data.proposals || []).filter(x => x.status === 'proposed'));
    } catch (e) { /* ignore */ }
    try {
      const s = await axios.get('/api/selffix');
      setSelffix((s.data.items || []).filter(x => x.status === 'review'));
    } catch (e) { /* ignore */ }
    try {
      const a = await axios.get('/api/pipeline/alerts');
      setAlerts(a.data.alerts || []);
    } catch (e) { /* ignore */ }
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

  // nightly retro digest: notify once per new report
  useEffect(() => {
    if (!digest || !digest.ts) return;
    if (seenDigest.current === null) { seenDigest.current = digest.ts; return; } // backlog on load
    if (digest.ts !== seenDigest.current) {
      seenDigest.current = digest.ts;
      if (document.hidden) {
        beep();
        if ('Notification' in window && Notification.permission === 'granted') {
          const n = new Notification('Retro: ночной отчёт готов', {
            body: (digest.digest || '').slice(0, 300), tag: 'retro' });
          n.onclick = () => { window.focus(); n.close(); };
        }
      }
    }
  }, [digest]);

  // new improvement proposals -> notify once per set
  useEffect(() => {
    const ids = proposals.map(p => p.id).sort().join(',');
    if (seenProposals.current === null) { seenProposals.current = ids; return; }
    if (ids && ids !== seenProposals.current && document.hidden) {
      seenProposals.current = ids;
      beep();
      if ('Notification' in window && Notification.permission === 'granted') {
        const n = new Notification(`Retro: предложений к рассмотрению: ${proposals.length}`, {
          body: proposals.map(p => `${p.risk} ${p.title}`).join('\n').slice(0, 300),
          tag: 'retro-proposal' });
        n.onclick = () => { window.focus(); n.close(); };
      }
    } else {
      seenProposals.current = ids;
    }
  }, [proposals]);

  // self-fix diffs awaiting review -> notify once per set
  useEffect(() => {
    const ids = selffix.map(p => p.id).sort().join(',');
    if (seenSelffix.current === null) { seenSelffix.current = ids; return; }
    if (ids && ids !== seenSelffix.current && document.hidden) {
      seenSelffix.current = ids;
      beep();
      if ('Notification' in window && Notification.permission === 'granted') {
        const n = new Notification(`Self-fix: диффов ждёт ревью: ${selffix.length}`, {
          body: selffix.map(p => p.diff_stat || p.complaint).join('\n').slice(0, 300),
          tag: 'selffix' });
        n.onclick = () => { window.focus(); n.close(); };
      }
    } else {
      seenSelffix.current = ids;
    }
  }, [selffix]);

  // pipeline incidents -> notify once per new set
  useEffect(() => {
    const keys = alerts.map(a => `${a.task_id}:${a.event}:${a.ts}`).sort().join(',');
    if (seenAlerts.current === null) { seenAlerts.current = keys; return; }
    if (keys && keys !== seenAlerts.current && document.hidden) {
      seenAlerts.current = keys;
      beep();
      if ('Notification' in window && Notification.permission === 'granted') {
        const n = new Notification(`Пайплайн: инциденты: ${alerts.length}`, {
          body: alerts.slice(0, 4).map(a => `${a.event} · ${a.task_id}`).join('\n'),
          tag: 'pipeline-alerts' });
        n.onclick = () => { window.focus(); n.close(); };
      }
    } else {
      seenAlerts.current = keys;
    }
  }, [alerts]);

  const decideSelffix = async (id, action) => {
    try {
      const r = await axios.post(`/api/selffix/${id}/${action}`);
      if (action === 'approve' && r.data && r.data.success === false) {
        alert('Мерж не состоялся: ' + (r.data.error || ''));
      }
      refresh();
    } catch (e) {
      alert('Не удалось: ' + (e.response?.data?.detail || e.message));
    }
  };

  const showSelffixDiff = async (id) => {
    if (sfDiff[id]) { setSfDiff(d => { const n = { ...d }; delete n[id]; return n; }); return; }
    try {
      const r = await axios.get(`/api/selffix/${id}/diff`);
      setSfDiff(d => ({ ...d, [id]: (r.data.diff || '').slice(0, 20000) }));
    } catch (e) { setSfDiff(d => ({ ...d, [id]: 'diff unavailable' })); }
  };

  const fileSelfFix = async () => {
    setFixBusy(true);
    try {
      await axios.post('/api/selffix', { complaint: fixText });
      setFixDialog(false); setFixText(''); refresh();
    } catch (e) {
      alert('Не удалось: ' + (e.response?.data?.detail || e.message));
    }
    setFixBusy(false);
  };

  const decide = async (id, action) => {
    try {
      await axios.post(`/api/retro/proposals/${id}/${action}`);
      refresh();
    } catch (e) {
      alert('Не удалось: ' + (e.response?.data?.detail || e.message));
    }
  };

  const byTask = {};
  items.forEach(i => { (byTask[i.task_id] = byTask[i.task_id] || []).push(i); });
  const groups = Object.entries(byTask);

  const openAnswer = (tid, qs) => {
    setAnchor(null);
    setAnswering({ task_id: tid, questions: qs });
    setDraft(Object.fromEntries(qs.map(q => [q.field, ''])));
    // V3 auto-detect: runtime-looking fields go to container env;
    // key/token-looking fields are additionally masked from prompts (env-only)
    const ENV_RE = /(URL|ENDPOINT|KEY|TOKEN|SECRET|PORT|HOST|MODEL|PASS)/i;
    const SECRET_RE = /(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)/i;
    setFlags(Object.fromEntries(qs.map(q => [
      q.field, { env: ENV_RE.test(q.field), secret: SECRET_RE.test(q.field) }])));
  };

  const submit = async () => {
    setBusy(true);
    try {
      await axios.post(`/api/tasks/${answering.task_id}/clarify`, {
        answers: draft,
        env_fields: Object.entries(flags).filter(([, f]) => f.env).map(([k]) => k),
        secret_fields: Object.entries(flags).filter(([, f]) => f.secret).map(([k]) => k),
      });
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
        <Badge badgeContent={items.length + proposals.length + selffix.length} color="error">
          <BellIcon />
        </Badge>
      </IconButton>
      <Menu anchorEl={anchor} open={!!anchor} onClose={() => setAnchor(null)}
        PaperProps={{ sx: { maxWidth: 460 } }}>
        {digest && (
          <MenuItem disabled sx={{ whiteSpace: 'pre-wrap', py: 1, opacity: '1 !important',
                                  bgcolor: 'grey.100', mb: 0.5 }}>
            <Box>
              <Typography variant="subtitle2" color="primary">
                📋 Retro · {new Date(digest.ts * 1000).toLocaleString('ru-RU')}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontSize: 12.5 }}>
                {digest.digest}
              </Typography>
            </Box>
          </MenuItem>
        )}
        {'Notification' in window && Notification.permission === 'default' && (
          <MenuItem onClick={() => { Notification.requestPermission(); setAnchor(null); }}
            sx={{ whiteSpace: 'normal', color: 'primary.main' }}>
            🔔 Включить системные уведомления (звук + всплывающее окно)
          </MenuItem>
        )}
        {'Notification' in window && Notification.permission === 'denied' && (
          <MenuItem disabled sx={{ whiteSpace: 'normal', fontSize: 12 }}>
            Системные уведомления заблокированы: откройте интерфейс по https://…
            (на http браузер их запрещает всегда) и разрешите их в настройках сайта
          </MenuItem>
        )}
        {alerts.length > 0 && (
          <Box sx={{ px: 2, py: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
            <Typography variant="subtitle2" color="warning.main">
              ⚠️ Инциденты за 48ч: {alerts.length}
            </Typography>
            {alerts.slice(0, 6).map((a, i) => (
              <Typography key={i} variant="caption" sx={{ display: 'block', color: 'text.secondary' }}>
                <b>{a.event}</b> · <span style={{ fontFamily: 'monospace' }}>{a.task_id}</span>
                {a.detail ? ` — ${String(a.detail).slice(0, 90)}` : ''}
              </Typography>
            ))}
          </Box>
        )}
        {groups.length === 0 && proposals.length === 0 && selffix.length === 0 &&
          <MenuItem disabled>Нет активных вопросов</MenuItem>}
        <MenuItem onClick={() => { setAnchor(null); setFixDialog(true); }}
          sx={{ color: 'primary.main', fontSize: 13 }}>
          🔧 Заявить проблему интерфейсу (self-fix)
        </MenuItem>
        {selffix.map(p => (
          <Box key={p.id} sx={{ px: 2, py: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
            <Typography variant="subtitle2">
              <Chip label="self-fix" size="small" color="secondary"
                sx={{ mr: 1, height: 20, fontSize: 11 }} />
              {p.area}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
              {(p.complaint || '').slice(0, 200)}
            </Typography>
            <Typography variant="caption" sx={{ display: 'block', fontFamily: 'monospace' }}>
              {p.diff_stat}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mt: 0.75 }}>
              <Button size="small" onClick={() => showSelffixDiff(p.id)}>
                {sfDiff[p.id] ? 'Скрыть diff' : 'Показать diff'}
              </Button>
              <Button size="small" variant="contained" onClick={() => decideSelffix(p.id, 'approve')}>
                Одобрить
              </Button>
              <Button size="small" onClick={() => decideSelffix(p.id, 'reject')}>Отклонить</Button>
            </Box>
            {sfDiff[p.id] && (
              <Box component="pre" sx={{
                mt: 0.75, p: 1, bgcolor: 'grey.900', color: 'grey.100', fontSize: 11,
                maxHeight: 260, overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {sfDiff[p.id]}
              </Box>
            )}
          </Box>
        ))}
        {proposals.map(p => (
          <Box key={p.id} sx={{ px: 2, py: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
            <Typography variant="subtitle2">
              <Chip label={p.risk} size="small" sx={{ mr: 1, height: 20, fontSize: 11 }}
                color={p.risk === 'R2' ? 'error' : 'warning'} />
              {p.title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
              {p.problem}
            </Typography>
            <Typography variant="caption" sx={{
              display: 'block', bgcolor: 'grey.200', p: 0.75, mt: 0.5,
              whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 11.5 }}>
              {p.patch_text}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mt: 0.75 }}>
              <Button size="small" variant="contained" onClick={() => decide(p.id, 'approve')}>
                Одобрить
              </Button>
              <Button size="small" onClick={() => decide(p.id, 'reject')}>Отклонить</Button>
            </Box>
          </Box>
        ))}
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
              <Box sx={{ display: 'flex', gap: 2 }}>
                <FormControlLabel control={
                  <Checkbox size="small" checked={!!flags[q.field]?.env}
                    onChange={e => setFlags(f => ({ ...f, [q.field]: { ...f[q.field], env: e.target.checked } }))} />
                } label={<Typography variant="caption">в env контейнера (deploy)</Typography>} />
                <FormControlLabel control={
                  <Checkbox size="small" checked={!!flags[q.field]?.secret}
                    onChange={e => setFlags(f => ({ ...f, [q.field]: { ...f[q.field], secret: e.target.checked } }))} />
                } label={<Typography variant="caption">секрет (не светить в коде)</Typography>} />
              </Box>
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
      <Dialog open={fixDialog} onClose={() => setFixDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Заявить проблему интерфейсу</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Команда сделает снимок UI-кода, починит копию, прогонит гейты — diff
            придёт сюда на ревью. В живой репозиторий попадёт только после «Одобрить».
          </Typography>
          <TextField
            fullWidth multiline minRows={4} size="small"
            placeholder="Опишите, что не так: вкладка, что видно, что должно быть…"
            value={fixText} onChange={e => setFixText(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFixDialog(false)}>Cancel</Button>
          <Button variant="contained" disabled={fixBusy || fixText.trim().length < 10}
            onClick={fileSelfFix}>
            Запустить self-fix
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
                to="/products"
                variant={isActive('/products') ? 'outlined' : 'text'}
                color="inherit"
              >
                Products
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