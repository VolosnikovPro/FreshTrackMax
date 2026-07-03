import React, { useEffect, useState } from 'react';
import { consumptionApi, productsApi } from '../api';
import { DailyConsumption, Product } from '../types';
import { Card, FAB, Modal, Input, Select, Loading, ErrorMsg, T } from '../components/common/UI';
import { Pencil } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { format, parseISO } from 'date-fns';

const UNITS = ['кг','л','шт','г','мл','уп'].map(u => ({ value: u, label: u }));

export default function ConsumptionPage() {
  const { hasRole } = useAuth();
  const canWrite = hasRole('admin', 'manager', 'nutrition_manager');
  const [entries, setEntries] = useState<DailyConsumption[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<DailyConsumption | null>(null);
  const today = new Date().toISOString().slice(0, 10);
  const [dateFilter, setDateFilter] = useState(today);
  const [form, setForm] = useState({ product_id: '', date: today, quantity_used: '', unit: 'кг', notes: '' });

  const load = () => {
    setLoading(true);
    Promise.all([
      consumptionApi.list({ date: dateFilter }).then(r => setEntries(r.data)),
      productsApi.list().then(r => setProducts(r.data)),
    ]).catch(() => setError('Ошибка загрузки')).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [dateFilter]);

  const productOptions = [{ value: '', label: '— Выберите продукт —' }, ...products.map(p => ({ value: String(p.id), label: p.name }))];

  const openCreate = () => { setEditing(null); setForm({ product_id: '', date: dateFilter, quantity_used: '', unit: 'кг', notes: '' }); setShowForm(true); };
  const openEdit = (e: DailyConsumption) => {
    setEditing(e);
    setForm({ product_id: String(e.product_id), date: e.date, quantity_used: String(e.quantity_used), unit: e.unit, notes: e.notes || '' });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.product_id || !form.quantity_used) { setError('Заполните обязательные поля'); return; }
    try {
      const payload = { product_id: Number(form.product_id), date: form.date, quantity_used: Number(form.quantity_used), unit: form.unit, notes: form.notes || null };
      if (editing) await consumptionApi.update(editing.id, payload);
      else await consumptionApi.create(payload);
      setShowForm(false); load();
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
  };

  const totalByUnit = entries.reduce((acc, e) => {
    const key = e.unit;
    acc[key] = (acc[key] || 0) + e.quantity_used;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div>
      <h1 style={{ margin: '0 0 12px', fontSize: 20, fontWeight: 800, color: T.text }}>Ежедневный расход</h1>

      {/* Date picker row */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, alignItems: 'center' }}>
        <input type="date" value={dateFilter} onChange={e => setDateFilter(e.target.value)}
          style={{ flex: 1, padding: '10px 12px', borderRadius: 10, border: `1.5px solid ${T.border}`, fontSize: 14, fontFamily: 'inherit', background: '#fff', outline: 'none' }} />
        <button onClick={() => setDateFilter(today)} style={{
          padding: '10px 14px', borderRadius: 10, border: `1px solid ${T.border}`,
          background: '#fff', fontSize: 13, fontWeight: 600, color: T.sub, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap',
        }}>Сегодня</button>
      </div>

      {error && <ErrorMsg message={error} />}

      {/* Summary totals */}
      {entries.length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {Object.entries(totalByUnit).map(([unit, total]) => (
            <div key={unit} style={{ background: T.blueLight, color: T.blue, borderRadius: 8, padding: '6px 12px', fontSize: 13, fontWeight: 700 }}>
              {total.toFixed(2)} {unit}
            </div>
          ))}
        </div>
      )}

      {loading ? <Loading /> : entries.length === 0 ? (
        <Card style={{ padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
          <div style={{ fontWeight: 600, color: T.sub }}>Нет записей за этот день</div>
          {canWrite && <div style={{ fontSize: 13, color: T.muted, marginTop: 4 }}>Нажмите + чтобы внести расход</div>}
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {entries.map(e => (
            <Card key={e.id} style={{ padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.product_name}</div>
                  {e.notes && <div style={{ fontSize: 12, color: T.muted, marginTop: 2 }}>{e.notes}</div>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  <span style={{ fontWeight: 800, fontSize: 16, color: T.green }}>{e.quantity_used} {e.unit}</span>
                  {canWrite && (
                    <button onClick={() => openEdit(e)} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                      <Pencil size={14} color={T.sub} />
                    </button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {canWrite && <FAB onClick={openCreate} />}

      {showForm && (
        <Modal title={editing ? 'Редактировать расход' : 'Внести расход'} onClose={() => setShowForm(false)}>
          {error && <ErrorMsg message={error} />}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Select label="Продукт *" value={form.product_id} onChange={e => setForm({ ...form, product_id: e.target.value })} options={productOptions} />
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
              <Input label="Количество *" type="number" min="0.01" step="0.01" value={form.quantity_used} onChange={e => setForm({ ...form, quantity_used: e.target.value })} />
              <Select label="Ед." value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} options={UNITS} />
            </div>
            <Input label="Дата *" type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} />
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