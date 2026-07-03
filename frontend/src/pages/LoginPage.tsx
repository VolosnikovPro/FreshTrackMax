import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Input, Button, T } from '../components/common/UI';

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  // const [seeding, setSeeding] = useState(false);
  // const [seedMsg, setSeedMsg] = useState('');

  if (user) { navigate('/'); return null; }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try { await login(username, password); navigate('/'); }
    catch (err: any) { setError(err.response?.data?.detail || 'Неверный логин или пароль'); }
    finally { setLoading(false); }
  };

  // const handleSeedAdmin = async () => {
  //   setSeeding(true);
  //   try { const r = await authApi.seedAdmin(); setSeedMsg(r.data.detail); }
  //   catch { setSeedMsg('Ошибка'); }
  //   finally { setSeeding(false); }
  // };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: 20,
      background: 'linear-gradient(160deg, #0F172A 0%, #1E3A5F 100%)',
      fontFamily: "'Onest', system-ui, sans-serif",
    }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <span style={{
              background: T.blue, borderRadius: 8, padding: '6px 12px',
              fontSize: 14, fontWeight: 800, letterSpacing: '0.06em', color: '#fff',
            }}>FRESH</span>
            <span style={{ fontWeight: 800, fontSize: 24, color: '#fff' }}>Track</span>
          </div>
          <p style={{ color: '#94A3B8', fontSize: 14, margin: 0 }}>
            Контроль сроков годности и расхода сырья
          </p>
        </div>

        <div style={{ background: '#fff', borderRadius: 20, padding: '28px 24px', boxShadow: '0 24px 48px rgba(0,0,0,0.35)' }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {error && (
              <div style={{ background: T.redLight, color: T.red, borderRadius: 8, padding: '11px 14px', fontSize: 14 }}>
                {error}
              </div>
            )}
            <Input label="Логин" value={username} onChange={e => setUsername(e.target.value)}
              placeholder="username" autoCapitalize="none" autoCorrect="off" required />
            <Input label="Пароль" type="password" value={password}
              onChange={e => setPassword(e.target.value)} placeholder="••••••••" required />
            <Button type="submit" disabled={loading} fullWidth size="lg" style={{ marginTop: 4 }}>
              {loading ? 'Входим...' : 'Войти'}
            </Button>
          </form>

          {/* <div style={{ marginTop: 20, paddingTop: 18, borderTop: `1px solid ${T.border}` }}>
            <p style={{ fontSize: 12, color: T.muted, marginBottom: 10 }}>Первый запуск — создайте admin-аккаунт:</p>
            <Button variant="secondary" size="sm" onClick={handleSeedAdmin} disabled={seeding} fullWidth>
              {seeding ? 'Создание...' : 'Создать admin (admin / admin123)'}
            </Button>
            {seedMsg && <p style={{ fontSize: 12, color: T.green, marginTop: 6, textAlign: 'center' }}>{seedMsg}</p>}
          </div> */}
        </div>
      </div>
    </div>
  );
}