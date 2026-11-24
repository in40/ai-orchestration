import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Button, Card, CardContent, Checkbox, Chip, Container,
  Dialog, DialogActions, DialogContent, DialogTitle,
  FormControl, FormControlLabel, Grid, InputLabel, MenuItem, Select,
  TextField, Typography, Alert
} from '@mui/material';
import {
  Add as AddIcon, Public as PublishIcon, Sync as SyncIcon,
  Undo as UndoIcon
} from '@mui/icons-material';
import axios from 'axios';
import PageHeader from './PageHeader';

// Products: mirrors on the artifact host; GitHub publication only on explicit
// human action (type "publish" to confirm).
const Products = () => {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [importOpen, setImportOpen] = useState(false);
  const [imp, setImp] = useState({ name: '', description: '', seed_task_id: '', source_url: '', readonly: false });
  const [pub, setPub] = useState(null); // product being published
  const [pubRepo, setPubRepo] = useState('');
  const [pubPrivate, setPubPrivate] = useState(true);
  const [pubWord, setPubWord] = useState('');
  const [pubForce, setPubForce] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sync, setSync] = useState(null);        // product being synced
  const [syncData, setSyncData] = useState(null);
  const [syncMode, setSyncMode] = useState('ff');
  const [syncWord, setSyncWord] = useState('');
  const [syncTag, setSyncTag] = useState('');
  const [syncMsg, setSyncMsg] = useState('');

  const refresh = useCallback(async () => {
    try {
      const r = await axios.get('/api/products');
      setItems(r.data.products || []);
      setError('');
    } catch (e) { setError('Не удалось загрузить продукты: ' + (e.message || '')); }
  }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 30000); return () => clearInterval(t); }, [refresh]);

  const doImport = async () => {
    setBusy(true);
    try {
      const r = await axios.post('/api/products', imp);
      if (!r.data || r.data.success !== true) alert('Ошибка: ' + ((r.data && (r.data.error || r.data.message)) || 'product import failed'));
      else { setImportOpen(false); setImp({ name: '', description: '', seed_task_id: '', source_url: '', readonly: false }); }
      refresh();
    } catch (e) { alert('Ошибка: ' + (e.response?.data?.detail || e.message)); }
    setBusy(false);
  };

  const openPublish = (p) => { setPub(p); setPubRepo(p.name); setPubWord(''); setPubForce(false); };

  const doPublish = async () => {
    setBusy(true);
    try {
      const r = await axios.post(`/api/products/${pub.id}/publish`,
        { github_repo: pubRepo, private: pubPrivate, confirm: pubWord, force: pubForce });
      if (r.data && r.data.success === false) alert('Не опубликовано: ' + r.data.error);
      else if (r.data && r.data.github_url) window.open(r.data.github_url, '_blank');
      setPub(null);
      refresh();
    } catch (e) { alert('Ошибка: ' + (e.response?.data?.detail || e.message)); }
    setBusy(false);
  };

  const loadCheck = async (p) => {
    setSyncMsg('');
    try {
      const r = await axios.get(`/api/products/${p.id}/upstream`);
      setSyncData(r.data);
      const v = r.data.verdict;
      setSyncMode(v === 'diverged' ? 'merge' : 'ff');
    } catch (e) { setSyncData({ success: false, error: e.message }); }
  };
  const openSync = (p) => {
    setSync(p); setSyncData(null); setSyncWord(''); setSyncTag('');
    loadCheck(p);
  };
  const doPull = async () => {
    setBusy(true); setSyncMsg('');
    try {
      const r = await axios.post(`/api/products/${sync.id}/upstream/pull`,
        { mode: syncMode, confirm: syncWord });
      const d = r.data;
      if (d.success) {
        setSyncMsg(`✅ ${d.detail || 'готово'}${d.rollback_tag ? ` (откат: ${d.rollback_tag})` : ''}`);
        loadCheck(sync); refresh();
      } else {
        setSyncMsg(`❌ ${d.error}${d.conflicts?.length ? ': ' + d.conflicts.join(', ') : ''}`);
      }
    } catch (e) { setSyncMsg('❌ ' + (e.response?.data?.detail || e.message)); }
    setBusy(false);
  };
  const doRollback = async () => {
    if (!syncTag) return;
    setBusy(true); setSyncMsg('');
    try {
      const r = await axios.post(`/api/products/${sync.id}/upstream/rollback`,
        { tag: syncTag });
      if (r.data.success) { setSyncMsg(`✅ ${r.data.detail}`); loadCheck(sync); refresh(); }
      else setSyncMsg('❌ ' + r.data.error);
    } catch (e) { setSyncMsg('❌ ' + (e.response?.data?.detail || e.message)); }
    setBusy(false);
  };

  return (
    <Container maxWidth="lg">
      <PageHeader title="Products" >
        <Button variant="outlined" color="inherit" startIcon={<AddIcon />}
          onClick={() => setImportOpen(true)}>
          Импортировать продукт
        </Button>
      </PageHeader>
      {error && <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>}
      {items.length === 0 && (
        <Alert severity="info">Пока нет продуктов. Импортируйте продукт из задачи (seed_task_id)
          или из внешнего git-репозитория.</Alert>
      )}
      <Grid container spacing={2}>
        {items.map(p => (
          <Grid item xs={12} md={6} key={p.id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="h6">{p.name}</Typography>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    {p.upstream_readonly && (
                      <Chip size="small" color="warning" variant="outlined"
                        label="upstream: только чтение" />
                    )}
                    <Chip size="small" label={p.status}
                      color={p.status === 'published' ? 'success' : 'default'} />
                  </Box>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ my: 1 }}>
                  {p.description || '—'}
                </Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace', display: 'block' }}>
                  зеркало: {p.mirror_url}
                </Typography>
                {p.github_url && (
                  <Typography variant="caption" sx={{ fontFamily: 'monospace', display: 'block' }}>
                    <a href={p.github_url} target="_blank" rel="noreferrer">{p.github_url}</a>
                    {' '}({p.visibility})
                  </Typography>
                )}
                {p.upstream_url && (
                  <Typography variant="caption" sx={{ fontFamily: 'monospace', display: 'block' }}>
                    upstream: <a href={p.upstream_url} target="_blank" rel="noreferrer">{p.upstream_url}</a>
                  </Typography>
                )}
                {p.result && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    {p.result}
                  </Typography>
                )}
                <Box sx={{ mt: 1.5, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {p.status !== 'published' ? (
                    <Button size="small" variant="contained" startIcon={<PublishIcon />}
                      onClick={() => openPublish(p)}>
                      Опубликовать…
                    </Button>
                  ) : (
                    <Button size="small" variant="outlined" startIcon={<PublishIcon />}
                      onClick={() => openPublish(p)}>
                      Обновить в GitHub
                    </Button>
                  )}
                  {(p.upstream_url || p.github_url) && (
                    <Button size="small" variant="outlined" startIcon={<SyncIcon />}
                      onClick={() => openSync(p)}>
                      Обновить из upstream
                    </Button>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={importOpen} onClose={() => setImportOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Импортировать продукт</DialogTitle>
        <DialogContent dividers>
          <TextField fullWidth size="small" margin="normal" label="Имя (a-z0-9._-)"
            value={imp.name} onChange={e => setImp(s => ({ ...s, name: e.target.value }))} />
          <TextField fullWidth size="small" margin="normal" label="Описание"
            value={imp.description} onChange={e => setImp(s => ({ ...s, description: e.target.value }))} />
          <TextField fullWidth size="small" margin="normal" label="seed_task_id (из results)"
            value={imp.seed_task_id} onChange={e => setImp(s => ({ ...s, seed_task_id: e.target.value }))} />
          <TextField fullWidth size="small" margin="normal" label="или source_url (git)"
            value={imp.source_url} onChange={e => setImp(s => ({ ...s, source_url: e.target.value }))} />
          <FormControlLabel
            disabled={!imp.source_url.trim()}
            control={
              <Checkbox checked={imp.readonly}
                onChange={e => setImp(s => ({ ...s, readonly: e.target.checked }))} />
            }
            label="read-only upstream (чужой репозиторий — обновления только к нам, наружу не пушим)"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportOpen(false)}>Отмена</Button>
          <Button variant="contained" disabled={busy || !imp.name.trim()} onClick={doImport}>
            Создать зеркало
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!pub} onClose={() => setPub(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Публикация: {pub?.name}</DialogTitle>
        <DialogContent dividers>
          {pub?.github_url ? (
            <Alert severity="info" sx={{ mb: 1 }}>
              Будет обновлён существующий репозиторий: {pub.github_url}
            </Alert>
          ) : (
            <TextField fullWidth size="small" margin="normal" label="Имя репо на GitHub"
              value={pubRepo} onChange={e => setPubRepo(e.target.value)} />
          )}
          <FormControlLabel control={
            <Checkbox checked={pubPrivate} onChange={e => setPubPrivate(e.target.checked)} />
          } label="приватный репозиторий" />
          <FormControlLabel control={
            <Checkbox checked={pubForce} onChange={e => setPubForce(e.target.checked)} />
          } label={<Typography variant="body2">force — перезаписать историю удалённого репо</Typography>} />
          <Alert severity="warning" sx={{ mt: 1 }}>
            Код уйдёт наружу (github.com/in40). Для подтверждения введите слово publish.
          </Alert>
          <TextField fullWidth size="small" margin="normal" label="publish"
            value={pubWord} onChange={e => setPubWord(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPub(null)}>Отмена</Button>
          <Button variant="contained" color="error"
            disabled={busy || pubWord !== 'publish' || !pubRepo.trim()} onClick={doPublish}>
            Опубликовать
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!sync} onClose={() => setSync(null)} maxWidth="md" fullWidth>
        <DialogTitle>Обновить из upstream: {sync?.name}</DialogTitle>
        <DialogContent dividers>
          <Typography variant="caption" sx={{ fontFamily: 'monospace', display: 'block', mb: 1 }}>
            upstream: {syncData?.upstream || '…'} ({syncData?.branch})
            {syncData?.readonly ? ' · только чтение (pull-only)' : ''}
          </Typography>
          {!syncData && <Alert severity="info">Идёт диагностика…</Alert>}
          {syncData && !syncData.success && <Alert severity="error">{syncData.error}</Alert>}
          {syncData && syncData.success && (
            <>
              <Alert sx={{ mb: 1 }} severity={
                syncData.verdict === 'behind' ? 'info' :
                syncData.verdict === 'diverged' ? 'warning' :
                syncData.verdict === 'up_to_date' ? 'success' : 'default'}>
                {syncData.verdict === 'behind' &&
                  `В upstream ${syncData.behind} новых коммитов — подтягиваем без конфликта (fast-forward).`}
                {syncData.verdict === 'ahead_only' &&
                  `Наши коммиты впереди (${syncData.ahead}), в upstream ничего нового — подтягивать нечего.`}
                {syncData.verdict === 'up_to_date' && 'Зеркало и upstream идентичны.'}
                {syncData.verdict === 'diverged' &&
                  `Расхождение: наши ${syncData.ahead}, их ${syncData.behind}. merge/rebase сохранят наши правки (конфликты = откат), overwrite — затрёт.`}
              </Alert>
              {syncData.upstream_commits?.length > 0 && (<>
                <Typography variant="subtitle2">новые в upstream:</Typography>
                <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', maxHeight: 140, overflow: 'auto', bgcolor: 'action.hover' }}>
                  {syncData.upstream_commits.join('\n')}
                </Typography>
              </>)}
              {syncData.our_commits?.length > 0 && (<>
                <Typography variant="subtitle2">наши (только в зеркале):</Typography>
                <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', maxHeight: 100, overflow: 'auto', bgcolor: 'action.hover' }}>
                  {syncData.our_commits.join('\n')}
                </Typography>
              </>)}
              {syncData.diffstat && (<>
                <Typography variant="subtitle2">diffstat (наши → upstream):</Typography>
                <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', maxHeight: 120, overflow: 'auto', bgcolor: 'action.hover' }}>
                  {syncData.diffstat}
                </Typography>
              </>)}
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mt: 1.5, flexWrap: 'wrap' }}>
                <FormControl size="small" sx={{ minWidth: 220 }}>
                  <InputLabel>Режим</InputLabel>
                  <Select value={syncMode} label="Режим"
                    onChange={e => setSyncMode(e.target.value)}>
                    <MenuItem value="ff" disabled={syncData.verdict !== 'behind'}>
                      fast-forward (только подтянуть)
                    </MenuItem>
                    <MenuItem value="merge" disabled={syncData.verdict !== 'diverged'}>
                      merge (наши поверх слияния)
                    </MenuItem>
                    <MenuItem value="rebase" disabled={syncData.verdict !== 'diverged'}>
                      rebase (наши пересадить на upstream)
                    </MenuItem>
                    <MenuItem value="overwrite">overwrite (наши теряются)</MenuItem>
                  </Select>
                </FormControl>
                {syncMode === 'overwrite' && (
                  <TextField size="small" label={`введите имя: ${sync?.name}`}
                    value={syncWord} onChange={e => setSyncWord(e.target.value)} />
                )}
              </Box>
              {syncMsg && <Alert sx={{ mt: 1 }} severity={syncMsg.startsWith('✅') ? 'success' : 'error'}>{syncMsg}</Alert>}
              {syncData.tags?.length > 0 && (
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 2 }}>
                  <FormControl size="small" sx={{ minWidth: 220 }}>
                    <InputLabel>Откатить к тегу</InputLabel>
                    <Select value={syncTag} label="Откатить к тегу"
                      onChange={e => setSyncTag(e.target.value)}>
                      {syncData.tags.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                    </Select>
                  </FormControl>
                  <Button size="small" color="warning" variant="outlined" startIcon={<UndoIcon />}
                    disabled={busy || !syncTag} onClick={doRollback}>
                    Откатить зеркало
                  </Button>
                </Box>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSync(null)}>Закрыть</Button>
          <Button onClick={() => syncData && loadCheck(sync)} disabled={busy}>Перепроверить</Button>
          <Button variant="contained" disabled={busy || !syncData?.success ||
              syncData.behind === 0 ||
              (syncMode === 'overwrite' && syncWord !== sync?.name)}
            onClick={doPull}>
            Применить ({syncMode})
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Products;
