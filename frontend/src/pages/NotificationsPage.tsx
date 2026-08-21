import React, { useEffect, useState } from 'react';
import { notificationsApi } from '../api';
import { Card, Loading, T } from '../components/common/UI';

interface Config { urgent_threshold_days: number; planned_threshold_days: number; notification_time: string; base_day: string; max_per_week: number; }
interface Result { sent: number; recipients: string[]; products_included: number; }

export default function NotificationsPage() {
  const [config, setConfig] = useState<Config | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState<'urgent' | 'planned' | null>(null);
  const [lastType, setLastType] = useState<string>('');

  useEffect(() => { notificationsApi.config().then(r => setConfig(r.data)); }, []);

  const trigger = async (type: 'urgent' | 'planned') => {
    setLoading(type); setResult(null); setLastType(type);
    try {
      const res = type === 'urgent' ? await notificationsApi.triggerUrgent() : await notificationsApi.triggerPlanned();
      setResult(res.data);
    } catch (e: any) { alert(e.response?.data?.detail || 'Ошибка отправки'); }
    finally { setLoading(null); }
  };

  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 20, fontWeight: 800, color: T.text }}>Уведомления MAX</h1>

      {/* Config summary */}
      {config && (
        <Card style={{ padding: '16px', marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>Настройки</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {[
              { label: 'Срочный порог', value: `${config.urgent_threshold_days} дн.` },
              { label: 'Плановый порог', value: `${config.planned_threshold_days} дн.` },
              { label: 'Время рассылки', value: config.notification_time },
              { label: 'Макс. в неделю', value: String(config.max_per_week) },
            ].map(({ label, value }) => (
              <div key={label} style={{ background: T.bg, borderRadius: 8, padding: '10px 12px' }}>
                <div style={{ fontSize: 11, color: T.muted, marginBottom: 2 }}>{label}</div>
                <div style={{ fontWeight: 700, fontSize: 16, color: T.text }}>{value}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Trigger buttons */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 16 }}>
        {/* Urgent */}
        <Card style={{ padding: '18px 16px', border: `1px solid #FECACA` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#DC2626', marginBottom: 4 }}>⚠️ Срочные уведомления</div>
              <div style={{ fontSize: 13, color: T.sub }}>
                Продукты с истечением срока менее {config?.urgent_threshold_days ?? 16} дней.
                Отправляется управляющему, кладовщику и руководителю.
              </div>
            </div>
          </div>
          <button onClick={() => trigger('urgent')} disabled={loading !== null}
            style={{ marginTop: 14, width: '100%', background: '#DC2626', color: '#fff', border: 'none', borderRadius: 10, padding: '13px', fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', opacity: loading !== null ? 0.7 : 1 }}>
            {loading === 'urgent' ? '⏳ Отправка...' : '🔔 Отправить срочную рассылку'}
          </button>
        </Card>

        {/* Planned */}
        <Card style={{ padding: '18px 16px', border: `1px solid #FDE68A` }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 15, color: '#D97706', marginBottom: 4 }}>📋 Плановые уведомления</div>
            <div style={{ fontSize: 13, color: T.sub }}>
              Продукты с истечением срока менее {config?.planned_threshold_days ?? 46} дней.
              До {config?.max_per_week ?? 6} раз в неделю, базовый день — воскресенье.
            </div>
          </div>
          <button onClick={() => trigger('planned')} disabled={loading !== null}
            style={{ marginTop: 14, width: '100%', background: '#D97706', color: '#fff', border: 'none', borderRadius: 10, padding: '13px', fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', opacity: loading !== null ? 0.7 : 1 }}>
            {loading === 'planned' ? '⏳ Отправка...' : '📣 Отправить плановую рассылку'}
          </button>
        </Card>
      </div>

      {/* Result */}
      {result && (
        <Card style={{ padding: '16px', background: T.greenLight, border: `1px solid #BBF7D0`, marginBottom: 16 }}>
          <div style={{ fontWeight: 700, color: T.green, fontSize: 15, marginBottom: 8 }}>✅ Рассылка выполнена</div>
          <div style={{ display: 'flex', gap: 20, fontSize: 14 }}>
            <div><span style={{ fontWeight: 800 }}>{result.sent}</span> <span style={{ color: T.sub }}>сообщений</span></div>
            <div><span style={{ fontWeight: 800 }}>{result.products_included}</span> <span style={{ color: T.sub }}>продуктов</span></div>
          </div>
          {result.recipients.length > 0 && (
            <div style={{ fontSize: 12, color: T.sub, marginTop: 8 }}>Получатели: {result.recipients.join(', ')}</div>
          )}
        </Card>
      )}

      {/* MVP limitations note */}
      <Card style={{ padding: '14px 16px', background: T.bg }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: T.muted, marginBottom: 8 }}>Ограничения MVP</div>
        {['Журнал доставки не реализован', 'Email и Telegram не входят в MVP', 'Автоматическое расписание требует настройки планировщика'].map(t => (
          <div key={t} style={{ fontSize: 12, color: T.muted, padding: '4px 0', borderTop: `1px solid ${T.border}` }}>· {t}</div>
        ))}
      </Card>
    </div>
  );
}