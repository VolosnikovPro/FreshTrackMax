import React, { useEffect, useState } from 'react';
import { batchesApi, productsApi } from '../api';
import { Batch, Product } from '../types';
import { Card, FAB, FilterTabs, Modal, Input, Select, Loading, ErrorMsg, ExpiryBadge, T } from '../components/common/UI';
import { Pencil, Trash2 } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { format, parseISO } from 'date-fns';

const emptyForm = { product_id: '', batch_number: '', quantity: '', unit: 'кг', expiry_date: '', received_date: '', notes: '' };
const UNITS = ['кг','л','шт','г','мл','уп','кор'].map(u => ({ value: u, label: u }));
type Filter = 'all' | 'urgent' | 'planned';

export default function BatchesPage() {
  const { hasRole } = useAuth();
  const canWrite = hasRole('admin', 'manager', 'storekeeper', 'nutrition_manager');
  const canDelete = hasRole('admin', 'manager');

  const [batches, setBatches] = useState<Batch[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Batch | null>(null);
  const [form, setForm] = useState({ ...emptyForm });

  const load = async () => {
    setLoading(true);
    try {
      const [batRes, prodRes] = await Promise.all([
        filter === 'urgent' ? batchesApi.expiringUrgent() :
        filter === 'planned' ? batchesApi.expiringPlanned() :
        batchesApi.list(),
        productsApi.list(),
      ]);
      setBatches(batRes.data); setProducts(prodRes.data);
    } catch { setError('Ошибка загрузки'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [filter]);

  const productOptions = [{ value: '', label: '— Выберите продукт —' }, ...products.map(p => ({ value: String(p.id), label: p.name }))];

  const openCreate = () => { setEditing(null); setForm({ ...emptyForm }); setShowForm(true); };
  const openEdit = (b: Batch) => {
    setEditing(b);
    setForm({ product_id: String(b.product_id), batch_number: b.batch_number || '', quantity: String(b.quantity), unit: b.unit, expiry_date: b.expiry_date, received_date: b.received_date || '', notes: b.notes || '' });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.product_id || !form.expiry_date || !form.quantity) { setError('Заполните обязательные поля'); return; }
    try {
      const p = { product_id: Number(form.product_id), batch_number: form.batch_number || null, quantity: Number(form.quantity), unit: form.unit, expiry_date: form.expiry_date, received_date: form.received_date || null, notes: form.notes || null };
      if (editing) await batchesApi.update(editing.id, p); else await batchesApi.create(p);
      setShowForm(false); load();
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить партию?')) return;
    await batchesApi.delete(id); load();
  };

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <h1 style={{ margin: '0 0 10px', fontSize: 20, fontWeight: 800, color: T.text }}>Партии / Сроки годности</h1>
        <FilterTabs
          options={[
            { value: 'all', label: `Все (${batches.length})` },
            { value: 'urgent', label: '⚠️ Срочно' },
            { value: 'planned', label: '📋 Планово' },
          ]}
          value={filter} onChange={setFilter as any}
        />
      </div>

      {error && <ErrorMsg message={error} />}

      {loading ? <Loading /> : batches.length === 0 ? (
        <Card style={{ padding: 24, textAlign: 'center', color: T.sub }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
          <div style={{ fontWeight: 600 }}>Партии не найдены</div>
          {canWrite && <div style={{ fontSize: 13, marginTop: 4 }}>Нажмите + чтобы добавить</div>}
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {batches.map(b => (
            <Card key={b.id} style={{ padding: '14px 16px', borderLeft: `3px solid ${b.days_until_expiry < 0 ? T.red : b.days_until_expiry < 16 ? T.red : b.days_until_expiry < 46 ? T.yellow : T.green}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{b.product_name}</div>
                  <div style={{ fontSize: 12, color: T.sub, marginTop: 3, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                    <span>📦 {b.quantity} {b.unit}</span>
                    <span>📅 до {format(parseISO(b.expiry_date), 'dd.MM.yyyy')}</span>
                    {b.batch_number && <span>#{b.batch_number}</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6, flexShrink: 0 }}>
                  <ExpiryBadge days={b.days_until_expiry} />
                  {canWrite && (
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button onClick={() => openEdit(b)} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, padding: '5px 8px', cursor: 'pointer' }}>
                        <Pencil size={13} color={T.sub} />
                      </button>
                      {canDelete && (
                        <button onClick={() => handleDelete(b.id)} style={{ background: T.redLight, border: `1px solid #FECACA`, borderRadius: 6, padding: '5px 8px', cursor: 'pointer' }}>
                          <Trash2 size={13} color={T.red} />
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {canWrite && <FAB onClick={openCreate} />}

      {showForm && (
        <Modal title={editing ? 'Редактировать партию' : 'Новая партия'} onClose={() => setShowForm(false)}>
          {error && <ErrorMsg message={error} />}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Select label="Продукт *" value={form.product_id} onChange={e => setForm({ ...form, product_id: e.target.value })} options={productOptions} />
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
              <Input label="Количество *" type="number" min="0.01" step="0.01" value={form.quantity} onChange={e => setForm({ ...form, quantity: e.target.value })} />
              <Select label="Ед." value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} options={UNITS} />
            </div>
            <Input label="Срок годности *" type="date" value={form.expiry_date} onChange={e => setForm({ ...form, expiry_date: e.target.value })} />
            <Input label="Дата поступления" type="date" value={form.received_date} onChange={e => setForm({ ...form, received_date: e.target.value })} />
            <Input label="Номер партии" value={form.batch_number} onChange={e => setForm({ ...form, batch_number: e.target.value })} placeholder="LOT-001" />
            <Input label="Примечание" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
            <div style={{ display: 'flex', gap: 10, paddingTop: 4 }}>
              <button onClick={handleSave} style={{ flex: 1, background: T.blue, color: '#fff', border: 'none', borderRadius: 10, padding: '14px', fontSize: 15, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>Сохранить</button>
              <button onClick={() => setShowForm(false)} style={{ flex: 1, background: T.bg, color: T.sub, border: `1px solid ${T.border}`, borderRadius: 10, padding: '14px', fontSize: 15, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>Отмена</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}