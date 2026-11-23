import React, { useEffect, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { RefreshCw, LogOut, User } from 'lucide-react';
import { healthApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const PAGE_TITLES: Record<string, string> = {
  '/':              'Digital Twin Overview',
  '/orders':        'Customer Orders',
  '/shipments':     'Logistics & Shipments',
  '/procurement':   'Procurement & Suppliers',
  '/inventory':     'Warehouse Inventory',
  '/control-tower': 'Incident Control Tower',
  '/agents':        'Agent Directory',
  '/reports':       'Reports & Analytics',
};

interface TopBarProps {
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({ onRefresh, isLoading }) => {
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();
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
    <header className="topbar">
      <div className="topbar-left">
        <h1 className="topbar-title">
          {title}
        </h1>
      </div>

      <div className="topbar-right">
        <span className="topbar-timestamp">
          {today}
        </span>

        <div
          className="topbar-system-badge"
          style={{
            background: isHealthy ? 'var(--c-success-bg)' : 'var(--c-warning-bg)',
            color: isHealthy ? 'var(--c-success)' : 'var(--c-warning)',
            border: `1px solid ${isHealthy ? 'var(--c-success-border)' : 'var(--c-warning-border)'}`,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: isHealthy ? 'var(--c-success)' : 'var(--c-warning)',
            }}
          />
          {isHealthy ? 'Operational' : 'Degraded'}
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh"
            className="btn-secondary btn-sm"
            style={{ width: '34px', padding: 0 }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
        )}

        {isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', borderLeft: '1px solid var(--c-border)', paddingLeft: 'var(--space-3)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: 'var(--text-xs)',
              color: 'var(--c-text-primary)',
              background: 'var(--c-bg-subtle)',
              border: '1px solid var(--c-border)',
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
            }}>
              <User size={13} style={{ color: 'var(--c-text-muted)' }} />
              <span><strong>{user.username}</strong> ({user.role})</span>
            </div>
            <button
              onClick={logout}
              title="Sign Out"
              className="btn-danger btn-sm"
              style={{ width: '34px', padding: 0 }}
            >
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            className="btn-primary btn-sm"
          >
            Sign In
          </Link>
        )}
      </div>
    </header>
  );
};
