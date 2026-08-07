import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { RefreshCw, Database, Server, MessageSquare } from 'lucide-react';
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

  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      const h = await healthApi.check();
      if (mounted) setHealth(h);
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30_000);
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
            borderColor: health?.status === 'ok' ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)',
            color: health?.status === 'ok' ? '#10b981' : '#ef4444',
          }}
        >
          <span
            className="topbar-system-dot"
            style={{ background: health?.status === 'ok' ? '#10b981' : '#ef4444' }}
          />
          {health?.status === 'ok' ? 'Healthy' : health ? 'Degraded' : 'Checking…'}
        </div>

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
