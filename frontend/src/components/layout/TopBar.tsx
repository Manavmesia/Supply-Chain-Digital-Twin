import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { healthApi } from '../../services/api';

const PAGE_TITLES: Record<string, string> = {
  '/':              'Digital Twin Overview',
  '/orders':        'Customer Orders',
  '/shipments':     'Logistics & Shipments',
  '/procurement':   'Procurement & Suppliers',
  '/inventory':     'Warehouse Inventory',
  '/control-tower': 'Incident Control Tower',
  '/workflows':     'Agent Workflow Engine',
  '/agents':        'Agent Directory',
  '/reports':       'Reports & Analytics',
};

interface TopBarProps {
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({ onRefresh, isLoading }) => {
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] ?? 'Supply Chain Portal';
  const [isHealthy, setIsHealthy] = useState(true);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const res = await healthApi.check();
        if (mounted) setIsHealthy(res.status === 'ok');
      } catch {
        if (mounted) setIsHealthy(false);
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  return (
    <header
      className="topbar"
      style={{
        padding: '0 2rem',
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: '#ffffff',
        borderBottom: '1px solid #e2e8f0',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <h1 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', margin: 0, letterSpacing: '-0.01em' }}>
          {title}
        </h1>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        <span style={{ fontSize: '0.825rem', color: '#64748b' }}>
          {today}
        </span>

        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.78rem',
            padding: '4px 10px',
            borderRadius: '6px',
            background: isHealthy ? '#ecfdf5' : '#fffbeb',
            color: isHealthy ? '#059669' : '#d97706',
            border: `1px solid ${isHealthy ? '#a7f3d0' : '#fde68a'}`,
            fontWeight: 500,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: isHealthy ? '#059669' : '#d97706',
            }}
          />
          {isHealthy ? 'Operational' : 'Degraded'}
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              border: '1px solid #e2e8f0',
              background: '#ffffff',
              color: '#64748b',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
        )}
      </div>
    </header>
  );
};
