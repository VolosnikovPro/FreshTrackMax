import React, { useEffect, useState } from 'react';
import { adminApi, batchesApi } from '../api';
import { AdminSummary, Batch } from '../types';
import { Card, StatCard, Loading, ExpiryBadge, T } from '../components/common/UI';
import { Package, CalendarClock, AlertTriangle, Users2, Flame, DollarSign } from 'lucide-react';
import { format, parseISO } from 'date-fns';

export default function DashboardPage() {
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [urgentBatches, setUrgentBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      adminApi.summary().then(r => setSummary(r.data)),
      batchesApi.expiringUrgent().then(r => setUrgentBatches(r.data)),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;

  const today = new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' });

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: T.text }}>Дашборд</h1>
        <p style={{ margin: '2px 0 0', fontSize: 13, color: T.sub, textTransform: 'capitalize' }}>{today}</p>
      </div>

      {summary && (
        <>
          {/* Alert banner */}
          {summary.expiring_soon_urgent > 0 && (
            <div style={{
              background: T.redLight, border: `1px solid #FECACA`,
              borderRadius: 12, padding: '14px 16px', marginBottom: 14,
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <AlertTriangle size={20} color={T.red} style={{ flexShrink: 0 }} />
              <div>
                <div style={{ fontWeight: 700, color: T.red, fontSize: 14 }}>
                  {summary.expiring_soon_urgent} партий истекают &lt;16 дней
                </div>
                <div style={{ fontSize: 12, color: '#EF4444', marginTop: 1 }}>Требуется проверка и решение</div>
              </div>
            </div>
          )}

          {/* Stats grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            <StatCard label="Продукты" value={summary.total_products} color={T.blue} icon={<Package />} />
            <StatCard label="Партии" value={summary.total_batches} color={T.purple} icon={<CalendarClock />} />
            <StatCard label="Срочно" value={summary.expiring_soon_urgent}
              color={summary.expiring_soon_urgent > 0 ? T.red : T.green} icon={<AlertTriangle />} />
            <StatCard label="Планово" value={summary.expiring_soon_planned}
              color={summary.expiring_soon_planned > 0 ? T.yellow : T.green} icon={<CalendarClock />} />
            <StatCard label="Питающихся" value={summary.today_headcount ?? '—'} color="#0891B2" icon={<Users2 />} />
            <StatCard label="Расход (записей)" value={summary.today_consumption_entries} color={T.green} icon={<Flame />} />
          </div>
        </>
      )}

      {/* Urgent expiry list */}
      {urgentBatches.length > 0 ? (
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: T.muted, letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 8 }}>
            ⚠️ Срочно истекают
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {urgentBatches.map(b => (
              <Card key={b.id} style={{ padding: '14px 16px', borderLeft: `3px solid ${T.red}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {b.product_name}
                    </div>
                    <div style={{ fontSize: 12, color: T.sub, marginTop: 2 }}>
                      {b.quantity} {b.unit}{b.batch_number ? ` · ${b.batch_number}` : ''}
                    </div>
                    <div style={{ fontSize: 12, color: T.muted, marginTop: 1 }}>
                      до {format(parseISO(b.expiry_date), 'dd.MM.yyyy')}
                    </div>
                  </div>
                  <ExpiryBadge days={b.days_until_expiry} />
                </div>
              </Card>
            ))}
          </div>
        </div>
      ) : (
        <Card style={{ padding: '20px 16px', textAlign: 'center' }}>
          <div style={{ fontSize: 28, marginBottom: 6 }}>✅</div>
          <div style={{ fontWeight: 700, color: T.green, fontSize: 14 }}>Всё в порядке</div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 2 }}>Нет партий с критичным сроком годности</div>
        </Card>
      )}
    </div>
  );
}