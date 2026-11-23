import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  FileText,
  Package,
  ChevronRight,
  Activity,
  ShoppingCart,
  Truck,
  Building2,
  ShieldAlert,
  GitFork,
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/',             label: 'Dashboard',       icon: LayoutDashboard },
  { path: '/workflows',     label: 'Live Visualizer', icon: GitFork },
  { path: '/orders',        label: 'Orders',          icon: ShoppingCart },
  { path: '/shipments',     label: 'Logistics',       icon: Truck },
  { path: '/procurement',   label: 'Procurement',     icon: Building2 },
  { path: '/inventory',     label: 'Inventory',       icon: Package },
  { path: '/control-tower', label: 'Control Tower',   icon: ShieldAlert },
  { path: '/agents',        label: 'Agent Directory', icon: Bot },
  { path: '/reports',       label: 'Reports',         icon: FileText },
];

interface SidebarProps {
  systemOnline: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ systemOnline }) => {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className="sidebar"
      style={{
        width: collapsed ? '68px' : '248px',
        transition: 'width 0.22s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Brand Header */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Activity size={18} color="var(--c-brand-accent)" />
        </div>
        {!collapsed && (
          <div className="sidebar-logo-text">
            <span className="sidebar-logo-title">Atelier Twin</span>
            <span className="sidebar-logo-sub">Enterprise Fashion Platform</span>
          </div>
        )}
        <button
          className="sidebar-collapse-btn"
          onClick={() => setCollapsed(!collapsed)}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronRight
            size={14}
            style={{
              transform: collapsed ? 'rotate(0deg)' : 'rotate(180deg)',
              transition: 'transform 0.2s ease',
            }}
          />
        </button>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ path, label, icon: Icon }) => {
          const isActive = path === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(path);

          return (
            <NavLink
              key={path}
              to={path}
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              title={collapsed ? label : undefined}
            >
              <Icon size={18} />
              {!collapsed && <span className="sidebar-nav-label">{label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Clean System Status in Footer */}
      {!collapsed && (
        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)', padding: '0 var(--space-2)' }}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: systemOnline ? 'var(--c-success)' : 'var(--c-danger)',
                display: 'inline-block',
              }}
            />
            <span>{systemOnline ? 'Telemetry Active' : 'Connecting...'}</span>
          </div>
        </div>
      )}
    </aside>
  );
};
