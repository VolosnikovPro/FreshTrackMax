import React, { ReactNode } from 'react';

// ─── Tokens ───────────────────────────────────────────────────────────────────
export const T = {
  bg:      '#F5F7FA',
  card:    '#FFFFFF',
  border:  '#E8ECF0',
  text:    '#0F1923',
  sub:     '#64748B',
  muted:   '#94A3B8',
  blue:    '#2563EB',
  blueLight: '#EFF6FF',
  red:     '#DC2626',
  redLight:'#FEF2F2',
  yellow:  '#D97706',
  yellowLight: '#FFFBEB',
  green:   '#16A34A',
  greenLight: '#F0FDF4',
  purple:  '#7C3AED',
  radius:  12,
  radiusSm: 8,
};

// ─── Card ─────────────────────────────────────────────────────────────────────
export function Card({ children, style, onClick }: { children: ReactNode; style?: React.CSSProperties; onClick?: React.MouseEventHandler<HTMLDivElement> | undefined }) {
  return (
    <div style={{
      background: T.card, borderRadius: T.radius,
      border: `1px solid ${T.border}`,
      boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
      ...style,
    }} onClick={onClick}>
      {children}
    </div>
  );
}

// ─── Button ───────────────────────────────────────────────────────────────────
interface BtnProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
}
export function Button({ children, variant = 'primary', size = 'md', fullWidth, style, ...rest }: BtnProps) {
  const pad = { sm: '8px 14px', md: '11px 20px', lg: '15px 24px' }[size];
  const fs  = { sm: 13, md: 14, lg: 16 }[size];
  const vars: Record<string, React.CSSProperties> = {
    primary:   { background: T.blue, color: '#fff', border: 'none' },
    secondary: { background: '#fff', color: T.text, border: `1px solid ${T.border}` },
    danger:    { background: T.redLight, color: T.red, border: `1px solid #FECACA` },
    ghost:     { background: 'transparent', color: T.sub, border: 'none' },
  };
  return (
    <button style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
      padding: pad, borderRadius: T.radiusSm, cursor: 'pointer',
      fontSize: fs, fontWeight: 600, fontFamily: 'inherit',
      width: fullWidth ? '100%' : undefined,
      WebkitTapHighlightColor: 'transparent',
      transition: 'opacity 0.15s',
      ...vars[variant], ...style,
    }}
    onMouseDown={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '0.75'; }}
    onMouseUp={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '1'; }}
    onTouchStart={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '0.75'; }}
    onTouchEnd={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '1'; }}
    {...rest}>
      {children}
    </button>
  );
}

// ─── Badge ────────────────────────────────────────────────────────────────────
export function Badge({ children, color = 'gray' }: { children: ReactNode; color?: 'green'|'yellow'|'red'|'blue'|'gray'|'purple' }) {
  const c = {
    green:  { bg: T.greenLight,  text: T.green },
    yellow: { bg: T.yellowLight, text: T.yellow },
    red:    { bg: T.redLight,    text: T.red },
    blue:   { bg: T.blueLight,   text: T.blue },
    purple: { bg: '#F5F3FF',     text: T.purple },
    gray:   { bg: '#F1F5F9',     text: T.sub },
  }[color];
  return (
    <span style={{
      background: c.bg, color: c.text, borderRadius: 6,
      padding: '3px 9px', fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap',
    }}>
      {children}
    </span>
  );
}

// ─── Input ────────────────────────────────────────────────────────────────────
export function Input({ label, style, type, ...rest }: React.InputHTMLAttributes<HTMLInputElement> & { label?: string }) {
  const [passwordShown, setPasswordShown] = React.useState(false);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {label && <label style={{ fontSize: 13, fontWeight: 600, color: T.text }}>{label}</label>}
      <div style={{ position: "relative", display: "inline-block" }}>
        <input style={{
          padding: '12px 14px', borderRadius: T.radiusSm,
          border: `1.5px solid ${T.border}`, fontSize: 15,
          fontFamily: 'inherit', outline: 'none', background: '#fff',
          WebkitAppearance: 'none', width: "100%",
          ...style,
        }}
        onFocus={e => { e.target.style.borderColor = T.blue; }}
        onBlur={e => { e.target.style.borderColor = T.border; }}
        type={type === "password" && passwordShown ? "text" : type}
        {...rest} />
        {type === "password" ? <svg viewBox="0 0 24 24" style={{
          position: "absolute",
          right: "14px",
          top: "50%",
          transform: "translateY(-50%)",
          cursor: "pointer",
          userSelect: "none",
          width: 20,
          height: 20,
          fill: passwordShown ? "#000" : "#888"
        }}
        onClick={() => setPasswordShown(!passwordShown)}>
          <path d="M12 5c-7 0-11 7-11 7s4 7 11 7 11-7 11-7-4-7-11-7zm0 12a5 5 0 110-10 5 5 0 010 10z"/>
        </svg> : null}
      </div>
    </div>
  );
}

// ─── Select ───────────────────────────────────────────────────────────────────
export function Select({ label, options, style, ...rest }: React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string; options: { value: string; label: string }[] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {label && <label style={{ fontSize: 13, fontWeight: 600, color: T.text }}>{label}</label>}
      <select style={{
        padding: '12px 14px', borderRadius: T.radiusSm,
        border: `1.5px solid ${T.border}`, fontSize: 15,
        fontFamily: 'inherit', background: '#fff', cursor: 'pointer',
        WebkitAppearance: 'none', appearance: 'none',
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%2364748B' stroke-width='1.5' fill='none'/%3E%3C/svg%3E")`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 14px center',
        paddingRight: 36,
        ...style,
      }} {...rest}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

// ─── PageHeader ───────────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: T.text, letterSpacing: '-0.3px' }}>{title}</h1>
        {subtitle && <p style={{ margin: '2px 0 0', color: T.sub, fontSize: 13 }}>{subtitle}</p>}
      </div>
      {actions && <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>{actions}</div>}
    </div>
  );
}

