import React from 'react';
import type { DashboardKPIs } from '../../types';
import {
  Package,
  DollarSign,
  Target,
  Cpu,
  Building2,
  AlertTriangle,
  Layers,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';

interface KPICardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ReactNode;
  trend?: { value: number; positive: boolean };
  badgeText?: string;
  isAlert?: boolean;
}

const KPICard: React.FC<KPICardProps> = ({
  label,
  value,
  sub,
  icon,
  trend,
  badgeText,
  isAlert,
}) => (
  <div
    style={{
      background: '#0f172a',
      border: isAlert ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(255, 255, 255, 0.07)',
      borderRadius: '8px',
      padding: '16px 18px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      position: 'relative',
      transition: 'border-color 0.2s ease, transform 0.2s ease',
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
      <div
        style={{
          width: '32px',
          height: '32px',
          borderRadius: '6px',
          background: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: isAlert ? '#f87171' : '#94a3b8',
        }}
      >
        {icon}
      </div>

      {trend && (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '3px',
            fontSize: '11px',
            fontWeight: 600,
            color: trend.positive ? '#34d399' : '#f87171',
            background: trend.positive ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
            padding: '2px 6px',
            borderRadius: '4px',
          }}
        >
          {trend.positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {trend.value}%
        </span>
      )}

      {badgeText && (
        <span
          style={{
            fontSize: '11px',
            fontWeight: 500,
            color: '#94a3b8',
            background: 'rgba(255, 255, 255, 0.04)',
            padding: '2px 6px',
            borderRadius: '4px',
          }}
        >
          {badgeText}
        </span>
      )}
    </div>

    <div>
      <div
        style={{
          fontSize: '22px',
          fontWeight: 700,
          color: '#f8fafc',
          letterSpacing: '-0.02em',
          lineHeight: 1.1,
          fontFamily: 'monospace',
          marginBottom: '4px',
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: '11px',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: '#64748b',
          marginBottom: '2px',
        }}
      >
        {label}
      </div>
      {sub && <div style={{ fontSize: '11px', color: '#94a3b8' }}>{sub}</div>}
    </div>
  </div>
);

interface KPIGridProps {
  kpis: DashboardKPIs | null;
  loading?: boolean;
}

export const KPIGrid: React.FC<KPIGridProps> = ({ kpis, loading }) => {
  if (loading || !kpis) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} style={{ height: '110px', background: '#0f172a', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }} />
        ))}
      </div>
    );
  }

  const revenue = parseFloat(kpis.total_revenue).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });

  const cards: KPICardProps[] = [
    {
      label: 'Commercial Orders',
      value: kpis.total_orders.toLocaleString(),
      sub: `${kpis.delivered_orders} fulfilled deliveries`,
      icon: <Package size={16} />,
    },
    {
      label: 'Gross Revenue',
      value: revenue,
      sub: 'Total contracted order value',
      icon: <DollarSign size={16} />,
    },
    {
      label: 'OTIF Fill Rate',
      value: `${kpis.fill_rate_pct}%`,
      sub: 'Service level target ≥ 98%',
      trend: { value: 2.4, positive: true },
      icon: <Target size={16} />,
    },
    {
      label: 'Agent Swarm',
      value: `${kpis.total_agents} Active`,
      sub: 'Consensus engine online',
      icon: <Cpu size={16} />,
    },
    {
      label: 'Tier-1 Suppliers',
      value: kpis.active_suppliers,
      sub: `Avg reliability score: ${kpis.avg_supplier_reliability}%`,
      icon: <Building2 size={16} />,
    },
    {
      label: 'Critical Stock Alerts',
      value: kpis.low_stock_alerts,
      sub: `${kpis.out_of_stock_alerts} stockouts detected`,
      isAlert: kpis.low_stock_alerts > 0,
      icon: <AlertTriangle size={16} />,
    },
    {
      label: 'SKU Availability',
      value: `${kpis.sku_availability_pct ?? Math.max(0, Math.min(100, Math.round((1 - (kpis.out_of_stock_alerts || 0) / (kpis.total_inventory_locations || 30)) * 100)))}%`,
      sub: 'Network warehouse fill rate',
      icon: <Layers size={16} />,
    },
    {
      label: 'Network Governance',
      value: 'Autonomous',
      sub: 'Neuro-symbolic safeguards',
      badgeText: 'Live',
      icon: <ShieldCheck size={16} />,
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px', marginBottom: '24px' }}>
      {cards.map((card) => (
        <KPICard key={card.label} {...card} />
      ))}
    </div>
  );
};
