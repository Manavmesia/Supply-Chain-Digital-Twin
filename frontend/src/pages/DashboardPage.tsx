import React, { useEffect, useState, useCallback, useRef } from 'react';
import { analyticsApi } from '../services/api';
import { Link } from 'react-router-dom';
import { KPIGrid } from '../components/dashboard/KPIGrid';
import type { DashboardData, RecentOrder } from '../types';
import {
  BarChart3,
  Layers,
  Package,
  RefreshCw,
  Inbox,
  ArrowRight,
} from 'lucide-react';
import {
  formatOrderId,
  getCustomerName,
  formatCurrency,
  formatTimeAgo,
} from '../utils/formatters';

export const DashboardPage: React.FC = () => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const isMountedRef = useRef(true);

  const fetchDashboardData = useCallback(async (isSilent = false) => {
    if (!isSilent) setIsUpdating(true);
    try {
      const dash = await analyticsApi.getDashboard();
      if (isMountedRef.current) {
        setDashboard(dash);
      }
    } catch (err) {
      console.error('Dashboard load failed:', err);
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
        setIsUpdating(false);
      }
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    isMountedRef.current = true;

    analyticsApi.getDashboard().then((dash) => {
      if (!ignore && isMountedRef.current) {
        setDashboard(dash);
        setLoading(false);
      }
    }).catch((err) => {
      console.error('Dashboard load failed:', err);
      if (!ignore && isMountedRef.current) setLoading(false);
    });

    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchDashboardData(true);
      }
    }, 4000);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        fetchDashboardData(true);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      ignore = true;
      isMountedRef.current = false;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [fetchDashboardData]);

  const statusBadges: Record<string, { bg: string; text: string; border: string }> = {
    delivered:  { bg: '#ecfdf5', text: '#059669', border: '#a7f3d0' },
    in_transit: { bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' },
    pending:    { bg: '#fffbeb', text: '#d97706', border: '#fde68a' },
    cancelled:  { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
    failed:     { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
  };

  const priorityBadges: Record<string, { bg: string; text: string }> = {
    critical: { bg: '#fef2f2', text: '#dc2626' },
    high:     { bg: '#fffbeb', text: '#d97706' },
    standard: { bg: '#f1f5f9', text: '#475569' },
    low:      { bg: '#f8fafc', text: '#64748b' },
  };

  return (
    <div className="page-container animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Digital Twin Overview</h1>
          <p className="page-subtitle">
            Real-time fulfillment metrics, warehouse inventory distribution, and commercial operations.
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={() => { setIsUpdating(true); fetchDashboardData(false); }}
            disabled={isUpdating}
            className="btn-secondary"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isUpdating ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Grid */}
      <KPIGrid kpis={dashboard?.kpis ?? null} loading={loading} />

      {/* Charts / Distribution row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)', marginBottom: 'var(--space-6)' }}>
        {/* Orders by status */}
        <div className="card" style={{ padding: 'var(--space-6)', marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
            <BarChart3 size={16} style={{ color: 'var(--c-text-muted)' }} />
            <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--c-text-primary)', margin: 0, textTransform: 'uppercase', letterSpacing: 'var(--track-wide)' }}>
              Fulfillment Pipeline by Status
            </h3>
          </div>

          {loading ? (
            <div style={{ height: '140px', background: 'var(--c-bg-subtle)', borderRadius: 'var(--radius-md)' }} />
          ) : dashboard?.orders_by_status ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {Object.entries(dashboard.orders_by_status).map(([st, count]) => {
                const total = Object.values(dashboard.orders_by_status).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? (count / total) * 100 : 0;
                return (
                  <div key={st}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', marginBottom: '4px' }}>
                      <span style={{ color: 'var(--c-text-secondary)', textTransform: 'capitalize' }}>{st.replace('_', ' ')}</span>
                      <span style={{ color: 'var(--c-text-primary)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{count} ({Math.round(pct)}%)</span>
                    </div>
                    <div style={{ height: '6px', background: 'var(--c-bg-subtle)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: st === 'delivered' ? 'var(--c-success)' : st === 'in_transit' ? 'var(--c-info)' : 'var(--c-warning)', borderRadius: 'var(--radius-full)' }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--c-text-muted)' }}>
              <Inbox size={20} style={{ margin: '0 auto 6px' }} />
              <p style={{ margin: 0, fontSize: 'var(--text-xs)' }}>No order distribution data</p>
            </div>
          )}
        </div>

        {/* Inventory health */}
        <div className="card" style={{ padding: 'var(--space-6)', marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
            <Layers size={16} style={{ color: 'var(--c-text-muted)' }} />
            <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--c-text-primary)', margin: 0, textTransform: 'uppercase', letterSpacing: 'var(--track-wide)' }}>
              Warehouse Inventory Distribution
            </h3>
          </div>

          {loading ? (
            <div style={{ height: '140px', background: 'var(--c-bg-subtle)', borderRadius: 'var(--radius-md)' }} />
          ) : dashboard?.inventory_health ? (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-2-5)', marginBottom: 'var(--space-4)' }}>
                <div style={{ background: 'var(--c-bg-subtle)', padding: 'var(--space-3) var(--space-3-5)', borderRadius: 'var(--radius-md)', border: '1px solid var(--c-border)' }}>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 'var(--track-wide)' }}>Healthy SKUs</div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--c-success)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                    {dashboard.inventory_health.healthy}
                  </div>
                </div>
                <div style={{ background: 'var(--c-bg-subtle)', padding: 'var(--space-3) var(--space-3-5)', borderRadius: 'var(--radius-md)', border: '1px solid var(--c-border)' }}>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 'var(--track-wide)' }}>Low Stock</div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--c-warning)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                    {dashboard.inventory_health.low_stock}
                  </div>
                </div>
                <div style={{ background: 'var(--c-bg-subtle)', padding: 'var(--space-3) var(--space-3-5)', borderRadius: 'var(--radius-md)', border: '1px solid var(--c-border)' }}>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 'var(--track-wide)' }}>Out of Stock</div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--c-danger)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                    {dashboard.inventory_health.out_of_stock}
                  </div>
                </div>
              </div>

              <div style={{ height: '6px', background: 'var(--c-bg-subtle)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${Math.round(
                      (dashboard.inventory_health.healthy /
                        Math.max(dashboard.inventory_health.total_locations, 1)) * 100
                    )}%`,
                    background: 'var(--c-success)',
                    borderRadius: 'var(--radius-full)',
                  }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)', marginTop: 'var(--space-2)' }}>
                <span>SKU Coverage Target: &gt;95%</span>
                <span>{dashboard.inventory_health.total_locations} SKU location checkpoints</span>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '32px', color: '#64748b' }}>
              <Inbox size={20} style={{ margin: '0 auto 6px' }} />
              <p style={{ margin: 0, fontSize: '12px' }}>No inventory telemetry available</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Orders */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 'var(--radius-lg)', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Package size={15} style={{ color: '#64748b' }} />
            <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a', margin: 0, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Recent Commercial Orders
            </h3>
          </div>
          <Link
            to="/orders"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '12px',
              color: '#2563eb',
              textDecoration: 'none',
              fontWeight: 500,
            }}
          >
            <span>Open Orders Module</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        {loading ? (
          <div style={{ height: '160px', background: '#f8fafc', borderRadius: 'var(--radius-md)' }} />
        ) : dashboard?.recent_orders?.length ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#64748b', textAlign: 'left', background: '#f8fafc' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>ORDER REFERENCE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>CLIENT ACCOUNT</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>STATUS</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>PRIORITY</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>ORDER VALUE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>PLACED</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_orders.map((order: RecentOrder) => {
                  const sBadge = statusBadges[order.status] || statusBadges.pending;
                  const pBadge = priorityBadges[order.priority] || priorityBadges.standard;

                  return (
                    <tr key={order.order_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '14px 16px', fontFamily: 'monospace', fontWeight: 600, color: '#0f172a' }}>
                        {formatOrderId(order.order_id)}
                      </td>
                      <td style={{ padding: '14px 16px', color: '#334155' }}>
                        {getCustomerName(order.customer_id || order.order_id)}
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            padding: '3px 10px',
                            borderRadius: '9999px',
                            background: sBadge.bg,
                            color: sBadge.text,
                            border: `1px solid ${sBadge.border}`,
                            textTransform: 'capitalize',
                          }}
                        >
                          {order.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            padding: '3px 8px',
                            borderRadius: '9999px',
                            background: pBadge.bg,
                            color: pBadge.text,
                            textTransform: 'uppercase',
                          }}
                        >
                          {order.priority}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#0f172a' }}>
                        {formatCurrency(order.total_amount)}
                      </td>
                      <td style={{ padding: '14px 16px', color: '#64748b' }}>
                        {formatTimeAgo(order.created_at)}
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <Link
                          to={`/orders?order_id=${order.order_id}&tab=decision`}
                          style={{
                            fontSize: '12px',
                            color: '#2563eb',
                            textDecoration: 'none',
                            fontWeight: 500,
                          }}
                        >
                          View Details &rarr;
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '32px', color: '#64748b' }}>
            <Inbox size={20} style={{ margin: '0 auto 6px' }} />
            <p style={{ margin: 0, fontSize: '12px' }}>No orders in pipeline</p>
          </div>
        )}
      </div>
    </div>
  );
};

