import React from 'react';
import { Link } from 'react-router-dom';
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
  link?: string;
}

const KPICard: React.FC<KPICardProps> = ({
  label,
  value,
  sub,
  icon,
  trend,
  badgeText,
  isAlert,
  link,
}) => {
  const content = (
  <div
    style={{
      background: 'var(--c-bg-card)',
      border: isAlert ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid var(--c-border)',
      borderRadius: 'var(--radius-lg)',
      padding: '18px 20px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      position: 'relative',
      boxShadow: 'var(--shadow-card)',
      transition: 'border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease',
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
      <div
        style={{
          width: '34px',
          height: '34px',
          borderRadius: 'var(--radius-md)',
          background: isAlert ? 'rgba(239, 68, 68, 0.08)' : 'var(--c-bg-subtle)',
          border: '1px solid var(--c-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: isAlert ? '#dc2626' : 'var(--c-text-secondary)',
        }}
      >
        {icon}
      </div>

      {trend && (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            color: trend.positive ? 'var(--c-success)' : 'var(--c-danger)',
            background: trend.positive ? 'var(--c-success-bg)' : 'var(--c-danger-bg)',
            border: `1px solid ${trend.positive ? 'var(--c-success-border)' : 'var(--c-danger-border)'}`,
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
          }}
        >
          {trend.positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {trend.value}%
        </span>
      )}

      {badgeText && (
        <span
          style={{
            fontSize: 'var(--text-xs)',
            fontWeight: 500,
            color: 'var(--c-text-muted)',
            background: 'var(--c-bg-subtle)',
            border: '1px solid var(--c-border)',
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
          }}
        >
          {badgeText}
        </span>
      )}
    </div>

    <div>
      <div
        style={{
          fontSize: 'var(--text-2xl)',
          fontWeight: 700,
          color: 'var(--c-text-primary)',
          letterSpacing: 'var(--track-tight)',
          lineHeight: 1.15,
          fontFamily: 'var(--font-mono)',
          fontVariantNumeric: 'tabular-nums',
          marginBottom: '4px',
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: 'var(--text-xs)',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: 'var(--track-wide)',
          color: 'var(--c-text-muted)',
          marginBottom: '2px',
        }}
      >
        {label}
      </div>
      {sub && <div style={{ fontSize: 'var(--text-xs)', color: 'var(--c-text-secondary)' }}>{sub}</div>}
    </div>
  </div>
  );

  if (link) {
    return (
      <Link to={link} style={{ textDecoration: 'none', display: 'block', color: 'inherit' }}>
        {content}
      </Link>
    );
  }

  return content;
};

interface KPIGridProps {
  kpis: DashboardKPIs | null;
  loading?: boolean;
}

export const KPIGrid: React.FC<KPIGridProps> = ({ kpis, loading }) => {
  if (loading || !kpis) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} style={{ height: '114px', background: 'var(--c-bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--c-border)' }} />
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
      label: 'Orders',
      value: kpis.total_orders.toLocaleString(),
      sub: `${kpis.delivered_orders} delivered`,
      icon: <Package size={16} />,
    },
    {
      label: 'Revenue',
      value: revenue,
      sub: 'Contracted value',
      icon: <DollarSign size={16} />,
    },
    {
      label: 'Fill Rate',
      value: `${kpis.fill_rate_pct}%`,
      sub: 'Target: ≥ 98%',
      icon: <Target size={16} />,
    },
    {
      label: 'Agents',
      value: kpis.total_agents,
      sub: 'Supervised',
      icon: <Cpu size={16} />,
      link: '/agents',
      badgeText: 'View',
    },
    {
      label: 'Suppliers',
      value: kpis.active_suppliers,
      sub: `Reliability: ${kpis.avg_supplier_reliability}%`,
      icon: <Building2 size={16} />,
    },
    {
      label: 'Stock Alerts',
      value: kpis.low_stock_alerts,
      sub: `${kpis.out_of_stock_alerts} stockouts`,
      isAlert: kpis.low_stock_alerts > 0,
      icon: <AlertTriangle size={16} />,
    },
    {
      label: 'Availability',
      value: `${kpis.sku_availability_pct ?? Math.max(0, Math.min(100, Math.round((1 - (kpis.out_of_stock_alerts || 0) / (kpis.total_inventory_locations || 30)) * 100)))}%`,
      sub: 'Warehouse buffer',
      icon: <Layers size={16} />,
    },
    {
      label: 'System',
      value: 'Optimal',
      sub: 'Operational',
      badgeText: 'Live',
      icon: <ShieldCheck size={16} />,
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
      {cards.map((card) => (
        <KPICard key={card.label} {...card} />
      ))}
    </div>
  );
};
