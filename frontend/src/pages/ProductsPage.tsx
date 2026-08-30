import React, { useEffect, useState } from 'react';
import { productsApi } from '../api';
import { Product } from '../types';
import { Card, FAB, FilterTabs, Modal, Input, Select, Loading, ErrorMsg, Badge, T } from '../components/common/UI';
import { Pencil } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useSite } from '../hooks/useSite';

const UNITS = ['кг','л','шт','г','мл','уп','кор','пач'].map(u => ({ value: u, label: u }));
type Filter = 'active' | 'all';

export default function ProductsPage() {
  const { hasRole, user } = useAuth();
  const { currentSiteId } = useSite();
  const role = user?.role;
  const canWrite = hasRole('superadmin', 'admin', 'storekeeper');
  const canView = hasRole('superadmin', 'admin', 'storekeeper', 'nutrition_manager');
  const canEdit = false;

  const [products, setProducts] = useState<Product[]>([]);
  const [filter, setFilter] = useState<Filter>('active');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState({ name: '', sku: '', unit: 'кг', category: '', description: '' });

  const load = () => {
    setLoading(true);
    productsApi.list(filter === 'active', currentSiteId)
      .then(r => setProducts(r.data))
      .catch(() => setError('Ошибка загрузки'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter, currentSiteId]);

  const visible = products.filter(p =>
    search === '' || p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.sku || '').toLowerCase().includes(search.toLowerCase())
  );

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', sku: '', unit: 'кг', category: '', description: '' });
    setShowForm(true);
  };
  const openEdit = (p: Product) => {
    if (!canEdit) return;
    setEditing(p);
    setForm({ name: p.name, sku: p.sku || '', unit: p.unit, category: p.category || '', description: p.description || '' });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.name) { setError('Введите название'); return; }
    try {
      const payload = { ...form, site_id: currentSiteId, sku: form.sku || null, category: form.category || null, description: form.description || null };
      if (editing) await productsApi.update(editing.id, payload);
      else await productsApi.create(payload);
      setShowForm(false); load();
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
  };

  const toggleActive = async (p: Product) => {
    if (!canEdit) return;
    await productsApi.update(p.id, { is_active: !p.is_active });
    load();
  };

  if (!canView) {
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
        <h1 style={{ margin: '0 0 10px', fontSize: 20, fontWeight: 800, color: T.text }}>Продукты</h1>
        <FilterTabs
          options={[{ value: 'active', label: 'Активные' }, { value: 'all', label: 'Все' }]}
          value={filter} onChange={setFilter as any}
        />
      </div>

      {/* Search */}
      <div style={{ marginBottom: 12 }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="🔍 Поиск по названию или SKU..."
          style={{
            width: '100%', padding: '11px 14px', borderRadius: 10,
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
              <div style={{ fontSize: 32, marginBottom: 8 }}>🔍</div>
              <div style={{ fontWeight: 600 }}>Ничего не найдено</div>
            </Card>
          ) : visible.map(p => (
            <Card key={p.id} style={{ padding: '14px 16px', opacity: p.is_active ? 1 : 0.6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {p.name}
                  </div>
                  <div style={{ fontSize: 12, color: T.sub, marginTop: 3, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <span>Ед: {p.unit}</span>
                    {p.sku && <span>SKU: {p.sku}</span>}
                    {p.category && <span>📂 {p.category}</span>}
                    {role === 'nutrition_manager' && <Badge color="blue">Просмотр</Badge>}
                  </div>
                </div>
                {canEdit && (
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    <button onClick={() => openEdit(p)} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                      <Pencil size={14} color={T.sub} />
                    </button>
                    <button onClick={() => toggleActive(p)} style={{
                      background: p.is_active ? T.redLight : T.greenLight,
                      border: `1px solid ${p.is_active ? '#FECACA' : '#BBF7D0'}`,
                      borderRadius: 7, padding: '7px 10px', cursor: 'pointer',
                      fontSize: 12, fontWeight: 600, color: p.is_active ? T.red : T.green,
                      fontFamily: 'inherit',
                    }}>
                      {p.is_active ? 'Откл' : 'Вкл'}
                    </button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {canWrite && <FAB onClick={openCreate} />}

      {showForm && (
        <Modal title={editing ? 'Редактировать продукт' : 'Новый продукт'} onClose={() => setShowForm(false)}>
          {error && <ErrorMsg message={error} />}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Input label="Название *" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Мука пшеничная" />
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
              <Input label="Артикул (SKU)" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} placeholder="SKU-001" />
              <Select label="Ед." value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} options={UNITS} />
            </div>
            <Input label="Категория" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} placeholder="Зерновые" />
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
