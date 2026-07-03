import { useNavigate } from 'react-router-dom';
import { T } from '../components/common/UI';

export default function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: T.bg, fontFamily: "'Onest', system-ui, sans-serif", padding: 24 }}>
      <div style={{ fontSize: 72, fontWeight: 900, color: T.border, lineHeight: 1 }}>404</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: T.sub, margin: '12px 0 6px' }}>Страница не найдена</div>
      <div style={{ fontSize: 14, color: T.muted, marginBottom: 24, textAlign: 'center' }}>Запрошенный адрес не существует в системе</div>
      <button onClick={() => navigate('/')} style={{ background: T.blue, color: '#fff', border: 'none', borderRadius: 10, padding: '12px 28px', fontSize: 15, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>← На главную</button>
    </div>
  );
}