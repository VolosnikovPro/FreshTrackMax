import React, { useEffect, useState } from 'react';
import { batchesApi, productsApi } from '../api';
import { Batch, Product } from '../types';
import { Card, FAB, FilterTabs, Modal, Input, Select, Loading, ErrorMsg, ExpiryBadge, T } from '../components/common/UI';
import { Pencil, Trash2, Search } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { format, parseISO } from 'date-fns';

const emptyForm = { product_id: '', batch_number: '', quantity: '', unit: 'кг', expiry_date: '', received_date: '', notes: '' };
const UNITS = ['кг','л','шт','г','мл','уп','кор'].map(u => ({ value: u, label: u }));
type Filter = 'all' | 'urgent' | 'planned';

export default function BatchesPage() {
  const { hasRole, user } = useAuth();
  const role = user?.role;
  const canWrite = hasRole('admin', 'storekeeper');  // Admin and Storekeeper can add
  const canEdit = hasRole('admin');  // Only admin can edit existing batches
  const canDelete = hasRole('admin', 'manager');  // Admin and Manager can delete
  const isViewOnly = role === 'nutrition_manager';  // UOP - view only

  const [batches, setBatches] = useState<Batch[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Batch | null>(null);
  const [form, setForm] = useState(emptyForm);

  const load = () => {
    setLoading(true);
    Promise.all([
      batchesApi.list(filter).then(r => setBatches(r.data)),
      productsApi.list(true).then(r => setProducts(r.data)),
    ]).catch(() => setError('Ошибка загрузки')).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter]);

  const visible = batches.filter(b =>
    search === '' ||
    b.product_name.toLowerCase().includes(search.toLowerCase()) ||
    (b.batch_number || '').toLowerCase().includes(search.toLowerCase())
  );

  const openCreate = () => {
    setEditing(null);
    setForm({ ...emptyForm, unit: 'кг' });
    setShowForm(true);
  };
  const openEdit = (b: Batch) => {
    if (!canEdit) return;
    setEditing(b);
    setForm({
      product_id: b.product_id.toString(),
      batch_number: b.batch_number || '',
      quantity: b.quantity.toString(),
      unit: b.unit,
      expiry_date: b.expiry_date.split('T')[0],
      received_date: b.received_date?.split('T')[0] || '',
      notes: b.notes || '',
    });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.product_id || !form.expiry_date || !form.quantity) { setError('Заполните обязательные поля'); return; }
    try {
      const payload = {
        product_id: Number(form.product_id),
        batch_number: form.batch_number || null,
        quantity: Number(form.quantity),
        unit: form.unit,
        expiry_date: form.expiry_date,
        received_date: form.received_date || null,
        notes: form.notes || null,
      };
      if (editing) await batchesApi.update(editing.id, payload);
      else await batchesApi.create(payload);
      setShowForm(false); load();
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
  };

  const handleDelete = async (id: number) => {
    if (!canDelete) return;
    if (!window.confirm('Удалить партию? Это действие необратимо.')) return;
    try {
      await batchesApi.delete(id);
      load();
    } catch { setError('Ошибка удаления'); }
  };

  if (!hasRole('admin', 'manager', 'storekeeper', 'nutrition_manager')) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: T.sub }}>
        <div style={{ fontSize: 32, marginBottom: 8 }}>🔒</div>
        <div style={{ fontWeight: 600 }}>Нет доступа к этому разделу</div>
        <div style={{ fontSize: 13, marginTop: 4 }}>Ваша роль: {role}</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <h1 style={{ margin: '0 0 10px', fontSize: 20, fontWeight: 800, color: T.text }}>Партии / Сроки годности</h1>
        <FilterTabs
          options={[
            { value: 'all', label: 'Все' },
            { value: 'urgent', label: 'Срочно (≤15 дн)' },
            { value: 'planned', label: 'Планово (≤45 дн)' },
          ]}
          value={filter} onChange={setFilter as any}
        />
      </div>

      {/* Search */}
      <div style={{ marginBottom: 12, position: 'relative' }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="🔍 Поиск по продукту или номеру партии..."
          style={{
            width: '100%', padding: '11px 14px 11px 40px', borderRadius: 10,
            border: `1.5px solid ${T.border}`, fontSize: 14, fontFamily: 'inherit',
            background: '#fff', boxSizing: 'border-box', outline: 'none',
          }}
        />
      </div>

      {error && <ErrorMsg message={error} />}

      {loading ? <Loading /> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {visible.length === 0 ? (
            <Card style={{ padding: 24, textAlign: 'center', color: T.sub }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
              <div style={{ fontWeight: 600 }}>Нет партий</div>
            </Card>
          ) : visible.map(b => (
            <Card key={b.id} style={{ padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {b.product_name}
                  </div>
                  <div style={{ fontSize: 12, color: T.sub, marginTop: 3, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <span>{b.quantity} {b.unit}</span>
                    {b.batch_number && <span>УПД: {b.batch_number}</span>}
                    <ExpiryBadge days={b.days_until_expiry} />
                    {isViewOnly && <span style={{ fontSize: 11, background: T.blueLight, color: T.blue, padding: '2px 6px', borderRadius: 4, fontWeight: 600 }}>Просмотр</span>}
                  </div>
                </div>
                {(canEdit || canDelete) && (
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    {canEdit && (
                      <button onClick={() => openEdit(b)} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                        <Pencil size={14} color={T.sub} />
                      </button>
                    )}
                    {canDelete && (
                      <button onClick={() => handleDelete(b.id)} style={{ background: T.redLight, border: `1px solid #FECACA`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                        <Trash2 size={14} color={T.red} />
                      </button>
                    )}
                  </div>
                )}
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
            <Select
              label="Продукт *"
              value={form.product_id}
              onChange={e => setForm({ ...form, product_id: e.target.value })}
              options={products.map(p => ({ value: p.id.toString(), label: p.name }))}
              placeholder="Выберите продукт"
            />
            <Input label="Номер УПД" value={form.batch_number} onChange={e => setForm({ ...form, batch_number: e.target.value })} placeholder="УПД-001" />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <Input label="Количество *" type="number" min="0.01" step="0.01" value={form.quantity} onChange={e => setForm({ ...form, quantity: e.target.value })} />
              <Select label="Ед." value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} options={UNITS} />
            </div>
            <Input label="Срок годности *" type="date" value={form.expiry_date} onChange={e => setForm({ ...form, expiry_date: e.target.value })} />
            <Input label="Дата поступления" type="date" value={form.received_date} onChange={e => setForm({ ...form, received_date: e.target.value })} />
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