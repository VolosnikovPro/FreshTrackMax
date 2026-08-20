import React, { useEffect, useState } from 'react';
import { costsApi, productsApi } from '../api';
import { RawMaterialCost, Product } from '../types';
import { Card, FAB, Modal, Input, Select, Loading, ErrorMsg, T } from '../components/common/UI';
import { Pencil } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { format, parseISO } from 'date-fns';

export default function CostsPage() {
  const { hasRole, user } = useAuth();
  const role = user?.role;
  const isAdmin = role === 'admin';
  const isManager = role === 'manager';
  const isNutritionManager = role === 'nutrition_manager';
  const canWrite = isAdmin || isManager || isNutritionManager;
  const canEdit = isAdmin || isManager;  // Only admin/manager can edit costs

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
    productsApi.list(true).then(r => setProducts(r.data)),
  ]).catch(() => setError('Ошибка загрузки')).finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const productOptions = [{ value: '', label: '— Выберите продукт —' }, ...products.map(p => ({ value: String(p.id), label: p.name }))];

  const openCreate = () => { setEditing(null); setForm({ product_id: '', cost_per_unit: '', currency: 'RUB', effective_date: today, notes: '' }); setShowForm(true); };
  const openEdit = (c: RawMaterialCost) => {
    if (!canEdit) return;
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

  // Group costs by date for table view
  const costsByDate = costs.reduce((acc, c) => {
    const date = c.effective_date.split('T')[0];
    if (!acc[date]) acc[date] = [];
    acc[date].push(c);
    return acc;
  }, {} as Record<string, RawMaterialCost[]>);

  const sortedDates = Object.keys(costsByDate).sort((a, b) => b.localeCompare(a));

  // Calculate average cost per unit across all products for each date
  const dailyAverages = sortedDates.map(date => {
    const items = costsByDate[date];
    const total = items.reduce((sum, c) => sum + c.cost_per_unit, 0);
    return { date, average: total / items.length, count: items.length };
  });

  if (loading) return <Loading />;

  // For nutrition_manager (UOP): view-only table with dates + average row
  if (isNutritionManager) {
    return (
      <div>
        <h1 style={{ margin: '0 0 16px', fontSize: 20, fontWeight: 800, color: T.text }}>Себестоимость сырья</h1>
        <div style={{ fontSize: 12, color: T.sub, marginBottom: 12 }}>Режим просмотра: таблица по датам + средняя</div>
        {error && <ErrorMsg message={error} />}

        {costs.length === 0 ? (
          <Card style={{ padding: 24, textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>💰</div>
            <div style={{ fontWeight: 600, color: T.sub }}>Нет записей о себестоимости</div>
          </Card>
        ) : (
          <div>
            {/* Table view */}
            <Card style={{ padding: 0, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: T.bg, borderBottom: `1px solid ${T.border}` }}>
                    <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: T.text }}>Продукт</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, color: T.text }}>Цена</th>
                    <th style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 600, color: T.text }}>Валюта</th>
                    <th style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 600, color: T.text }}>Дата</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedDates.map(date => (
                    <React.Fragment key={date}>
                      {costsByDate[date].map(c => (
                        <tr key={c.id} style={{ borderBottom: `1px solid ${T.border}` }}>
                          <td style={{ padding: '10px 12px', color: T.text }}>{c.product_name}</td>
                          <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, color: '#7C3AED' }}>
                            {c.cost_per_unit.toFixed(2)}
                          </td>
                          <td style={{ padding: '10px 12px', textAlign: 'center', color: T.sub }}>{c.currency}</td>
                          <td style={{ padding: '10px 12px', textAlign: 'center', color: T.sub }}>
                            {format(parseISO(c.effective_date), 'dd.MM.yyyy')}
                          </td>
                        </tr>
                      ))}
                      {/* Average row for this date */}
                      <tr style={{ background: T.blueLight, borderBottom: `2px solid ${T.blue}` }}>
                        <td style={{ padding: '8px 12px', fontWeight: 600, color: T.blue }}>Средняя по дате</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, color: T.blue }}>
                          {dailyAverages.find(d => d.date === date)?.average.toFixed(2) || '—'}
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'center', color: T.sub }}>RUB</td>
                        <td style={{ padding: '8px 12px', textAlign: 'center', color: T.sub }}>
                          {format(parseISO(date), 'dd.MM.yyyy')}
                        </td>
                      </tr>
                    </React.Fragment>
                  ))}
                  {/* Overall average row */}
                  <tr style={{ background: T.yellowLight, borderTop: `2px solid ${T.yellow}`, fontWeight: 700 }}>
                    <td style={{ padding: '10px 12px', color: T.yellow }}>Средняя общая</td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', color: T.yellow }}>
                      {(costs.reduce((sum, c) => sum + c.cost_per_unit, 0) / costs.length).toFixed(2)}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'center', color: T.sub }}>RUB</td>
                    <td style={{ padding: '10px 12px', textAlign: 'center', color: T.sub }}>—</td>
                  </tr>
                </tbody>
              </table>
            </Card>
          </div>
        )}
      </div>
    );
  }

  // Admin/Manager view - card list with edit capability
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
                  {canEdit && (
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