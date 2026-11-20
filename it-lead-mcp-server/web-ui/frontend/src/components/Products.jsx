import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Button, Card, CardContent, Checkbox, Chip, Container,
  Dialog, DialogActions, DialogContent, DialogTitle,
  FormControlLabel, Grid, TextField, Typography, Alert
} from '@mui/material';
import { Add as AddIcon, Public as PublishIcon } from '@mui/icons-material';
import axios from 'axios';
import PageHeader from './PageHeader';

// Products: mirrors on the artifact host; GitHub publication only on explicit
// human action (type "publish" to confirm).
const Products = () => {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [importOpen, setImportOpen] = useState(false);
  const [imp, setImp] = useState({ name: '', description: '', seed_task_id: '', source_url: '' });
  const [pub, setPub] = useState(null); // product being published
  const [pubRepo, setPubRepo] = useState('');
  const [pubPrivate, setPubPrivate] = useState(true);
  const [pubWord, setPubWord] = useState('');
  const [busy, setBusy] = useState(false);

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
      if (r.data && r.data.success === false) alert('Ошибка: ' + r.data.error);
      setImportOpen(false);
      setImp({ name: '', description: '', seed_task_id: '', source_url: '' });
      refresh();
    } catch (e) { alert('Ошибка: ' + (e.response?.data?.detail || e.message)); }
    setBusy(false);
  };

  const openPublish = (p) => { setPub(p); setPubRepo(p.name); setPubWord(''); };

  const doPublish = async () => {
    setBusy(true);
    try {
      const r = await axios.post(`/api/products/${pub.id}/publish`,
        { github_repo: pubRepo, private: pubPrivate, confirm: pubWord });
      if (r.data && r.data.success === false) alert('Не опубликовано: ' + r.data.error);
      else if (r.data && r.data.github_url) window.open(r.data.github_url, '_blank');
      setPub(null);
      refresh();
    } catch (e) { alert('Ошибка: ' + (e.response?.data?.detail || e.message)); }
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
                  <Chip size="small" label={p.status}
                    color={p.status === 'published' ? 'success' : 'default'} />
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
                {p.result && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    {p.result}
                  </Typography>
                )}
                <Box sx={{ mt: 1.5 }}>
                  {p.status !== 'published' && (
                    <Button size="small" variant="contained" startIcon={<PublishIcon />}
                      onClick={() => openPublish(p)}>
                      Опубликовать…
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
          <TextField fullWidth size="small" margin="normal" label="Имя репо на GitHub"
            value={pubRepo} onChange={e => setPubRepo(e.target.value)} />
          <FormControlLabel control={
            <Checkbox checked={pubPrivate} onChange={e => setPubPrivate(e.target.checked)} />
          } label="приватный репозиторий" />
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
    </Container>
  );
};

export default Products;
