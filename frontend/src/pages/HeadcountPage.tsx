import React, { useEffect, useState } from 'react';
import { headcountApi } from '../api';
import { DailyHeadcount } from '../types';
import { Card, FAB, Modal, Input, Loading, ErrorMsg, T } from '../components/common/UI';
import { useAuth } from '../hooks/useAuth';
import { format, parseISO } from 'date-fns';

export default function HeadcountPage() {
  const { hasRole } = useAuth();
  const canWrite = hasRole('admin', 'manager');
  const [entries, setEntries] = useState<DailyHeadcount[]>([]);
  const [todayEntry, setTodayEntry] = useState<DailyHeadcount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ date: today, count: '', notes: '' });

  const load = () => {
    setLoading(true);
    Promise.all([
      headcountApi.list().then(r => setEntries(r.data)),
      headcountApi.today().then(r => setTodayEntry(r.data)).catch(() => setTodayEntry(null)),
    ]).catch(() => setError('Ошибка загрузки')).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openForm = () => {
    setForm({ date: today, count: todayEntry ? String(todayEntry.count) : '', notes: todayEntry?.notes || '' });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.count || Number(form.count) < 1) { setError('Введите количество'); return; }
    try {
      await headcountApi.create({ date: form.date, count: Number(form.count), notes: form.notes || null });
      setShowForm(false); load();
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка'); }
  };

  if (loading) return <Loading />;

  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 20, fontWeight: 800, color: T.text }}>Питающиеся</h1>
      {error && <ErrorMsg message={error} />}

      {/* Today hero card */}
      <Card style={{ padding: '20px 20px', marginBottom: 16, background: todayEntry ? T.greenLight : T.bg, border: `1px solid ${todayEntry ? '#BBF7D0' : T.border}` }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: T.sub, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>Сегодня</div>
            {todayEntry ? (
              <div style={{ fontSize: 48, fontWeight: 900, color: T.green, lineHeight: 1 }}>{todayEntry.count}</div>
            ) : (
              <div style={{ fontSize: 28, fontWeight: 700, color: T.muted }}>—</div>
            )}
            <div style={{ fontSize: 13, color: T.sub, marginTop: 4 }}>человек</div>
          </div>
          {canWrite && (
            <button onClick={openForm} style={{
              background: T.blue, color: '#fff', border: 'none', borderRadius: 10,
              padding: '12px 20px', fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
            }}>
              {todayEntry ? 'Обновить' : '+ Внести'}
            </button>
          )}
        </div>
        {todayEntry?.notes && <div style={{ fontSize: 13, color: T.sub, marginTop: 10, paddingTop: 10, borderTop: `1px solid #BBF7D0` }}>{todayEntry.notes}</div>}
      </Card>

      {/* History */}
      {entries.length > 1 && (
        <>
          <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 8 }}>История</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {entries.filter(e => e.date !== today).map(e => (
              <Card key={e.id} style={{ padding: '12px 16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14, color: T.sub }}>{format(parseISO(e.date), 'dd.MM.yyyy')}</span>
                  <span style={{ fontWeight: 800, fontSize: 18, color: T.text }}>{e.count} <span style={{ fontSize: 13, fontWeight: 500, color: T.sub }}>чел.</span></span>
                </div>
                {e.notes && <div style={{ fontSize: 12, color: T.muted, marginTop: 4 }}>{e.notes}</div>}
              </Card>
            ))}
          </div>
        </>
      )}

      {entries.length === 0 && (
        <Card style={{ padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>👥</div>
          <div style={{ fontWeight: 600, color: T.sub }}>Нет записей</div>
        </Card>
      )}

      {canWrite && !todayEntry && <FAB onClick={openForm} />}

      {showForm && (
        <Modal title={todayEntry ? 'Обновить питающихся' : 'Внести питающихся'} onClose={() => setShowForm(false)}>
          {error && <ErrorMsg message={error} />}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Input label="Дата *" type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} />
            <Input label="Количество человек *" type="number" min="1" value={form.count}
              onChange={e => setForm({ ...form, count: e.target.value })} placeholder="Например: 150"
              style={{ fontSize: 24, fontWeight: 700, textAlign: 'center' }} />
            <Input label="Примечание" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
            <div style={{ display: 'flex', gap: 10, paddingTop: 4 }}>
              <button onClick={handleSave} style={{ flex: 1, background: T.blue, color: '#fff', border: 'none', borderRadius: 10, padding: 14, fontSize: 15, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>Сохранить</button>
              <button onClick={() => setShowForm(false)} style={{ flex: 1, background: T.bg, color: T.sub, border: `1px solid ${T.border}`, borderRadius: 10, padding: 14, fontSize: 15, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>Отмена</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}