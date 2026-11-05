import React, { useEffect, useState, useCallback, useRef } from 'react';
import { analyticsApi } from '../services/api';
import { KPIGrid } from '../components/dashboard/KPIGrid';
import { AgentPipeline } from '../components/dashboard/AgentPipeline';
import { DigitalTwinCanvas } from '../components/dashboard/DigitalTwinCanvas';
import type { DashboardData, AgentDefinition, RecentOrder, TwinNetworkData } from '../types';
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
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [networkData, setNetworkData] = useState<TwinNetworkData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const isMountedRef = useRef(true);

  const fetchDashboardData = useCallback(async (isSilent = false) => {
    if (!isSilent) setIsUpdating(true);
    try {
      const [dash, agentsRes, netRes] = await Promise.all([
        analyticsApi.getDashboard(),
        analyticsApi.getAgents(),
        analyticsApi.getNetworkTopology(),
      ]);
      if (isMountedRef.current) {
        setDashboard(dash);
        setAgents(agentsRes.agents);
        setNetworkData(netRes);
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
    let ignore = false;
    isMountedRef.current = true;

    Promise.all([
      analyticsApi.getDashboard(),
      analyticsApi.getAgents(),
      analyticsApi.getNetworkTopology(),
    ]).then(([dash, agentsRes, netRes]) => {
      if (!ignore && isMountedRef.current) {
        setDashboard(dash);
        setAgents(agentsRes.agents);
        setNetworkData(netRes);
        setLastUpdated(new Date());
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
    <div style={{ padding: '24px 28px', maxWidth: '1440px', margin: '0 auto', color: 'var(--c-text-primary)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '22px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700, margin: 0, letterSpacing: '-0.02em', color: 'var(--c-text-primary)' }}>
            Enterprise Supply Chain Digital Twin
          </h1>
          <p style={{ color: '#64748b', fontSize: '13px', margin: '4px 0 0 0' }}>
            Decentralized multi-agent execution & real-time physical network telemetry
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#059669', background: '#ecfdf5', border: '1px solid #a7f3d0', padding: '5px 10px', borderRadius: '4px' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#059669' }} />
            <span>Telemetry Synced {lastUpdated.toLocaleTimeString()}</span>
          </div>
          <button
            onClick={() => { setIsUpdating(true); fetchDashboardData(false); }}
            disabled={isUpdating}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '5px',
              color: '#334155',
              cursor: 'pointer',
              fontSize: '12px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
            }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isUpdating ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Grid */}
      <KPIGrid kpis={dashboard?.kpis ?? null} loading={loading} />

      {/* Spatial Digital Twin Network Topology Canvas */}
      <div style={{ marginBottom: '24px' }}>
        <DigitalTwinCanvas
          data={networkData}
          loading={loading}
          onRefresh={() => fetchDashboardData(false)}
        />
      </div>

      {/* Charts / Distribution row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        {/* Orders by status */}
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '18px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <BarChart3 size={15} style={{ color: '#64748b' }} />
            <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a', margin: 0, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Fulfillment Pipeline by Status
            </h3>
          </div>

          {loading ? (
            <div style={{ height: '140px', background: '#f8fafc', borderRadius: '6px' }} />
          ) : dashboard?.orders_by_status ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {Object.entries(dashboard.orders_by_status).map(([st, count]) => {
                const total = Object.values(dashboard.orders_by_status).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? (count / total) * 100 : 0;
                return (
                  <div key={st}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                      <span style={{ color: '#475569', textTransform: 'capitalize' }}>{st.replace('_', ' ')}</span>
                      <span style={{ color: '#0f172a', fontWeight: 600, fontFamily: 'monospace' }}>{count} ({Math.round(pct)}%)</span>
                    </div>
                    <div style={{ height: '5px', background: '#f1f5f9', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: st === 'delivered' ? '#059669' : st === 'in_transit' ? '#2563eb' : '#d97706', borderRadius: '3px' }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '32px', color: '#64748b' }}>
              <Inbox size={20} style={{ margin: '0 auto 6px' }} />
              <p style={{ margin: 0, fontSize: '12px' }}>No order distribution data</p>
            </div>
          )}
        </div>

        {/* Inventory health */}
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '18px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Layers size={15} style={{ color: '#64748b' }} />
            <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a', margin: 0, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Warehouse Inventory Distribution
            </h3>
          </div>

          {loading ? (
            <div style={{ height: '140px', background: '#f8fafc', borderRadius: '6px' }} />
          ) : dashboard?.inventory_health ? (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '14px' }}>
                <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Healthy SKUs</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#059669', fontFamily: 'monospace', marginTop: '2px' }}>
                    {dashboard.inventory_health.healthy}
                  </div>
                </div>
                <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Low Stock</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#d97706', fontFamily: 'monospace', marginTop: '2px' }}>
                    {dashboard.inventory_health.low_stock}
                  </div>
                </div>
                <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Out of Stock</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#dc2626', fontFamily: 'monospace', marginTop: '2px' }}>
                    {dashboard.inventory_health.out_of_stock}
                  </div>
                </div>
              </div>

              <div style={{ height: '6px', background: '#f1f5f9', borderRadius: '3px', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${Math.round(
                      (dashboard.inventory_health.healthy /
                        Math.max(dashboard.inventory_health.total_locations, 1)) * 100
                    )}%`,
                    background: '#059669',
                    borderRadius: '3px',
                  }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b', marginTop: '8px' }}>
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

      {/* Agent Pipeline */}
      <AgentPipeline agents={agents} loading={loading} />

      {/* Recent Orders */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Package size={15} style={{ color: '#64748b' }} />
            <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a', margin: 0, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Recent Commercial Orders
            </h3>
          </div>
          <a
            href="/orders"
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
          </a>
        </div>

        {loading ? (
          <div style={{ height: '160px', background: '#f8fafc', borderRadius: '6px' }} />
        ) : dashboard?.recent_orders?.length ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#64748b', textAlign: 'left', background: '#f8fafc' }}>
                  <th style={{ padding: '8px 12px', fontWeight: 600 }}>ORDER REFERENCE</th>
                  <th style={{ padding: '8px 12px', fontWeight: 600 }}>CLIENT ACCOUNT</th>
                  <th style={{ padding: '8px 12px', fontWeight: 600 }}>STATUS</th>
                  <th style={{ padding: '8px 12px', fontWeight: 600 }}>PRIORITY</th>
                  <th style={{ padding: '8px 12px', fontWeight: 600 }}>COMMERCIAL VALUE</th>
                  <th style={{ padding: '8px 12px', fontWeight: 600 }}>TIMELINE</th>
                  <th style={{ padding: '8px 12px', fontWeight: 600, textAlign: 'right' }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_orders.map((order: RecentOrder) => {
                  const sBadge = statusBadges[order.status] || statusBadges.pending;
                  const pBadge = priorityBadges[order.priority] || priorityBadges.standard;

                  return (
                    <tr key={order.order_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontWeight: 600, color: '#0f172a' }}>
                        {formatOrderId(order.order_id)}
                      </td>
                      <td style={{ padding: '10px 12px', color: '#334155' }}>
                        {getCustomerName(order.customer_id || order.order_id)}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            padding: '2px 7px',
                            borderRadius: '4px',
                            background: sBadge.bg,
                            color: sBadge.text,
                            border: `1px solid ${sBadge.border}`,
                            textTransform: 'capitalize',
                          }}
                        >
                          {order.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: 600,
                            padding: '2px 6px',
                            borderRadius: '3px',
                            background: pBadge.bg,
                            color: pBadge.text,
                            textTransform: 'uppercase',
                          }}
                        >
                          {order.priority}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', fontWeight: 600, color: '#0f172a', fontFamily: 'monospace' }}>
                        {formatCurrency(order.total_amount)}
                      </td>
                      <td style={{ padding: '10px 12px', color: '#64748b' }}>
                        {formatTimeAgo(order.created_at)}
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                        <a
                          href={`/workflows${order.workflow_id ? `?workflow_id=${order.workflow_id}` : ''}`}
                          style={{
                            fontSize: '11px',
                            color: '#2563eb',
                            textDecoration: 'none',
                            fontWeight: 500,
                          }}
                        >
                          Inspect Trace &rarr;
                        </a>
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

