import React, { useEffect, useState } from 'react';
import { Upload } from 'lucide-react';
import { sheetsApi } from '../api';
import { Card, ErrorMsg, Loading, Select, T } from '../components/common/UI';
import { useAuth } from '../hooks/useAuth';
import { useSite } from '../hooks/useSite';

const ADMIN_TYPES = [
  { value: 'risk_report', label: 'Риск-отчет' },
  { value: 'cost_sheet', label: 'Legacy: цены и остатки' },
];

export default function ImportPage() {
  const { user } = useAuth();
  const { currentSiteId } = useSite();
  const isStorekeeper = user?.role === 'storekeeper';
  const isAdministrative = user?.role === 'superadmin' || user?.role === 'admin';
  const [type, setType] = useState(isStorekeeper ? 'consumption_file' : 'risk_report');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ imported: number; updated: number; skipped: number } | null>(null);
  const [history, setHistory] = useState<Array<{ id: number; import_type: string; status: string; created_at: string }>>([]);

  const loadHistory = () => {
    if (!isAdministrative) return;
    sheetsApi.history(currentSiteId).then(response => setHistory(response.data)).catch(() => setError('Не удалось загрузить историю импорта'));
  };

  useEffect(() => { loadHistory(); }, [currentSiteId, isAdministrative]);

  const submit = async () => {
    if (!file) { setError('Выберите файл .xlsx или .xlsm'); return; }
    setLoading(true); setError(''); setResult(null);
    try {
      const response = await sheetsApi.importFile(file, type, currentSiteId);
      setResult(response.data);
      loadHistory();
    } catch (requestError: any) {
      setError(requestError.response?.data?.detail?.message || requestError.response?.data?.detail || 'Ошибка импорта');
    } finally { setLoading(false); }
  };

  if (loading) return <Loading />;

  const cancelImport = async (id: number) => {
    const reason = window.prompt('Причина отмены импорта') || '';
    try {
      await sheetsApi.cancel(id, reason);
      loadHistory();
    } catch (requestError: any) {
      setError(requestError.response?.data?.detail?.message || 'Не удалось отменить импорт');
    }
  };

  return <div>
    <h1 style={{ margin: '0 0 16px', fontSize: 20, fontWeight: 800, color: T.text }}>Импорт</h1>
    {error && <ErrorMsg message={typeof error === 'string' ? error : 'Ошибка импорта'} />}
    <Card style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
      {isStorekeeper ? <div style={{ color: T.sub }}>Расход сырья будет списан по FEFO только для вашего объекта.</div> : <Select label="Тип файла" value={type} onChange={event => setType(event.target.value)} options={ADMIN_TYPES} />}
      <label style={{ border: `2px dashed ${file ? T.blue : T.border}`, padding: 22, textAlign: 'center', cursor: 'pointer', borderRadius: 8 }}>
        <Upload size={24} color={file ? T.blue : T.muted} />
        <div style={{ marginTop: 8, color: T.sub }}>{file ? file.name : 'Выбрать XLSX-файл'}</div>
        <input type="file" accept=".xlsx,.xlsm" onChange={event => setFile(event.target.files?.[0] || null)} style={{ display: 'none' }} />
      </label>
      <button onClick={submit} style={{ background: T.blue, color: '#fff', border: 0, borderRadius: 8, padding: 12, fontWeight: 700, cursor: 'pointer' }}>Импортировать</button>
    </Card>
    {result && <Card style={{ marginTop: 16, padding: 16, background: T.greenLight }}>Добавлено: {result.imported}; обновлено: {result.updated}; пропущено: {result.skipped}</Card>}
    {isAdministrative && <Card style={{ marginTop: 16, padding: 16 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>История импорта</div>
      {history.length === 0 ? <div style={{ color: T.sub }}>Нет импортов для выбранного объекта</div> : history.map(item => (
        <div key={item.id} style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', borderTop: `1px solid ${T.border}` }}>
          <span>{item.import_type} #{item.id}: {item.status}</span>
          {item.status === 'success' && <button onClick={() => cancelImport(item.id)} style={{ border: `1px solid ${T.red}`, color: T.red, background: '#fff', borderRadius: 6, padding: '5px 8px', cursor: 'pointer' }}>Отменить</button>}
        </div>
      ))}
    </Card>}
  </div>;
}
