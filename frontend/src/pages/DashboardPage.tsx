import React, { useEffect, useState, useCallback, useRef } from 'react';
import { analyticsApi } from '../services/api';
import { KPIGrid } from '../components/dashboard/KPIGrid';
import { AgentPipeline } from '../components/dashboard/AgentPipeline';
import type { DashboardData, AgentDefinition, RecentOrder } from '../types';
import {
  formatOrderId,
  getCustomerName,
  formatCurrency,
  formatTimeAgo,
} from '../utils/formatters';

export const DashboardPage: React.FC = () => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const isMountedRef = useRef(true);

  const fetchDashboardData = useCallback(async (isSilent = false) => {
    if (!isSilent) setIsUpdating(true);
    try {
      const [dash, agentsRes] = await Promise.all([
        analyticsApi.getDashboard(),
        analyticsApi.getAgents(),
      ]);
      if (isMountedRef.current) {
        setDashboard(dash);
        setAgents(agentsRes.agents);
        setLastUpdated(new Date());
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
    isMountedRef.current = true;
    fetchDashboardData(false);

    // Live auto-sync every 3.5 seconds
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchDashboardData(true);
      }
    }, 3500);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        fetchDashboardData(true);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [fetchDashboardData]);

  const statusColors: Record<string, string> = {
    pending:    '#f59e0b',
    in_transit: '#3b82f6',
    delivered:  '#10b981',
    cancelled:  '#ef4444',
    failed:     '#ef4444',
  };

  const priorityColors: Record<string, string> = {
    critical: '#ef4444',
    high:     '#f59e0b',
    standard: '#3b82f6',
  };

  return (
    <div className="page-content animate-fade-in">
      {/* Page header */}
      <div className="page-header">
        <h1>
          <span className="gradient-text">Executive Dashboard</span>
        </h1>
        <p>Real-time supply chain monitoring across all 18 AI agents</p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => fetchDashboardData(false)}
            disabled={isUpdating}
          >
            {isUpdating ? '↻ Refreshing…' : '↻ Refresh Data'}
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: '#10b981' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 6px #10b981' }} />
            Live Auto-Sync (3.5s) • Updated {lastUpdated.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* KPI Grid */}
      <KPIGrid kpis={dashboard?.kpis ?? null} loading={loading} />

      {/* Charts row */}
      <div className="grid-2 mt-6">
        {/* Orders by status */}
        <div className="card animate-fade-in" style={{ animationDelay: '100ms' }}>
          <h3 className="section-title mb-4">📊 Orders by Status</h3>
          {loading ? (
            <div className="skeleton" style={{ height: '160px' }} />
          ) : dashboard?.orders_by_status ? (
            <div className="status-bars">
              {Object.entries(dashboard.orders_by_status).map(([status, count]) => {
                const total = Object.values(dashboard.orders_by_status).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? (count / total) * 100 : 0;
                const color = statusColors[status] ?? '#64748b';
                return (
                  <div key={status} className="status-bar-row">
                    <div className="status-bar-label">
                      <span className="status-dot" style={{ background: color }} />
                      <span style={{ textTransform: 'capitalize' }}>{status.replace('_', ' ')}</span>
                    </div>
                    <div className="status-bar-track">
                      <div
                        className="status-bar-fill"
                        style={{ width: `${pct}%`, background: color }}
                      />
                    </div>
                    <span className="status-bar-count">{count}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-icon">📭</span>
              <p>No order data yet</p>
            </div>
          )}
        </div>

        {/* Inventory health */}
        <div className="card animate-fade-in" style={{ animationDelay: '200ms' }}>
          <h3 className="section-title mb-4">🏪 Inventory Health</h3>
          {loading ? (
            <div className="skeleton" style={{ height: '160px' }} />
          ) : dashboard?.inventory_health ? (
            <div>
              <div className="inv-health-ring">
                <div className="inv-health-stats">
                  {[
                    { label: 'Healthy', value: dashboard.inventory_health.healthy, color: '#10b981' },
                    { label: 'Low Stock', value: dashboard.inventory_health.low_stock, color: '#f59e0b' },
                    { label: 'Out of Stock', value: dashboard.inventory_health.out_of_stock, color: '#ef4444' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="inv-stat-row">
                      <span className="status-dot" style={{ background: color }} />
                      <span className="inv-stat-label">{label}</span>
                      <span className="inv-stat-value" style={{ color }}>{value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="progress-bar mt-4">
                <div
                  className="progress-bar-fill"
                  style={{
                    width: `${Math.round(
                      (dashboard.inventory_health.healthy /
                        Math.max(dashboard.inventory_health.total_locations, 1)) * 100
                    )}%`,
                  }}
                />
              </div>
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.5rem' }}>
                {dashboard.inventory_health.total_locations} total SKU locations
              </p>
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-icon">📦</span>
              <p>No inventory data yet</p>
            </div>
          )}
        </div>
      </div>

      {/* Agent Pipeline */}
      <div className="mt-6">
        <AgentPipeline agents={agents} loading={loading} />
      </div>

      {/* Recent Orders */}
      <div className="card mt-6 animate-fade-in" style={{ animationDelay: '300ms' }}>
        <div className="section-header">
          <h3 className="section-title">🛒 Recent Orders & Commercial Pipeline</h3>
          <a href="/workflow" className="btn btn-ghost btn-sm">Manage Workflows →</a>
        </div>
        {loading ? (
          <div className="skeleton" style={{ height: '200px' }} />
        ) : dashboard?.recent_orders?.length ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Order Reference</th>
                  <th>Client Account</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Total Amount</th>
                  <th>Timeline</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_orders.map((order: RecentOrder) => (
                  <tr key={order.order_id}>
                    <td>
                      <span className="tag" style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                        {formatOrderId(order.order_id)}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600, color: 'var(--c-text-primary)' }}>
                        {getCustomerName((order as any).customer_id || order.order_id)}
                      </span>
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: `${statusColors[order.status] ?? '#64748b'}22`,
                          color: statusColors[order.status] ?? '#64748b',
                          border: `1px solid ${statusColors[order.status] ?? '#64748b'}44`,
                          textTransform: 'uppercase',
                        }}
                      >
                        {order.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: `${priorityColors[order.priority] ?? '#64748b'}22`,
                          color: priorityColors[order.priority] ?? '#64748b',
                          border: `1px solid ${priorityColors[order.priority] ?? '#64748b'}44`,
                          textTransform: 'capitalize',
                        }}
                      >
                        {order.priority}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: '#10b981' }}>
                      {formatCurrency(order.total_amount)}
                    </td>
                    <td style={{ color: 'var(--c-text-muted)', fontSize: '0.8125rem' }}>
                      {formatTimeAgo(order.created_at)}
                    </td>
                    <td>
                      <a
                        href={`/workflow${(order as any).workflow_id ? `?id=${(order as any).workflow_id}` : ''}`}
                        className="btn btn-ghost btn-sm"
                        style={{ fontSize: '0.75rem', padding: '2px 8px' }}
                      >
                        View Flow →
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <span className="empty-icon">📭</span>
            <p>No orders yet. Submit a workflow to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
};
