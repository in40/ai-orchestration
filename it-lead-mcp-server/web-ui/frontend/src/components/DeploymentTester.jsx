import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Button,
  IconButton,
  TextField,
  MenuItem,
  Select,
  InputLabel,
  FormControl,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  Tooltip
} from '@mui/material';
import { Refresh as RefreshIcon, Send as SendIcon } from '@mui/icons-material';
import axios from 'axios';

// Generic tester for any deployed artifact. Probe picks the mode:
//  mcp     -> tools/list drives the forms, tools/call through backend proxy
//  openapi -> spec operations drive the forms, plain proxied HTTP
//  raw     -> free-form method/path/body (mini-Postman)
// All traffic goes through /api/tester/* (backend whitelist = task_deployments).

const pretty = (v) => {
  if (typeof v !== 'string') return JSON.stringify(v, null, 2);
  try { return JSON.stringify(JSON.parse(v), null, 2); } catch { return v; }
};

const skeleton = (schema) => {
  const out = {};
  Object.entries((schema && schema.properties) || {}).forEach(([k, p]) => {
    if (p.type === 'boolean') out[k] = true;
    else if (p.type === 'number' || p.type === 'integer') out[k] = 0;
    else if (p.type === 'array') out[k] = [];
    else if (p.type === 'object') out[k] = {};
    else out[k] = p.default !== undefined ? p.default : '';
  });
  return out;
};

const ResponseView = ({ resp }) => {
  if (!resp) return null;
  const isError = resp.status >= 400 || resp.isError;
  return (
    <Box sx={{ mt: 2 }}>
      <Box display="flex" gap={1} alignItems="center">
        <Chip size="small" label={`HTTP ${resp.status ?? '—'}`}
              color={isError ? 'error' : 'success'} />
        {resp.elapsed_ms !== undefined && (
          <Typography variant="caption" color="text.secondary">{resp.elapsed_ms} ms</Typography>
        )}
      </Box>
      <Box component="pre" sx={{
        mt: 1, p: 1.5, bgcolor: 'grey.900', color: 'grey.100',
        fontSize: 12, maxHeight: 320, overflow: 'auto', borderRadius: 1,
        whiteSpace: 'pre-wrap', wordBreak: 'break-all'
      }}>
        {resp.text}
      </Box>
    </Box>
  );
};

