import React, { useEffect, useState, useCallback } from 'react';
import { analyticsApi } from '../services/api';
import { KPIGrid } from '../components/dashboard/KPIGrid';
import { AgentPipeline } from '../components/dashboard/AgentPipeline';
import type { DashboardData, AgentDefinition, RecentOrder } from '../types';

export const DashboardPage: React.FC = () => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, agentsRes] = await Promise.all([
        analyticsApi.getDashboard(),
        analyticsApi.getAgents(),
      ]);
      setDashboard(dash);
      setAgents(agentsRes.agents);
    } catch (err) {
      console.error('Dashboard load failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load, refreshKey]);

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
        <button
          className="btn btn-ghost btn-sm mt-4"
          onClick={() => setRefreshKey((k) => k + 1)}
          disabled={loading}
        >
          ↻ Refresh Data
        </button>
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
          <h3 className="section-title">🛒 Recent Orders</h3>
          <a href="/workflows" className="btn btn-ghost btn-sm">Submit Order →</a>
        </div>
        {loading ? (
          <div className="skeleton" style={{ height: '200px' }} />
        ) : dashboard?.recent_orders?.length ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Amount</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_orders.map((order: RecentOrder) => (
                  <tr key={order.order_id}>
                    <td>
                      <span className="tag">{order.order_id.slice(0, 8)}…</span>
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: `${statusColors[order.status] ?? '#64748b'}22`,
                          color: statusColors[order.status] ?? '#64748b',
                          border: `1px solid ${statusColors[order.status] ?? '#64748b'}44`,
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
                        }}
                      >
                        {order.priority}
                      </span>
                    </td>
                    <td>
                      {parseFloat(order.total_amount).toLocaleString('en-US', {
                        style: 'currency', currency: 'USD',
                      })}
                    </td>
                    <td style={{ color: '#64748b', fontSize: '0.8125rem' }}>
                      {order.created_at
                        ? new Date(order.created_at).toLocaleDateString()
                        : '—'}
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
