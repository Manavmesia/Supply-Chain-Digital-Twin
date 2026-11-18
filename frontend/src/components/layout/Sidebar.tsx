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
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/',             label: 'Dashboard',       icon: LayoutDashboard },
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
        width: collapsed ? '68px' : '240px',
        transition: 'width 0.2s ease',
      }}
    >
      {/* Brand Header */}
      <div className="sidebar-logo" style={{ padding: '1.25rem 1rem' }}>
        <div className="sidebar-logo-icon">
          <Activity size={18} color="#2563eb" />
        </div>
        {!collapsed && (
          <div className="sidebar-logo-text">
            <span className="sidebar-logo-title">Digital Twin</span>
            <span className="sidebar-logo-sub">Supply Chain Portal</span>
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
      <nav className="sidebar-nav" style={{ padding: '1rem 0.75rem', gap: '4px' }}>
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
              style={{
                padding: '0.65rem 0.85rem',
                fontSize: '0.85rem',
                borderRadius: '8px',
                marginBottom: '2px',
              }}
            >
              <Icon size={18} />
              {!collapsed && <span className="sidebar-nav-label">{label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Clean System Status in Footer */}
      {!collapsed && (
        <div style={{ marginTop: 'auto', padding: '1rem', borderTop: '1px solid #f1f5f9' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: '#64748b' }}>
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: systemOnline ? '#10b981' : '#ef4444',
                display: 'inline-block',
              }}
            />
            <span>{systemOnline ? 'System Operational' : 'Connecting...'}</span>
          </div>
        </div>
      )}
    </aside>
  );
};
