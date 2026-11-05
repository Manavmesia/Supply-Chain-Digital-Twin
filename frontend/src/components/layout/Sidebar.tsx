import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Workflow, Bot, FileText,
  Package, ChevronRight, Activity, Settings, LogOut,
  ShoppingCart, Truck, Building2, ShieldAlert,
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/',              label: 'Dashboard',         icon: LayoutDashboard, badge: null },
  { path: '/orders',         label: 'Orders (OMS)',      icon: ShoppingCart,    badge: null },
  { path: '/shipments',      label: 'Logistics (TMS)',   icon: Truck,           badge: null },
  { path: '/procurement',    label: 'Procurement (SRM)', icon: Building2,       badge: null },
  { path: '/inventory',      label: 'Inventory (WMS)',   icon: Package,         badge: null },
  { path: '/control-tower',  label: 'Control Tower',     icon: ShieldAlert,     badge: 'Live' },
  { path: '/workflows',      label: 'AI Agent Engine',   icon: Workflow,        badge: null },
  { path: '/agents',         label: 'Agent Roster',      icon: Bot,             badge: '18' },
  { path: '/reports',        label: 'Executive Reports', icon: FileText,        badge: null },
];

const LAYER_COLORS: Record<string, string> = {
  operational:  '#10b981',
  business:     '#f59e0b',
  coordination: '#8b5cf6',
};

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
        width: collapsed ? '64px' : '260px',
        transition: 'width 0.25s ease',
      }}
    >
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Activity size={20} color="#3b82f6" />
        </div>
        {!collapsed && (
          <div className="sidebar-logo-text">
            <span className="sidebar-logo-title">Digital Twin</span>
            <span className="sidebar-logo-sub">Supply Chain AI</span>
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

      {/* System status */}
      <div className="sidebar-status">
        <div
          className="sidebar-status-dot"
          style={{ background: systemOnline ? '#10b981' : '#ef4444' }}
        />
        {!collapsed && (
          <span className="sidebar-status-text">
            {systemOnline ? 'System Online' : 'System Offline'}
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {!collapsed && <p className="sidebar-section-label">Navigation</p>}
        {NAV_ITEMS.map(({ path, label, icon: Icon, badge }) => {
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
              {!collapsed && badge && (
                <span className="sidebar-nav-badge">{badge}</span>
              )}
              {isActive && !collapsed && (
                <ChevronRight size={12} className="sidebar-nav-arrow" />
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Agent layers legend */}
      {!collapsed && (
        <div className="sidebar-legend">
          <p className="sidebar-section-label">Agent Layers</p>
          {Object.entries(LAYER_COLORS).map(([layer, color]) => (
            <div key={layer} className="sidebar-legend-item">
              <span
                className="sidebar-legend-dot"
                style={{ background: color }}
              />
              <span className="sidebar-legend-label">
                {layer.charAt(0).toUpperCase() + layer.slice(1)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="sidebar-footer">
        <button className="sidebar-footer-btn" title="Settings">
          <Settings size={16} />
          {!collapsed && <span>Settings</span>}
        </button>
        <button
          className="sidebar-footer-btn danger"
          title="Logout"
          onClick={() => localStorage.removeItem('access_token')}
        >
          <LogOut size={16} />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
};
