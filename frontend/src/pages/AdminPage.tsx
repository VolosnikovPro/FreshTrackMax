import React, { useEffect, useState } from 'react';
import { adminApi, sheetsApi, sitesApi, notificationsApi } from '../api';
import { User, UserRole, Site, NotificationLog } from '../types';
import { Card, Modal, Input, Select, Loading, ErrorMsg, Badge, T } from '../components/common/UI';
import { Pencil, Upload, Users, FileSpreadsheet, Trash, Building2, Plus, Bell, MessageSquare } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { format, parseISO } from 'date-fns';

const ROLE_OPTIONS = [
  { value: 'admin', label: 'Администратор' },
  { value: 'manager', label: 'Управляющий (УПП)' },
  { value: 'storekeeper', label: 'Кладовщик' },
  { value: 'nutrition_manager', label: 'Управл. по питанию (УОП)' },
];
const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Администратор', manager: 'Управляющий (УПП)',
  storekeeper: 'Кладовщик', nutrition_manager: 'Управл. по питанию (УОП)',
};
const ROLE_COLORS: Record<UserRole, 'blue' | 'green' | 'yellow' | 'gray'> = {
  admin: 'blue', manager: 'green', storekeeper: 'yellow', nutrition_manager: 'gray',
};
const IMPORT_TYPES = [
  { value: 'risk_report', label: 'Риск-Отчет (партии + сроки)' },
  { value: 'cost_sheet', label: 'Себестоимость расхода сырья' },
];

type Tab = 'users' | 'sites' | 'import' | 'notifications';

