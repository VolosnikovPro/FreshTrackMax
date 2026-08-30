import React, { useEffect, useState } from 'react';
import { adminApi, batchesApi, financialApi } from '../api';
import { AdminSummary, Batch } from '../types';
import { Card, StatCard, Loading, ExpiryBadge, T } from '../components/common/UI';
import { Package, CalendarClock, AlertTriangle, Users2, Flame, DollarSign, TrendingUp, AlertCircle } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { useAuth } from '../hooks/useAuth';
import { useSite } from '../hooks/useSite';

export default function DashboardPage() {
  const { user } = useAuth();
  const { currentSiteId } = useSite();
  const role = user?.role;
  const isNutritionManager = role === 'nutrition_manager';
  const isAdmin = role === 'admin' || role === 'superadmin';
  const isManager = role === 'manager';

  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [urgentBatches, setUrgentBatches] = useState<Batch[]>([]);
  const [plannedBatches, setPlannedBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [financialSummary, setFinancialSummary] = useState<{rows: any[]; average: number | null}>({ rows: [], average: null });

  useEffect(() => {
    if (isNutritionManager) {
      Promise.all([
        batchesApi.expiringUrgent(currentSiteId).then(r => setUrgentBatches(r.data)),
        batchesApi.expiringPlanned(currentSiteId).then(r => setPlannedBatches(r.data)),
        financialApi.list({ site_id: currentSiteId, month: new Date().toISOString().slice(0, 7) }).then(r => setFinancialSummary(r.data)),
      ]).finally(() => setLoading(false));
    } else {
      Promise.all([
        adminApi.summary(currentSiteId).then(r => setSummary(r.data)),
        batchesApi.expiringUrgent(currentSiteId).then(r => setUrgentBatches(r.data)),
        batchesApi.expiringPlanned(currentSiteId).then(r => setPlannedBatches(r.data)),
      ]).finally(() => setLoading(false));
    }
  }, [isNutritionManager, currentSiteId]);

  if (loading) return <Loading />;

  // UOP Dashboard - simplified with urgent/expired, cost per day, average
  if (isNutritionManager) {
    return (
      <div>
        <h1 style={{ margin: '0 0 16px', fontSize: 20, fontWeight: 800, color: T.text }}>Дашборд</h1>

        {/* Urgent batches */}
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ margin: '0 0 10px', fontSize: 15, fontWeight: 700, color: T.text }}>
            ⚠️ Срочные сроки годности (≤ 15 дней) — {urgentBatches.length}
          </h2>
          {urgentBatches.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {urgentBatches.map(b => (
                <Card key={b.id} style={{ padding: '12px 16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {b.product_name}
                      </div>
                      <div style={{ fontSize: 11, color: T.sub, marginTop: 2 }}>
                        {b.quantity} {b.unit} | {b.batch_number ? `УПД: ${b.batch_number}` : '—'}
                      </div>
                    </div>
                    <ExpiryBadge days={b.days_until_expiry} />
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card style={{ padding: '16px', textAlign: 'center', color: T.sub }}>
              <div style={{ fontSize: 24, marginBottom: 4 }}>✅</div>
              <div style={{ fontWeight: 600 }}>Нет срочных партий</div>
            </Card>
          )}
        </div>

        {/* Planned batches */}
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ margin: '0 0 10px', fontSize: 15, fontWeight: 700, color: T.text }}>
            📋 Плановые сроки годности (≤ 45 дней) — {plannedBatches.length}
          </h2>
          {plannedBatches.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {plannedBatches.map(b => (
                <Card key={b.id} style={{ padding: '10px 16px', opacity: 0.8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: 12, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {b.product_name} — {b.quantity} {b.unit}
                    </div>
                    <ExpiryBadge days={b.days_until_expiry} />
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card style={{ padding: '16px', textAlign: 'center', color: T.sub }}>
              <div style={{ fontSize: 24, marginBottom: 4 }}>📅</div>
              <div style={{ fontWeight: 600 }}>Нет плановых партий</div>
            </Card>
          )}
        </div>

        {/* Contractual cost per day */}
        <div>
          <h2 style={{ margin: '0 0 10px', fontSize: 15, fontWeight: 700, color: T.text }}>
            💰 Себестоимость дня
          </h2>
          <Card style={{ padding: '16px' }}>
            <div style={{ fontSize: 13, color: T.sub, textAlign: 'center' }}>
              Сумма накладной без НДС / количество питающихся
            </div>
            <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-around', fontSize: 12, color: T.text }}>
              <div>
                <div style={{ color: T.sub }}>Средняя в день</div>
                <div style={{ fontWeight: 700 }}>{financialSummary.average ?? '—'}</div>
              </div>
              <div>
                <div style={{ color: T.sub }}>За вчера</div>
                <div style={{ fontWeight: 700 }}>—</div>
              </div>
              <div>
                <div style={{ color: T.sub }}>За неделю</div>
                <div style={{ fontWeight: 700 }}>—</div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  // Admin/Manager Dashboard - full view
  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 20, fontWeight: 800, color: T.text }}>Дашборд</h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 12, marginBottom: 20 }}>
        <StatCard icon={Package} label="Продуктов" value={summary?.total_products ?? 0} />
        <StatCard icon={CalendarClock} label="Партий" value={summary?.total_batches ?? 0} />
        <StatCard icon={AlertTriangle} label="Срочно (≤15 дн)" value={summary?.expiring_soon_urgent ?? 0} color="red" />
        <StatCard icon={Users2} label="Питающихся сегодня" value={summary?.today_headcount ?? '—'} />
        <StatCard icon={Flame} label="Расход сегодня" value={summary?.today_consumption_entries ?? 0} />
        <StatCard icon={DollarSign} label="С ценой" value={summary?.total_products_with_cost ?? 0} />
      </div>

      {urgentBatches.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ margin: '0 0 10px', fontSize: 15, fontWeight: 700, color: T.text }}>
            ⚠️ Срочные сроки годности (≤ 15 дней) — {urgentBatches.length}
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {urgentBatches.map(b => (
              <Card key={b.id} style={{ padding: '12px 16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {b.product_name}
                    </div>
                    <div style={{ fontSize: 11, color: T.sub, marginTop: 2 }}>
                      {b.quantity} {b.unit} | {b.batch_number ? `УПД: ${b.batch_number}` : '—'}
                    </div>
                  </div>
                  <ExpiryBadge days={b.days_until_expiry} />
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {plannedBatches.length > 0 && (
        <div>
          <h2 style={{ margin: '0 0 10px', fontSize: 15, fontWeight: 700, color: T.text }}>
            📋 Плановые сроки годности (≤ 45 дней) — {plannedBatches.length}
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {plannedBatches.map(b => (
              <Card key={b.id} style={{ padding: '10px 16px', opacity: 0.8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: 12, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {b.product_name} — {b.quantity} {b.unit}
                  </div>
                  <ExpiryBadge days={b.days_until_expiry} />
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {urgentBatches.length === 0 && plannedBatches.length === 0 && (
        <Card style={{ padding: '20px 16px', textAlign: 'center' }}>
          <div style={{ fontSize: 28, marginBottom: 6 }}>✅</div>
          <div style={{ fontWeight: 700, color: T.green, fontSize: 14 }}>Всё в порядке</div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 2 }}>Нет партий с критичным сроком годности</div>
        </Card>
      )}
    </div>
  );
}
