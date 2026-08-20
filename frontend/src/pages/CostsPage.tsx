import React, { useEffect, useState } from 'react';
import { costsApi, productsApi } from '../api';
import { RawMaterialCost, Product } from '../types';
import { Card, FAB, Modal, Input, Select, Loading, ErrorMsg, T } from '../components/common/UI';
import { Pencil } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { format, parseISO } from 'date-fns';

export default function CostsPage() {
  const { hasRole } = useAuth();
  const canWrite = hasRole('admin', 'manager', 'nutrition_manager');
  const [costs, setCosts] = useState<RawMaterialCost[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<RawMaterialCost | null>(null);
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ product_id: '', cost_per_unit: '', currency: 'RUB', effective_date: today, notes: '' });

  const load = () => Promise.all([
    costsApi.list().then(r => setCosts(r.data)),
    productsApi.list().then(r => setProducts(r.data)),
  ]).catch(() => setError('Ошибка загрузки')).finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const productOptions = [{ value: '', label: '— Выберите продукт —' }, ...products.map(p => ({ value: String(p.id), label: p.name }))];

  const openCreate = () => { setEditing(null); setForm({ product_id: '', cost_per_unit: '', currency: 'RUB', effective_date: today, notes: '' }); setShowForm(true); };
  const openEdit = (c: RawMaterialCost) => {
    setEditing(c);
    setForm({ product_id: String(c.product_id), cost_per_unit: String(c.cost_per_unit), currency: c.currency, effective_date: c.effective_date, notes: c.notes || '' });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.product_id || !form.cost_per_unit) { setError('Заполните обязательные поля'); return; }
    try {
      const payload = { product_id: Number(form.product_id), cost_per_unit: Number(form.cost_per_unit), currency: form.currency, effective_date: form.effective_date, notes: form.notes || null };
      if (editing) await costsApi.update(editing.id, payload);
      else await costsApi.create(payload);
      setShowForm(false); load();
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
  };

  if (loading) return <Loading />;

  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 20, fontWeight: 800, color: T.text }}>Себестоимость сырья</h1>
      {error && <ErrorMsg message={error} />}

      {costs.length === 0 ? (
        <Card style={{ padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>💰</div>
          <div style={{ fontWeight: 600, color: T.sub }}>Нет записей о себестоимости</div>
          {canWrite && <div style={{ fontSize: 13, color: T.muted, marginTop: 4 }}>Нажмите + чтобы добавить</div>}
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {costs.map(c => (
            <Card key={c.id} style={{ padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.product_name}</div>
                  <div style={{ fontSize: 12, color: T.sub, marginTop: 3 }}>
                    📅 {format(parseISO(c.effective_date), 'dd.MM.yyyy')}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  <span style={{ fontWeight: 800, fontSize: 16, color: '#7C3AED' }}>
                    {c.cost_per_unit.toFixed(2)} ₽
                  </span>
                  {canWrite && (
                    <button onClick={() => openEdit(c)} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                      <Pencil size={14} color={T.sub} />
                    </button>
                  )}
                </div>
              </div>
              {c.notes && <div style={{ fontSize: 12, color: T.muted, marginTop: 6, paddingTop: 6, borderTop: `1px solid ${T.border}` }}>{c.notes}</div>}
            </Card>
          ))}
        </div>
      )}

      {canWrite && <FAB onClick={openCreate} />}

      {showForm && (
        <Modal title={editing ? 'Редактировать цену' : 'Новая запись'} onClose={() => setShowForm(false)}>
          {error && <ErrorMsg message={error} />}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Select label="Продукт *" value={form.product_id} onChange={e => setForm({ ...form, product_id: e.target.value })} options={productOptions} />
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
              <Input label="Цена за ед. *" type="number" min="0.01" step="0.01" value={form.cost_per_unit} onChange={e => setForm({ ...form, cost_per_unit: e.target.value })} placeholder="0.00" />
              <Select label="Валюта" value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })} options={[{ value: 'RUB', label: '₽ RUB' }, { value: 'USD', label: '$ USD' }]} />
            </div>
            <Input label="Дата *" type="date" value={form.effective_date} onChange={e => setForm({ ...form, effective_date: e.target.value })} />
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