export default function AdminPage() {
  const { hasRole } = useAuth();
  const isAdmin = hasRole('admin');
  const [tab, setTab] = useState<Tab>('users');

  const [users, setUsers] = useState<User[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [notifications, setNotifications] = useState<NotificationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // User form
  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [userForm, setUserForm] = useState({ username: '', display_name: '', role: 'storekeeper' as UserRole, password: '', max_user_id: undefined as undefined | number, site_id: undefined as undefined | number });

  // Site form
  const [showSiteForm, setShowSiteForm] = useState(false);
  const [editingSite, setEditingSite] = useState<Site | null>(null);
  const [siteForm, setSiteForm] = useState({ name: '', code: '', description: '', is_active: true });

  // Import state
  const [importType, setImportType] = useState('risk_report');
  const [importSource, setImportSource] = useState<'file' | 'sheets'>('file');
  const [importFile, setImportFile] = useState<File | null>(null);
  const [sheetsUrl, setSheetsUrl] = useState('');
  const [sheetName, setSheetName] = useState('');
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);

  // Notifications state
  const [loadingNotifications, setLoadingNotifications] = useState(false);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      adminApi.listUsers().then(r => setUsers(r.data)).catch(() => {}),
      sitesApi.list().then(r => setSites(r.data)).catch(() => {}),
    ]).catch(() => setError('Ошибка загрузки')).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const loadNotifications = async () => {
    setLoadingNotifications(true);
    try {
      const res = await notificationsApi.logs({ limit: 100 });
      setNotifications(res.data);
    } catch (e) {
      console.error('Failed to load notifications', e);
    } finally {
      setLoadingNotifications(false);
    }
  };

  const openCreateUser = () => {
    setEditingUser(null);
    setUserForm({ username: '', display_name: '', role: 'storekeeper', password: '', max_user_id: undefined, site_id: sites[0]?.id });
    setShowUserForm(true);
  };
  const openEditUser = (u: User) => {
    setEditingUser(u);
    setUserForm({ username: u.username, display_name: u.display_name, role: u.role, password: '', max_user_id: u.max_user_id, site_id: u.site_id });
    setShowUserForm(true);
  };

  const handleSaveUser = async () => {
    if (!userForm.username) { setError('Логин обязателен'); return; }
    try {
      if (editingUser) {
        await adminApi.updateUser(editingUser.id, userForm);
      } else {
        await adminApi.createUser(userForm);
      }
      setShowUserForm(false);
      loadData();
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка'); }
  };

  const toggleActive = async (u: User) => {
    await adminApi.updateUser(u.id, { is_active: !u.is_active }); loadData();
  };

  const openCreateSite = () => {
    setEditingSite(null);
    setSiteForm({ name: '', code: '', description: '', is_active: true });
    setShowSiteForm(true);
  };
  const openEditSite = (s: Site) => {
    setEditingSite(s);
    setSiteForm({ name: s.name, code: s.code, description: s.description || '', is_active: s.is_active });
    setShowSiteForm(true);
  };

  const handleSaveSite = async () => {
    if (!siteForm.name || !siteForm.code) { setError('Название и код обязательны'); return; }
    try {
      if (editingSite) {
        await sitesApi.update(editingSite.id, siteForm);
      } else {
        await sitesApi.create(siteForm);
      }
      setShowSiteForm(false);
      loadData();
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка'); }
  };

  const handleDeleteSite = async (id: number) => {
    if (!window.confirm('Деактивировать объект? Он станет недоступен пользователям.')) return;
    try {
      await sitesApi.delete(id);
      loadData();
    } catch { setError('Ошибка удаления'); }
  };

  const handleImport = async () => {
    setError(''); setImportResult(null); setImporting(true);
    try {
      let res;
      if (importSource === 'file') {
        if (!importFile) { setError('Выберите файл'); setImporting(false); return; }
        res = await sheetsApi.importFile(importFile, importType);
      } else {
        if (!sheetsUrl) { setError('Введите ссылку на таблицу'); setImporting(false); return; }
        res = await sheetsApi.importSheets({ url_or_id: sheetsUrl, import_type: importType, sheet_name: sheetName });
      }
      setImportResult(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.response?.data?.errors?.[0] || 'Ошибка импорта');
    } finally { setImporting(false); }
  };

  if (loading) return <Loading />;

  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 20, fontWeight: 800, color: T.text }}>Администрирование</h1>
      {error && <ErrorMsg message={error} />}

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
        {([
          ['users', <Users size={15} />, 'Пользователи'],
          ['sites', <Building2 size={15} />, 'Объекты'],
          ['import', <FileSpreadsheet size={15} />, 'Импорт данных'],
          ['notifications', <Bell size={15} />, 'Уведомления'],
        ] as const).map(([t, icon, label]) => (
          <button key={t} onClick={() => setTab(t as Tab)} style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            padding: '11px', borderRadius: 10, cursor: 'pointer',
            fontSize: 13, fontWeight: 700, fontFamily: 'inherit',
            background: tab === t ? T.blue : '#fff',
            color: tab === t ? '#fff' : T.sub,
            boxShadow: tab === t ? '0 2px 8px rgba(37,99,235,0.3)' : 'none',
            border: tab === t ? 'none' : `1px solid ${T.border}`,
          }}>
            {icon}{label}
          </button>
        ))}
      </div>

      {/* ── Users tab ── */}
      {tab === 'users' && (
        <>
          {isAdmin && (
            <button onClick={openCreateUser} style={{
              width: '100%', marginBottom: 12, padding: '12px', borderRadius: 10,
              background: T.blue, color: '#fff', border: 'none', fontSize: 14,
              fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}>
              <Plus size={14} /> Новый пользователь
            </button>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {users.map(u => (
              <Card key={u.id} style={{ padding: '14px 16px', opacity: u.is_active ? 1 : 0.6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: T.text }}>{u.display_name || u.username}</div>
                    <div style={{ fontSize: 12, color: T.sub, marginTop: 2 }}>@{u.username}</div>
                    <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      <Badge color={ROLE_COLORS[u.role]}>{ROLE_LABELS[u.role]}</Badge>
                      {sites.find(s => s.id === u.site_id) && (
                        <Badge color="blue">{sites.find(s => s.id === u.site_id)?.name}</Badge>
                      )}
                      {!u.is_active && <Badge color="gray">Отключён</Badge>}
                    </div>
                  </div>
                  {isAdmin && (
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button onClick={() => adminApi.deleteUser(u.id).then(() => setUsers(users.filter(x => x.id !== u.id)))} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                        <Trash size={14} color={T.sub} />
                      </button>
                      <button onClick={() => openEditUser(u)} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                        <Pencil size={14} color={T.sub} />
                      </button>
                      <button onClick={() => toggleActive(u)} style={{
                        background: u.is_active ? T.redLight : T.greenLight,
                        border: `1px solid ${u.is_active ? '#FECACA' : '#BBF7D0'}`,
                        borderRadius: 7, padding: '7px 10px', cursor: 'pointer',
                        fontSize: 12, fontWeight: 600, color: u.is_active ? T.red : T.green, fontFamily: 'inherit',
                      }}>
                        {u.is_active ? 'Откл' : 'Вкл'}
                      </button>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* ── Sites tab ── */}
      {tab === 'sites' && (
        <>
          {isAdmin && (
            <button onClick={openCreateSite} style={{
              width: '100%', marginBottom: 12, padding: '12px', borderRadius: 10,
              background: T.blue, color: '#fff', border: 'none', fontSize: 14,
              fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}>
              <Plus size={14} /> Новый объект
            </button>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sites.map(s => (
              <Card key={s.id} style={{ padding: '14px 16px', opacity: s.is_active ? 1 : 0.6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: T.text }}>{s.name}</div>
                    <div style={{ fontSize: 12, color: T.sub, marginTop: 2 }}>Код: {s.code}</div>
                    {s.description && <div style={{ fontSize: 12, color: T.muted, marginTop: 2 }}>{s.description}</div>}
                    <div style={{ marginTop: 6, display: 'flex', gap: 6 }}>
                      {s.is_active ? <Badge color="green">Активен</Badge> : <Badge color="gray">Неактивен</Badge>}
                    </div>
                  </div>
                  {isAdmin && (
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button onClick={() => handleDeleteSite(s.id)} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                        <Trash size={14} color={T.sub} />
                      </button>
                      <button onClick={() => openEditSite(s)} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, padding: '7px 10px', cursor: 'pointer' }}>
                        <Pencil size={14} color={T.sub} />
                      </button>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* ── Import tab ── */}
      {tab === 'import' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Import type */}
          <Card style={{ padding: '16px' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 10 }}>Тип данных</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {IMPORT_TYPES.map(t => (
                <label key={t.value} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', padding: '10px 12px', borderRadius: 8, border: `1.5px solid ${importType === t.value ? T.blue : T.border}`, background: importType === t.value ? T.blueLight : '#fff' }}>
                  <input type="radio" name="importType" value={t.value} checked={importType === t.value} onChange={() => setImportType(t.value)} style={{ accentColor: T.blue }} />
                  <span style={{ fontSize: 14, fontWeight: importType === t.value ? 600 : 400, color: importType === t.value ? T.blue : T.text }}>{t.label}</span>
                </label>
              ))}
            </div>
          </Card>

          {/* Source */}
          <Card style={{ padding: '16px' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 10 }}>Источник</div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
              {[['file', '📁 Файл xlsx'], ['sheets', '🔗 Google Sheets']].map(([s, label]) => (
                <button key={s} onClick={() => { setImportSource(s as any); setImportResult(null); }} style={{
                  flex: 1, padding: '10px', borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
                  fontSize: 13, fontWeight: 600,
                  background: importSource === s ? T.blue : '#fff',
                  color: importSource === s ? '#fff' : T.sub,
                  border: importSource === s ? 'none' : `1px solid ${T.border}`,
                }}>{label}</button>
              ))}
            </div>

            {importSource === 'file' ? (
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 6 }}>Выберите .xlsx файл</div>
                <label style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                  border: `2px dashed ${importFile ? T.blue : T.border}`, borderRadius: 10,
                  padding: '24px 16px', cursor: 'pointer', background: importFile ? T.blueLight : T.bg,
                  gap: 8,
                }}>
                  <Upload size={24} color={importFile ? T.blue : T.muted} />
                  <span style={{ fontSize: 14, fontWeight: 600, color: importFile ? T.blue : T.sub }}>
                    {importFile ? importFile.name : 'Нажмите для выбора файла'}
                  </span>
                  {importFile && <span style={{ fontSize: 12, color: T.muted }}>{(importFile.size / 1024).toFixed(0)} КБ</span>}
                  <input type="file" accept=".xlsx,.xlsm" onChange={e => { setImportFile(e.target.files?.[0] || null); setImportResult(null); }} style={{ display: 'none' }} />
                </label>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <Input
                  label="Ссылка на Google Sheets или ID таблицы"
                  value={sheetsUrl}
                  onChange={e => { setSheetsUrl(e.target.value); setImportResult(null); }}
                  placeholder="https://docs.google.com/spreadsheets/d/..."
                />
                <Input
                  label="Название листа (необязательно)"
                  value={sheetName}
                  onChange={e => setSheetName(e.target.value)}
                  placeholder="Лист1 (по умолчанию — первый лист)"
                />
                <div style={{ fontSize: 12, color: T.muted, background: T.bg, borderRadius: 8, padding: '10px 12px' }}>
                  💡 Таблица должна быть открыта: «Все, у кого есть ссылка — просмотр»
                </div>
              </div>
            )}
          </Card>

          {/* Result */}
          {importResult && (
            <Card style={{ padding: '16px', background: importResult.errors?.length > 0 ? T.yellowLight : T.greenLight, border: `1px solid ${importResult.errors?.length > 0 ? '#FDE68A' : '#BBF7D0'}` }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: importResult.errors?.length > 0 ? T.yellow : T.green, marginBottom: 8 }}>
                {importResult.errors?.length > 0 ? '⚠️ Импорт с ошибками' : '✅ Импорт завершён'}
              </div>
              <div style={{ display: 'flex', gap: 20, fontSize: 14, marginBottom: importResult.errors?.length ? 10 : 0 }}>
                <div><span style={{ fontWeight: 800 }}>{importResult.imported}</span> <span style={{ color: T.sub }}>добавлено</span></div>
                <div><span style={{ fontWeight: 800 }}>{importResult.updated}</span> <span style={{ color: T.sub }}>обновлено</span></div>
                <div><span style={{ fontWeight: 800 }}>{importResult.skipped}</span> <span style={{ color: T.sub }}>пропущено</span></div>
              </div>
              {importResult.errors?.map((e: string, i: number) => (
                <div key={i} style={{ fontSize: 12, color: T.red, borderTop: `1px solid ${T.border}`, paddingTop: 4, marginTop: 4 }}>⚠ {e}</div>
              ))}
            </Card>
          )}

          {/* Import button */}
          <button onClick={handleImport} disabled={importing} style={{
            width: '100%', padding: '15px', borderRadius: 12, border: 'none',
            background: importing ? T.muted : T.blue, color: '#fff',
            fontSize: 16, fontWeight: 700, cursor: importing ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit',
          }}>
            {importing ? '⏳ Идёт импорт...' : '📤 Импортировать'}
          </button>

          {/* Format hints */}
          <Card style={{ padding: '14px 16px', background: T.bg }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: T.muted, marginBottom: 8 }}>Поддерживаемые форматы</div>
            <div style={{ fontSize: 12, color: T.sub, lineHeight: 1.7 }}>
              <div>• <b>Риск-Отчет</b> — колонки: Наименование товаров, Ед. Изм., Количество, Срок годности</div>
              <div>• <b>Себестоимость</b> — строка 5 с заголовком Код / Товар / Ед. изм. / Цена, данные с 7-й строки</div>
            </div>
          </Card>
        </div>
      )}

      {/* ── Notifications tab ── */}
      {tab === 'notifications' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: T.text }}>История отправленных уведомлений</div>
              <button onClick={loadNotifications} disabled={loadingNotifications} style={{
                padding: '8px 14px', borderRadius: 8, border: `1px solid ${T.border}`,
                background: '#fff', color: T.sub, fontSize: 12, fontWeight: 600,
                cursor: loadingNotifications ? 'not-allowed' : 'pointer', fontFamily: 'inherit',
              }}>
                {loadingNotifications ? '⏳ Обновление...' : '🔄 Обновить'}
              </button>
            </div>

            {loadingNotifications ? (
              <div style={{ textAlign: 'center', padding: '24px', color: T.sub }}>Загрузка...</div>
            ) : notifications.length === 0 ? (
              <Card style={{ padding: 24, textAlign: 'center' }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>🔔</div>
                <div style={{ fontWeight: 600, color: T.sub }}>Нет записей об уведомлениях</div>
              </Card>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {notifications.map(n => (
                  <Card key={n.id} style={{ padding: '14px 16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, flexWrap: 'wrap' }}>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                          <Badge color={n.notification_type === 'urgent' ? 'red' : 'yellow'}>
                            {n.notification_type === 'urgent' ? '⚠️ Срочное' : '📋 Плановое'}
                          </Badge>
                          <span style={{ fontSize: 12, color: T.sub }}>
                            {format(parseISO(n.created_at), 'dd.MM.yyyy HH:mm')}
                          </span>
                        </div>
                        <div style={{ fontSize: 12, color: T.sub, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                          <span>📦 Продуктов: {n.products_count}</span>
                          <span>👥 Получателей: {n.recipients_count}</span>
                          <span>✅ Отправлено: {n.sent_count}</span>
                        </div>
                        {n.message_text && (
                          <details style={{ marginTop: 8, cursor: 'pointer' }}>
                            <summary style={{ fontSize: 11, color: T.muted, fontWeight: 500 }}>Показать текст сообщения</summary>
                            <pre style={{ fontSize: 11, color: T.sub, background: T.bg, padding: '8px', borderRadius: 6, marginTop: 4, whiteSpace: 'pre-wrap', overflow: 'auto', maxHeight: 200 }}>{n.message_text}</pre>
                          </details>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* User form modal */}
      {showUserForm && (
        <Modal title={editingUser ? `Редактировать: ${editingUser.username}` : 'Новый пользователь'} onClose={() => setShowUserForm(false)}>
          {error && <ErrorMsg message={error} />}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Input label="Логин *" value={userForm.username} onChange={e => setUserForm({ ...userForm, username: e.target.value })} placeholder="username" autoCapitalize="none" />
            <Input label="Отображаемое имя" value={userForm.display_name} onChange={e => setUserForm({ ...userForm, display_name: e.target.value })} placeholder="Иванов Иван" />
            <Select label="Роль" value={userForm.role} onChange={e => setUserForm({ ...userForm, role: e.target.value as UserRole })} options={ROLE_OPTIONS} />
            <Select label="Объект" value={String(userForm.site_id || '')} onChange={e => setUserForm({ ...userForm, site_id: e.target.value ? +e.target.value : undefined })} options={[{ value: '', label: '— Выберите объект —' }, ...sites.map(s => ({ value: String(s.id), label: `${s.name} (${s.code})` }))]} />
            <Input label="Пароль (для локального входа)" type="password" value={userForm.password} onChange={e => setUserForm({ ...userForm, password: e.target.value })} placeholder="Пусто = только MAX-авторизация" />
            <Input label="MAX User ID" value={userForm.max_user_id} onChange={e => setUserForm({ ...userForm, max_user_id: e.target.value ? +e.target.value : undefined })} placeholder="ID пользователя в MAX" />
            <div style={{ display: 'flex', gap: 10, paddingTop: 4 }}>
              <button onClick={handleSaveUser} style={{ flex: 1, background: T.blue, color: '#fff', border: 'none', borderRadius: 10, padding: 14, fontSize: 15, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>Сохранить</button>
              <button onClick={() => setShowUserForm(false)} style={{ flex: 1, background: T.bg, color: T.sub, border: `1px solid ${T.border}`, borderRadius: 10, padding: 14, fontSize: 15, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>Отмена</button>
            </div>
          </div>
        </Modal>
      )}

      {/* Site form modal */}
      {showSiteForm && (
        <Modal title={editingSite ? `Редактировать: ${editingSite.name}` : 'Новый объект'} onClose={() => setShowSiteForm(false)}>
          {error && <ErrorMsg message={error} />}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Input label="Название *" value={siteForm.name} onChange={e => setSiteForm({ ...siteForm, name: e.target.value })} placeholder="Асача" />
            <Input label="Код *" value={siteForm.code} onChange={e => setSiteForm({ ...siteForm, code: e.target.value })} placeholder="ASACH" />
            <Input label="Описание" value={siteForm.description} onChange={e => setSiteForm({ ...siteForm, description: e.target.value })} placeholder="Описание объекта" />
            <Select label="Статус" value={String(siteForm.is_active)} onChange={e => setSiteForm({ ...siteForm, is_active: e.target.value === 'true' })} options={[{ value: 'true', label: 'Активен' }, { value: 'false', label: 'Неактивен' }]} />
            <div style={{ display: 'flex', gap: 10, paddingTop: 4 }}>
              <button onClick={handleSaveSite} style={{ flex: 1, background: T.blue, color: '#fff', border: 'none', borderRadius: 10, padding: 14, fontSize: 15, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>Сохранить</button>
              <button onClick={() => setShowSiteForm(false)} style={{ flex: 1, background: T.bg, color: T.sub, border: `1px solid ${T.border}`, borderRadius: 10, padding: 14, fontSize: 15, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>Отмена</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}