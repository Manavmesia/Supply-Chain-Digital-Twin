import React from 'react';
import type { DashboardKPIs } from '../../types';

interface KPICardProps {
  label: string;
  value: string | number;
  sub?: string;
  color: string;
  icon: string;
  trend?: { value: number; positive: boolean };
  delay?: number;
}

const KPICard: React.FC<KPICardProps> = ({
  label, value, sub, color, icon, trend, delay = 0,
}) => (
  <div
    className="kpi-card animate-fade-in"
    style={{ animationDelay: `${delay}ms`, borderTop: `2px solid ${color}` }}
  >
    <div className="kpi-card-header">
      <span className="kpi-icon" style={{ color }}>{icon}</span>
      {trend && (
        <span
          className={`kpi-trend ${trend.positive ? 'positive' : 'negative'}`}
        >
          {trend.positive ? '↑' : '↓'} {Math.abs(trend.value)}%
        </span>
      )}
    </div>
    <div className="kpi-value" style={{ color }}>
      {value}
    </div>
    <div className="kpi-label">{label}</div>
    {sub && <div className="kpi-sub">{sub}</div>}
  </div>
);

interface KPIGridProps {
  kpis: DashboardKPIs | null;
  loading?: boolean;
}

export const KPIGrid: React.FC<KPIGridProps> = ({ kpis, loading }) => {
  if (loading || !kpis) {
    return (
      <div className="grid-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="kpi-card skeleton" style={{ height: '120px' }} />
        ))}
      </div>
    );
  }

  const revenue = parseFloat(kpis.total_revenue).toLocaleString('en-US', {
    style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2,
  });

  const cards: KPICardProps[] = [
    {
      label: 'Total Orders',
      value: kpis.total_orders.toLocaleString(),
      sub: `${kpis.delivered_orders} delivered`,
      color: '#3b82f6',
      icon: '📦',
      delay: 0,
    },
    {
      label: 'Total Revenue',
      value: revenue,
      sub: 'Gross order value',
      color: '#10b981',
      icon: '💰',
      delay: 60,
    },
    {
      label: 'Fill Rate',
      value: `${kpis.fill_rate_pct}%`,
      sub: 'Target: ≥ 98%',
      color: kpis.fill_rate_pct >= 98 ? '#10b981' : '#f59e0b',
      icon: '🎯',
      trend: { value: 2.4, positive: true },
      delay: 120,
    },
    {
      label: 'Active Agents',
      value: kpis.total_agents,
      sub: 'All 18 operational',
      color: '#8b5cf6',
      icon: '🤖',
      delay: 180,
    },
    {
      label: 'Active Suppliers',
      value: kpis.active_suppliers,
      sub: `Avg. reliability: ${kpis.avg_supplier_reliability}%`,
      color: '#06b6d4',
      icon: '🏭',
      delay: 240,
    },
    {
      label: 'Low Stock Alerts',
      value: kpis.low_stock_alerts,
      sub: `${kpis.out_of_stock_alerts} out of stock`,
      color: kpis.low_stock_alerts > 5 ? '#ef4444' : '#f59e0b',
      icon: '⚠️',
      delay: 300,
    },
    {
      label: 'Inventory Health',
      value: `${kpis.sku_availability_pct ?? Math.max(0, Math.min(100, Math.round((1 - (kpis.out_of_stock_alerts || 0) / (kpis.total_inventory_locations || 30)) * 100)))}%`,
      sub: 'SKU availability',
      color: '#10b981',
      icon: '🏪',
      delay: 360,
    },
    {
      label: 'System Status',
      value: 'Phase 5',
      sub: 'Multi-Agent Coordination',
      color: '#3b82f6',
      icon: '⚡',
      delay: 420,
    },
  ];

  return (
    <div className="grid-4">
      {cards.map((card) => (
        <KPICard key={card.label} {...card} />
      ))}
    </div>
  );
};
