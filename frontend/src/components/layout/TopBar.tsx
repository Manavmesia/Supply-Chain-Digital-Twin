import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { RefreshCw, Database, Server, MessageSquare, Sun, Moon } from 'lucide-react';
import { healthApi } from '../../services/api';

const PAGE_TITLES: Record<string, string> = {
  '/':              'Executive Digital Twin',
  '/orders':        'Commercial Orders (OMS)',
  '/shipments':     'Transportation & Logistics (TMS)',
  '/procurement':   'Procurement & Suppliers (SRM)',
  '/inventory':     'Warehouse Inventory (WMS)',
  '/control-tower': 'Supply Chain Control Tower',
  '/workflows':     'AI Agent Workflow Engine',
  '/agents':        '18-Agent Consensus Swarm',
  '/reports':       'Executive Synthesis Reports',
};

interface TopBarProps {
  onRefresh?: () => void;
  isLoading?: boolean;
}

interface HealthStatus {
  status: string;
  dependencies: {
    db: string;
    redis: string;
    rabbitmq: string;
  };
}

export const TopBar: React.FC<TopBarProps> = ({ onRefresh, isLoading }) => {
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] ?? 'Supply Chain Digital Twin';
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      const h = await healthApi.check();
      if (mounted) setHealth(h);
    };
    checkHealth();
    const interval = setInterval(checkHealth, 8000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const depStatus = (val: string | undefined) =>
    val === 'connected' ? 'ok' : 'err';

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h2 className="topbar-title">{title}</h2>
        <span style={{ color: '#475569', fontSize: '0.75rem' }}>/</span>
        <span className="topbar-timestamp">
          {new Date().toLocaleDateString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric',
          })}
        </span>
      </div>

      <div className="topbar-right">
        {/* Subtle live sync status */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.7rem',
            color: '#94a3b8',
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            padding: '3px 8px',
            borderRadius: '4px',
            fontWeight: 500,
          }}
          title="Telemetry and agent consensus sync automatically"
        >
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: '#34d399',
            }}
          />
          Live Telemetry
        </div>

        {/* Dependency health indicators */}
        {health && (
          <div className="topbar-health">
            <DepIndicator
              icon={<Database size={11} />}
              label="DB"
              status={depStatus(health.dependencies.db)}
            />
            <DepIndicator
              icon={<Server size={11} />}
              label="Cache"
              status={depStatus(health.dependencies.redis)}
            />
            <DepIndicator
              icon={<MessageSquare size={11} />}
              label="EventBus"
              status={depStatus(health.dependencies.rabbitmq)}
            />
          </div>
        )}

        {/* Overall system badge */}
        <div
          className="topbar-system-badge"
          style={{
            border: `1px solid ${health?.status === 'ok' ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
            color: health?.status === 'ok' ? '#34d399' : '#fbbf24',
          }}
        >
          <span
            className="topbar-system-dot"
            style={{ background: health?.status === 'ok' ? '#10b981' : '#f59e0b' }}
          />
          {health?.status === 'ok' ? 'Operational' : 'Degraded Mode'}
        </div>

        <button
          className="btn btn-ghost btn-sm topbar-theme-btn"
          onClick={toggleTheme}
          title={theme === 'light' ? 'Switch to Dark theme' : 'Switch to Light theme'}
          aria-label="Toggle theme"
          style={{ border: '1px solid rgba(255,255,255,0.06)', borderRadius: '4px', padding: '4px 8px' }}
        >
          {theme === 'light' ? <Moon size={13} /> : <Sun size={13} />}
        </button>

        {onRefresh && (
          <button
            className="btn btn-ghost btn-sm topbar-refresh-btn"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh data"
            style={{ border: '1px solid rgba(255,255,255,0.06)', borderRadius: '4px', padding: '4px 8px' }}
          >
            <RefreshCw
              size={13}
              style={{
                animation: isLoading ? 'spin 0.7s linear infinite' : 'none',
              }}
            />
          </button>
        )}
      </div>
    </header>
  );
};

const DepIndicator: React.FC<{
  icon: React.ReactNode;
  label: string;
  status: 'ok' | 'err';
}> = ({ icon, label, status }) => (
  <div className="dep-indicator">
    {icon}
    <span>{label}</span>
    <span
      className="dep-dot"
      style={{ background: status === 'ok' ? '#10b981' : '#ef4444' }}
    />
  </div>
);
