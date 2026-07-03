import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { appRoutes } from '../../routes';
import { T } from './UI';

const ROLE_LABELS: Record<string, string> = {
  admin: 'Администратор',
  manager: 'Управляющий',
  storekeeper: 'Кладовщик',
  nutrition_manager: 'Управл. по питанию',
};

export default function Layout() {
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  const navItems = appRoutes.filter(({ inNav, allowedRoles }) =>
    inNav && (allowedRoles.length === 0 || allowedRoles.some(r => hasRole(r)))
  );

  // Bottom nav shows first 5 items max
  const bottomItems = navItems.slice(0, 5);

  return (
    <div style={{ minHeight: '100vh', background: T.bg, fontFamily: "'Onest', system-ui, sans-serif", paddingBottom: 72 }}>
      {/* Top header */}
      <header style={{
        position: 'sticky', top: 0, zIndex: 50,
        background: '#fff', borderBottom: `1px solid ${T.border}`,
        padding: '0 16px', height: 52,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            background: T.blue, borderRadius: 6, padding: '3px 8px',
            fontSize: 11, fontWeight: 800, letterSpacing: '0.06em', color: '#fff',
          }}>FRESH</span>
          <span style={{ fontWeight: 800, fontSize: 16, color: T.text }}>Track</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: T.text, lineHeight: 1.2 }}>
              {user?.display_name || user?.username}
            </div>
            <div style={{ fontSize: 11, color: T.sub }}>{ROLE_LABELS[user?.role || '']}</div>
          </div>
          {window.WebApp ? null : <button onClick={() => { logout(); navigate('/login'); }} style={{
            background: T.bg, border: `1px solid ${T.border}`, borderRadius: 8,
            padding: '6px 10px', fontSize: 12, color: T.sub, cursor: 'pointer', fontFamily: 'inherit',
          }}>
            Выйти
          </button>}
        </div>
      </header>

      {/* Page content */}
      <main style={{ padding: '16px', maxWidth: 640, margin: '0 auto' }}>
        <Outlet />
      </main>

      {/* Bottom navigation */}
      <nav style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 50,
        background: '#fff', borderTop: `1px solid ${T.border}`,
        display: 'flex', height: 72,
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}>
        {bottomItems.map(({ path, label, icon: Icon }) => (
          <NavLink key={path} to={path} end={path === '/'} style={({ isActive }) => ({
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', gap: 3, textDecoration: 'none',
            color: isActive ? T.blue : T.muted,
            fontSize: 10, fontWeight: isActive ? 700 : 500,
            borderTop: isActive ? `2px solid ${T.blue}` : '2px solid transparent',
            WebkitTapHighlightColor: 'transparent',
            transition: 'color 0.15s',
            paddingTop: 4,
          })}>
            <Icon size={22} />
            <span style={{ letterSpacing: '-0.01em' }}>{label.split(' ')[0]}</span>
          </NavLink>
        ))}

        {/* If more than 5 nav items, show "Ещё" with all remaining in a popover */}
        {navItems.length > 5 && <MoreMenu items={navItems.slice(5)} />}
      </nav>
    </div>
  );
}

function MoreMenu({ items }: { items: typeof appRoutes }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  return (
    <>
      <button onClick={() => setOpen(!open)} style={{
        flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', gap: 3, border: 'none', background: 'none',
        color: T.muted, fontSize: 10, fontWeight: 500, cursor: 'pointer',
        fontFamily: 'inherit', paddingTop: 4,
        WebkitTapHighlightColor: 'transparent',
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/>
        </svg>
        Ещё
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 90 }} />
          <div style={{
            position: 'fixed', bottom: 76, right: 8, zIndex: 100,
            background: '#fff', borderRadius: 14, padding: '8px 0',
            boxShadow: '0 8px 32px rgba(0,0,0,0.16)', border: `1px solid ${T.border}`,
            minWidth: 200,
          }}>
            {items.map(({ path, label, icon: Icon }) => (
              <button key={path} onClick={() => { navigate(path); setOpen(false); }} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                width: '100%', padding: '13px 18px', border: 'none',
                background: 'none', cursor: 'pointer', fontSize: 14,
                fontWeight: 500, color: T.text, fontFamily: 'inherit',
                WebkitTapHighlightColor: 'transparent',
                textAlign: 'left',
              }}>
                <Icon size={18} color={T.sub} />
                {label}
              </button>
            ))}
          </div>
        </>
      )}
    </>
  );
}