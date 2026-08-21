import React, { useEffect, useState } from 'react';
import { consumptionApi, productsApi } from '../api';
import { DailyConsumption, Product } from '../types';
import { Card, FAB, Modal, Input, Select, Loading, ErrorMsg, T } from '../components/common/UI';
import { Pencil, Trash2 } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { format, parseISO } from 'date-fns';

const UNITS = ['кг','л','шт','г','мл','уп'].map(u => ({ value: u, label: u }));

export default function ConsumptionPage() {
  const { hasRole, user } = useAuth();
  const role = user?.role;
  const isManager = role === 'manager';  // УПП - only date + total amount
  const isStorekeeper = role === 'storekeeper';
  const isAdmin = role === 'admin';
  const isNutritionManager = role === 'nutrition_manager';

  const canWrite = isAdmin || isStorekeeper || isNutritionManager;  // Admin, Storekeeper, Nutrition Manager can add
  const canWriteDetailed = isAdmin || isStorekeeper || isNutritionManager;  // Detailed entries
  const canDelete = isAdmin || isManager;  // Admin and Manager can delete

  const [entries, setEntries] = useState<DailyConsumption[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<DailyConsumption | null>(null);
  const [form, setForm] = useState({
    product_id: '',
    quantity_used: '',
    unit: 'кг',
    date: format(new Date(), 'yyyy-MM-dd'),
    notes: '',
  });

  const load = () => {
    setLoading(true);
    Promise.all([
      consumptionApi.list().then(r => setEntries(r.data)),
      productsApi.list(true).then(r => setProducts(r.data)),
    ]).catch(() => setError('Ошибка загрузки')).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ product_id: '', quantity_used: '', unit: 'кг', date: format(new Date(), 'yyyy-MM-dd'), notes: '' });
    setShowForm(true);
  };
  const openEdit = (e: DailyConsumption) => {
    if (!canWriteDetailed) return;
    setEditing(e);
    setForm({
      product_id: e.product_id.toString(),
      quantity_used: e.quantity_used.toString(),
      unit: e.unit,
      date: e.date,
      notes: e.notes || '',
    });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.product_id || !form.quantity_used) { setError('Заполните обязательные поля'); return; }
    try {
      const payload = {
        product_id: Number(form.product_id),
        quantity_used: Number(form.quantity_used),
        unit: form.unit,
        date: form.date,
        notes: form.notes || null,
      };
      if (editing) await consumptionApi.update(editing.id, payload);
      else await consumptionApi.create(payload);
      setShowForm(false); load();
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
  };

  const handleDelete = async (id: number) => {
    if (!canDelete) return;
    if (!window.confirm('Удалить запись о расходе?')) return;
    try {
      await consumptionApi.delete(id);
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

  // For UPP (manager): show only date and total amount per day
  if (isManager) {
    // Group entries by date and sum amounts
    const byDate = entries.reduce((acc, e) => {
      const key = e.date;
      if (!acc[key]) acc[key] = { date: key, total: 0, items: [] };
      acc[key].total += e.quantity_used;
      acc[key].items.push(e);
      return acc;
    }, {} as Record<string, { date: string; total: number; items: DailyConsumption[] }>);

    const dates = Object.values(byDate).sort((a, b) => b.date.localeCompare(a.date));

    return (
      <div>
        <div style={{ marginBottom: 12 }}>
          <h1 style={{ margin: '0 0 4px', fontSize: 20, fontWeight: 800, color: T.text }}>Расход сырья</h1>
          <div style={{ fontSize: 12, color: T.sub }}>Режим УПП: только дата и сумма</div>
        </div>

        {error && <ErrorMsg message={error} />}

        {loading ? <Loading /> : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {dates.length === 0 ? (
              <Card style={{ padding: 24, textAlign: 'center', color: T.sub }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
                <div style={{ fontWeight: 600 }}>Нет записей о расходе</div>
              </Card>
            ) : dates.map(d => (
              <Card key={d.date} style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontWeight: 700, fontSize: 15, color: T.text }}>
                    {format(parseISO(d.date), 'dd.MM.yyyy')}
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 15, color: T.blue }}>
                    {d.total.toFixed(2)} кг
                  </div>
                </div>
                <div style={{ marginTop: 6, fontSize: 12, color: T.sub }}>
                  {d.items.length} {d.items.length === 1 ? 'позиция' : d.items.length < 5 ? 'позиции' : 'позиций'}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <h1 style={{ margin: '0 0 4px', fontSize: 20, fontWeight: 800, color: T.text }}>Расход сырья</h1>
      </div>

      {error && <ErrorMsg message={error} />}

      {loading ? <Loading /> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {entries.length === 0 ? (
            <Card style={{ padding: 24, textAlign: 'center', color: T.sub }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
              <div style={{ fontWeight: 600 }}>Нет записей о расходе</div>
            </Card>
          ) : entries.map(e => (
            <Card key={e.id} style={{ padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {e.product_name}
                  </div>
                  <div style={{ fontSize: 12, color: T.sub, marginTop: 3, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <span>{e.quantity_used} {e.unit}</span>
                    <span>{format(parseISO(e.date), 'dd.MM.yyyy')}</span>
                  </div>
                </div>
                {(canWriteDetailed || canDelete) && (
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    {canWriteDetailed && (
                      <button onClick={() => openEdit(e)} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                        <Pencil size={14} color={T.sub} />
                      </button>
                    )}
                    {canDelete && (
                      <button onClick={() => handleDelete(e.id)} style={{ background: T.redLight, border: `1px solid #FECACA`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
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

      {showForm && canWriteDetailed && (
        <Modal title={editing ? 'Редактировать расход' : 'Новый расход'} onClose={() => setShowForm(false)}>
          {error && <ErrorMsg message={error} />}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Select
              label="Продукт *"
              value={form.product_id}
              onChange={(e: any) => setForm({ ...form, product_id: e.target.value })}
              options={products.map(p => ({ value: p.id.toString(), label: p.name }))}
            />
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