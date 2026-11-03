import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { RefreshCw, Database, Server, MessageSquare, Sun, Moon } from 'lucide-react';
import { healthApi } from '../../services/api';

const PAGE_TITLES: Record<string, string> = {
  '/':          'Executive Dashboard',
  '/workflows': 'Workflow Management',
  '/agents':    'Agent Control Centre',
  '/inventory': 'Inventory Intelligence',
  '/reports':   'Reports & Analytics',
  '/simulate':  'What-If Simulator',
  '/events':    'Event Bus Monitor',
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
  const title = PAGE_TITLES[location.pathname] ?? 'AI Supply Chain Digital Twin';
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'light';
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
        <span className="topbar-timestamp">
          {new Date().toLocaleDateString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric',
          })}
        </span>
      </div>

      <div className="topbar-right">
        {/* Live sync pulse badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.72rem',
            color: '#10b981',
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            padding: '2px 8px',
            borderRadius: '12px',
          }}
          title="All screens automatically sync data in real time"
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: '#10b981',
              boxShadow: '0 0 6px #10b981',
            }}
          />
          Live Real-Time Sync
        </div>
        {/* Dependency health indicators */}
        {health && (
          <div className="topbar-health">
            <DepIndicator
              icon={<Database size={12} />}
              label="DB"
              status={depStatus(health.dependencies.db)}
            />
            <DepIndicator
              icon={<Server size={12} />}
              label="Redis"
              status={depStatus(health.dependencies.redis)}
            />
            <DepIndicator
              icon={<MessageSquare size={12} />}
              label="MQ"
              status={depStatus(health.dependencies.rabbitmq)}
            />
          </div>
        )}

        {/* Overall system badge */}
        <div
          className="topbar-system-badge"
          style={{
            border: `1px solid ${health?.status === 'ok' ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)'}`,
            color: health?.status === 'ok' ? '#10b981' : '#ef4444',
          }}
        >
          <span
            className="topbar-system-dot"
            style={{ background: health?.status === 'ok' ? '#10b981' : '#ef4444' }}
          />
          {health?.status === 'ok' ? 'Healthy' : health ? 'Degraded' : 'Checking…'}
        </div>

        <button
          className="btn btn-ghost btn-sm topbar-theme-btn"
          onClick={toggleTheme}
          title={theme === 'light' ? 'Switch to Dark theme' : 'Switch to Light theme'}
          aria-label="Toggle theme"
        >
          {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
          <span style={{ fontSize: '0.75rem', fontWeight: 500 }}>
            {theme === 'light' ? 'Light' : 'Dark'}
          </span>
        </button>

        {onRefresh && (
          <button
            className="btn btn-ghost btn-sm topbar-refresh-btn"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh data"
          >
            <RefreshCw
              size={14}
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