// ─── Loading / Empty / Error ──────────────────────────────────────────────────
export function Loading() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 48, color: T.muted, gap: 10 }}>
      <div style={{ width: 20, height: 20, border: `2px solid ${T.border}`, borderTopColor: T.blue, borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      Загрузка...
    </div>
  );
}

export function Empty({ message = 'Нет данных', hint }: { message?: string; hint?: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 20px', color: T.muted }}>
      <div style={{ fontSize: 36, marginBottom: 8 }}>📭</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: T.sub, marginBottom: 4 }}>{message}</div>
      {hint && <div style={{ fontSize: 13 }}>{hint}</div>}
    </div>
  );
}

export function ErrorMsg({ message }: { message: string }) {
  return (
    <div style={{
      background: T.redLight, color: T.red, borderRadius: T.radiusSm,
      padding: '12px 16px', fontSize: 14, marginBottom: 14,
      border: `1px solid #FECACA`,
    }}>
      {message}
    </div>
  );
}

// ─── Modal (bottom sheet on mobile) ──────────────────────────────────────────
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
      background: 'rgba(0,0,0,0.5)',
    }}
    onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{
        background: '#fff', borderRadius: '20px 20px 0 0', padding: '0 0 32px',
        width: '100%', maxWidth: 560, maxHeight: '92vh', overflowY: 'auto',
        boxShadow: '0 -8px 40px rgba(0,0,0,0.18)',
      }}>
        {/* Handle */}
        <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 0' }}>
          <div style={{ width: 36, height: 4, borderRadius: 2, background: T.border }} />
        </div>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px 16px' }}>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: T.text }}>{title}</h2>
          <button onClick={onClose} style={{
            background: T.bg, border: 'none', borderRadius: '50%',
            width: 32, height: 32, cursor: 'pointer', fontSize: 16, color: T.sub,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>✕</button>
        </div>
        <div style={{ padding: '0 20px' }}>{children}</div>
      </div>
    </div>
  );
}

// ─── StatCard ─────────────────────────────────────────────────────────────────
export function StatCard({ label, value, color, icon }: { label: string; value: string | number; color?: string; icon?: any }) {
  const Icon = icon;
  return (
    <Card style={{ padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 12, color: T.sub, fontWeight: 500, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: color || T.text, lineHeight: 1 }}>{value}</div>
        </div>
        {Icon && <div style={{ color: color || T.sub, opacity: 0.25, transform: 'scale(1.4)' }}><Icon size={20} /></div>}
      </div>
    </Card>
  );
}

// ─── ItemCard (mobile list item) ──────────────────────────────────────────────
export function ItemCard({ children, style, onClick }: { children: ReactNode; style?: React.CSSProperties; onClick?: () => void }) {
  return (
    <Card style={{ padding: '14px 16px', cursor: onClick ? 'pointer' : undefined, ...style }} onClick={onClick}>
      {children}
    </Card>
  );
}

// ─── Divider ─────────────────────────────────────────────────────────────────
export function Divider() {
  return <div style={{ height: 1, background: T.border, margin: '4px 0' }} />;
}

// ─── SectionLabel ─────────────────────────────────────────────────────────────
export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '16px 0 6px' }}>
      {children}
    </div>
  );
}

// ─── FAB (Floating Action Button) ────────────────────────────────────────────
export function FAB({ onClick, children }: { onClick: () => void; children?: ReactNode }) {
  return (
    <button onClick={onClick} style={{
      position: 'fixed', bottom: 88, right: 20, zIndex: 100,
      width: 56, height: 56, borderRadius: '50%',
      background: T.blue, color: '#fff', border: 'none',
      boxShadow: '0 4px 16px rgba(37,99,235,0.4)',
      cursor: 'pointer', fontSize: 24,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      WebkitTapHighlightColor: 'transparent',
    }}>
      {children ?? '+'}
    </button>
  );
}

// ─── FilterTabs ───────────────────────────────────────────────────────────────
export function FilterTabs<T extends string>({ options, value, onChange }: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div style={{
      display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 2,
      scrollbarWidth: 'none', msOverflowStyle: 'none',
    }}>
      {options.map(o => (
        <button key={o.value} onClick={() => onChange(o.value)} style={{
          padding: '7px 14px', borderRadius: 20, fontSize: 13, fontWeight: 600,
          whiteSpace: 'nowrap', cursor: 'pointer', fontFamily: 'inherit',
          border: value === o.value ? 'none' : `1px solid ${T.border}`,
          background: value === o.value ? T.blue : '#fff',
          color: value === o.value ? '#fff' : T.sub,
          flexShrink: 0,
          WebkitTapHighlightColor: 'transparent',
        }}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

// ─── ExpiryBadge ─────────────────────────────────────────────────────────────
export function ExpiryBadge({ days }: { days: number }) {
  if (days < 0)  return <Badge color="red">Просрочен</Badge>;
  if (days < 16) return <Badge color="red">{days} дн. ⚠️</Badge>;
  if (days < 46) return <Badge color="yellow">{days} дн.</Badge>;
  return <Badge color="green">{days} дн.</Badge>;
}