const DeploymentTester = ({ open, onClose, deployment }) => {
  const tid = deployment?.task_id;
  const [probing, setProbing] = useState(false);
  const [probe, setProbe] = useState(null);
  const [error, setError] = useState(null);
  const [resp, setResp] = useState(null);
  const [busy, setBusy] = useState(false);
  // mcp mode
  const [toolName, setToolName] = useState('');
  const [mcpArgs, setMcpArgs] = useState({});
  // openapi mode
  const [opKey, setOpKey] = useState('');
  const [opParams, setOpParams] = useState({});
  const [opBody, setOpBody] = useState('');
  // raw mode
  const [rawMethod, setRawMethod] = useState('GET');
  const [rawPath, setRawPath] = useState('');
  const [rawBody, setRawBody] = useState('');

  const runProbe = async () => {
    if (!tid) return;
    setProbing(true);
    setError(null);
    setResp(null);
    try {
      const r = await axios.post('/api/tester/probe', { task_id: tid });
      setProbe(r.data);
      const tools = r.data.tools || [];
      setToolName(tools[0]?.name || '');
      if (tools[0]) setMcpArgs(skeleton(tools[0].inputSchema));
      const ops = r.data.mode === 'openapi' ? openapiOps(r.data.openapi) : [];
      setOpKey(ops[0]?.key || '');
      setOpParams({});
      setRawPath('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setProbe(null);
    } finally {
      setProbing(false);
    }
  };

  useEffect(() => { if (open && tid) runProbe(); /* eslint-disable-next-line */ }, [open, tid]);

  const openapiOps = (spec) => Object.entries((spec && spec.paths) || {}).flatMap(([p, ms]) =>
    Object.entries(ms || {})
      .filter(([m]) => ['get', 'post', 'put', 'patch', 'delete'].includes(m))
      .map(([m, def]) => ({
        key: `${m.toUpperCase()} ${p}`,
        method: m.toUpperCase(),
        path: p,
        summary: (def.summary || '').slice(0, 60),
        params: (def.parameters || []).filter(x => x.in !== 'header'),
        hasBody: !!def.requestBody
      })));

  const tool = (probe?.tools || []).find(t => t.name === toolName);

  const callMcp = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await axios.post('/api/tester/mcp', {
        task_id: tid, method: 'tools/call',
        params: { name: toolName, arguments: mcpArgs }
      });
      const res = r.data.result || {};
      const text = (res.content || []).map(c => c.text || '').join('\n');
      setResp({ status: res.isError ? 500 : 200, isError: res.isError, text: pretty(text) || '(empty)' });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const callOpenapi = async () => {
    const op = openapiOps(probe?.openapi).find(o => o.key === opKey);
    if (!op) return;
    let path = op.path.replace(/\{(\w+)\}/g, (_, name) => encodeURIComponent(opParams[name] ?? ''));
    const qs = op.params.filter(p => p.in === 'query' && opParams[p.name] !== undefined && opParams[p.name] !== '')
      .map(p => `${encodeURIComponent(p.name)}=${encodeURIComponent(opParams[p.name])}`).join('&');
    if (qs) path += (path.includes('?') ? '&' : '?') + qs;
    setBusy(true);
    setError(null);
    try {
      const body = op.hasBody && opBody.trim() ? opBody : undefined;
      const r = await axios.post('/api/tester/request',
        { task_id: tid, method: op.method, path, body });
      setResp({ ...r.data, text: pretty(r.data.body) });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const callRaw = async () => {
    setBusy(true);
    setError(null);
    try {
      let body = rawBody;
      try { body = rawBody.trim() ? JSON.parse(rawBody) : undefined; } catch { /* keep as text */ }
      const r = await axios.post('/api/tester/request',
        { task_id: tid, method: rawMethod, path: rawPath, body });
      setResp({ ...r.data, text: pretty(r.data.body) });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const modeChip = {
    mcp: <Chip size="small" color="primary" label="MCP server" />,
    openapi: <Chip size="small" color="secondary" label="OpenAPI" />,
    raw: <Chip size="small" label="raw HTTP" />
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ pb: 1 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h6">Test deployment</Typography>
            <Typography variant="caption" color="text.secondary" fontFamily="monospace">
              {deployment?.deployment_url}
            </Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            {probe && modeChip[probe.mode]}
            <Tooltip title="Re-probe">
              <span><IconButton onClick={runProbe} disabled={probing}><RefreshIcon /></IconButton></span>
            </Tooltip>
          </Box>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        {probing && <Box display="flex" justifyContent="center" p={4}><CircularProgress /></Box>}
        {error && <Alert severity="error" sx={{ mb: 2 }}>{String(error).slice(0, 300)}</Alert>}
        {!probing && probe && probe.mode === 'mcp' && (
          <Box>
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel>Tool</InputLabel>
              <Select value={toolName} label="Tool" onChange={(e) => {
                setToolName(e.target.value);
                const t = (probe.tools || []).find(x => x.name === e.target.value);
                setMcpArgs(skeleton(t && t.inputSchema));
              }}>
                {(probe.tools || []).map(t => (
                  <MenuItem key={t.name} value={t.name}>
                    {t.name}{t.description ? ` — ${t.description.slice(0, 60)}` : ''}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {Object.entries((tool && tool.inputSchema && tool.inputSchema.properties) || {}).map(([k, p]) => (
              <TextField key={k} size="small" fullWidth sx={{ mb: 1 }}
                label={`${k}${((tool.inputSchema.required || []).includes(k)) ? ' *' : ''} (${p.type || 'any'})`}
                value={typeof mcpArgs[k] === 'object' ? JSON.stringify(mcpArgs[k]) : String(mcpArgs[k] ?? '')}
                onChange={(e) => {
                  const v = e.target.value;
                  let parsed = v;
                  if (p.type === 'object' || p.type === 'array') { try { parsed = JSON.parse(v); } catch { return; } }
                  else if (p.type === 'number' || p.type === 'integer') parsed = Number(v) || 0;
                  else if (p.type === 'boolean') parsed = v === 'true';
                  setMcpArgs(prev => ({ ...prev, [k]: parsed }));
                }} />
            ))}
            <Button variant="contained" endIcon={busy ? <CircularProgress size={16} /> : <SendIcon />}
              onClick={callMcp} disabled={busy || !toolName}>
              tools/call
            </Button>
          </Box>
        )}
        {!probing && probe && probe.mode === 'openapi' && (() => {
          const ops = openapiOps(probe.openapi);
          const op = ops.find(o => o.key === opKey) || ops[0];
          return (
            <Box>
              <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                <InputLabel>Operation</InputLabel>
                <Select value={opKey} label="Operation" onChange={(e) => { setOpKey(e.target.value); setOpParams({}); }}>
                  {ops.map(o => <MenuItem key={o.key} value={o.key}>{o.key} {o.summary && `— ${o.summary}`}</MenuItem>)}
                </Select>
              </FormControl>
              {(op?.params || []).map(p => (
                <TextField key={p.name} size="small" fullWidth sx={{ mb: 1 }}
                  label={`${p.name} (${p.in}${p.required ? ', required' : ''})`}
                  value={opParams[p.name] ?? ''}
                  onChange={(e) => setOpParams(prev => ({ ...prev, [p.name]: e.target.value }))} />
              ))}
              {op?.hasBody && (
                <TextField size="small" fullWidth multiline minRows={3} sx={{ mb: 1 }}
                  label="Request body (JSON)" value={opBody}
                  onChange={(e) => setOpBody(e.target.value)} />
              )}
              <Button variant="contained" endIcon={busy ? <CircularProgress size={16} /> : <SendIcon />}
                onClick={callOpenapi} disabled={busy || !op}>
                {op ? op.key : 'Execute'}
              </Button>
            </Box>
          );
        })()}
        {!probing && probe && probe.mode === 'raw' && (
          <Box>
            <Box display="flex" gap={1} sx={{ mb: 1 }}>
              <FormControl size="small" sx={{ minWidth: 110 }}>
                <Select value={rawMethod} onChange={(e) => setRawMethod(e.target.value)}>
                  {['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'].map(m => <MenuItem key={m} value={m}>{m}</MenuItem>)}
                </Select>
              </FormControl>
              <TextField size="small" fullWidth placeholder="path, e.g. health or echo"
                value={rawPath} onChange={(e) => setRawPath(e.target.value)} />
            </Box>
            <TextField size="small" fullWidth multiline minRows={3} sx={{ mb: 1 }}
              label="Body (JSON or text)" value={rawBody}
              onChange={(e) => setRawBody(e.target.value)} />
            <Button variant="contained" endIcon={busy ? <CircularProgress size={16} /> : <SendIcon />}
              onClick={callRaw} disabled={busy}>
              Send
            </Button>
            {probe.root_status && (
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                GET / answered {probe.root_status}
              </Typography>
            )}
          </Box>
        )}
        {!probing && probe && probe.mode !== 'mcp' && (probe.tools || []).length > 0 && <Divider />}
        <ResponseView resp={resp} />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default DeploymentTester;
