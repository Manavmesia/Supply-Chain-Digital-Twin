import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ordersApi } from '../services/api';
import type { Order } from '../types';
import {
  Plus,
  RefreshCw,
  Search,
  ChevronRight,
  X,
  Zap,
  Cpu,
  FileText,
} from 'lucide-react';
import { formatCurrency } from '../utils/formatters';
import { OrderDecisionTrail } from '../components/orders/OrderDecisionTrail';

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  pending:    { label: 'Evaluating', bg: '#fffbeb', text: '#d97706', border: '#fde68a' },
  processing: { label: 'Processing', bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' },
  in_transit: { label: 'In Transit', bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' },
  delivered:  { label: 'Delivered', bg: '#ecfdf5', text: '#059669', border: '#a7f3d0' },
  cancelled:  { label: 'Cancelled', bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
};

const PRIORITY_BADGES: Record<string, { bg: string; text: string }> = {
  critical: { bg: '#fef2f2', text: '#dc2626' },
  high:     { bg: '#fffbeb', text: '#d97706' },
  standard: { bg: '#f1f5f9', text: '#475569' },
  low:      { bg: '#f8fafc', text: '#64748b' },
};

const BASELINE_CUSTOMERS = [
  { id: '50000000-0000-0000-0000-000000000001', name: 'Siemens Global Automations', tier: 'Enterprise' },
  { id: '50000000-0000-0000-0000-000000000002', name: 'Tesla Energy & Storage', tier: 'Enterprise' },
  { id: '50000000-0000-0000-0000-000000000003', name: 'Schneider Electric Grid', tier: 'Enterprise' },
  { id: '50000000-0000-0000-0000-000000000004', name: 'Honeywell Aerospace', tier: 'Standard' },
];

const CATALOG_PRODUCTS = [
  { id: '30000000-0000-0000-0000-000000000001', sku: 'ELEC-001', name: 'Industrial Sensor Module', price: 150.00 },
  { id: '30000000-0000-0000-0000-000000000002', sku: 'ELEC-002', name: 'High-Torque Servo Motor', price: 280.00 },
  { id: '30000000-0000-0000-0000-000000000003', sku: 'ELEC-003', name: 'IoT Gateway Device', price: 1249.99 },
  { id: '30000000-0000-0000-0000-000000000004', sku: 'MECH-001', name: 'Precision Ball Bearing Set', price: 95.00 },
  { id: '30000000-0000-0000-0000-000000000005', sku: 'MECH-002', name: 'Hydraulic Actuator Cylinder', price: 3450.00 },
];

export const OrdersPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const urlOrderId = searchParams.get('order_id') || searchParams.get('id');

  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [drawerTab, setDrawerTab] = useState<'overview' | 'decision-trail'>('overview');
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New order form
  const [formCustomerId, setFormCustomerId] = useState(BASELINE_CUSTOMERS[0].id);
  const [formPriority, setFormPriority] = useState<'low' | 'standard' | 'high' | 'critical'>('standard');
  const [orderItems, setOrderItems] = useState([
    { product_id: CATALOG_PRODUCTS[0].id, quantity: 10 },
  ]);

  const isMountedRef = useRef(true);

  const loadData = useCallback(async (isSilent = false) => {
    try {
      const [listRes, statRes] = await Promise.all([
        ordersApi.list({ limit: 100 }),
        ordersApi.getStats(),
      ]);
      if (isMountedRef.current) {
        setOrders(listRes.items || []);
        setStats(statRes);
      }
    } catch (err) {
      console.error('Failed to load orders:', err);
    } finally {
      if (isMountedRef.current && !isSilent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    loadData();
    const interval = setInterval(() => loadData(true), 12000);
    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
    };
  }, [loadData]);

  useEffect(() => {
    if (urlOrderId && orders.length > 0) {
      const match = orders.find(o => o.order_id === urlOrderId);
      if (match) {
        setSelectedOrder(match);
        if (searchParams.get('tab') === 'decision') {
          setDrawerTab('decision-trail');
        }
      }
    }
  }, [urlOrderId, orders, searchParams]);

  const handleCreateOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await ordersApi.create({
        customer_id: formCustomerId,
        priority: formPriority,
        items: orderItems,
      });
      setShowCreateModal(false);
      setActionMessage(`Commercial Order ${res.order_id} booked! Autonomous decision pipeline initiated (Audit Ref: ${res.workflow_id ? res.workflow_id.slice(0, 8) : 'ACT-' + res.order_id.slice(0, 8)}).`);
      await loadData(true);
    } catch (err: any) {
      setActionMessage(`Order creation failed: ${err.message}`);
    }
  };

  const handleAddItemRow = () => {
    setOrderItems([...orderItems, { product_id: CATALOG_PRODUCTS[0].id, quantity: 5 }]);
  };

  const handleRemoveItemRow = (index: number) => {
    if (orderItems.length > 1) {
      setOrderItems(orderItems.filter((_, i) => i !== index));
    }
  };

  const calculateFormTotal = () => {
    return orderItems.reduce((acc, it) => {
      const prod = CATALOG_PRODUCTS.find((p) => p.id === it.product_id);
      return acc + (prod ? prod.price * it.quantity : 0);
    }, 0);
  };

  const filteredOrders = orders.filter((o) => {
    if (statusFilter !== 'all' && o.status !== statusFilter) return false;
    if (priorityFilter !== 'all' && o.priority !== priorityFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchId = o.order_id.toLowerCase().includes(q);
      const matchCust = (o.customer?.name || '').toLowerCase().includes(q);
      return matchId || matchCust;
    }
    return true;
  });

  return (
    <div className="page-container animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Customer Orders</h1>
          <p className="page-subtitle">
            Manage customer orders, priority allocations, and fulfillment execution.
          </p>
        </div>
        <div className="page-actions">
          <button onClick={() => loadData()} className="btn-secondary">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            <Plus className="w-4 h-4" />
            New Order
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="banner-info">
          <Zap className="w-4 h-4 text-blue-600" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">TOTAL REVENUE</div>
          <div className="stat-value">
            {formatCurrency(parseFloat(stats?.total_revenue || '176900'))}
          </div>
          <div className="stat-sub">Contracted order volume</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">TOTAL ORDERS</div>
          <div className="stat-value" style={{ color: '#2563eb' }}>
            {stats?.total_orders ?? orders.length}
          </div>
          <div className="stat-sub">Customer purchases</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">DELIVERED</div>
          <div className="stat-value" style={{ color: '#059669' }}>
            {stats?.by_status?.delivered ?? 0}
          </div>
          <div className="stat-sub">Fulfilled customer deliveries</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">PROCESSING</div>
          <div className="stat-value" style={{ color: '#d97706' }}>
            {((stats?.by_status?.pending || 0) + (stats?.by_status?.in_transit || 0))}
          </div>
          <div className="stat-sub">Active in pipeline</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-toolbar">
        <div className="filter-group">
          <span className="filter-label">Status:</span>
          {['all', 'pending', 'in_transit', 'delivered'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`filter-pill ${statusFilter === st ? 'active' : ''}`}
            >
              {st === 'all' ? 'All' : st.replace('_', ' ')}
            </button>
          ))}
          <span style={{ margin: '0 4px', color: '#cbd5e1' }}>|</span>
          <span className="filter-label">Priority:</span>
          {['all', 'high', 'standard', 'critical'].map((pr) => (
            <button
              key={pr}
              onClick={() => setPriorityFilter(pr)}
              className={`filter-pill ${priorityFilter === pr ? 'active' : ''}`}
            >
              {pr}
            </button>
          ))}
        </div>

        <div className="search-box">
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search order ID or customer..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
        </div>
      </div>

      {/* Orders Table */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 'var(--radius-lg)', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#64748b', textAlign: 'left', background: '#f8fafc' }}>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>ORDER ID</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>CUSTOMER</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>PRIORITY</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>ORDER VALUE</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>STATUS</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>DECISION AUDIT</th>
              <th style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600 }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map((ord) => {
              const badge = STATUS_CONFIG[ord.status] || STATUS_CONFIG.pending;
              const priBadge = PRIORITY_BADGES[ord.priority] || PRIORITY_BADGES.standard;

              return (
                <tr
                  key={ord.order_id}
                  style={{ borderBottom: '1px solid #f1f5f9', cursor: 'pointer', transition: 'background 0.15s ease' }}
                  onClick={() => {
                    setSelectedOrder(ord);
                    setDrawerTab('overview');
                  }}
                >
                  <td style={{ padding: '14px 16px', fontFamily: 'monospace', fontWeight: 600, color: '#0f172a' }}>
                    {ord.order_id.slice(0, 16)}...
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ color: '#0f172a', fontWeight: 500 }}>
                      {ord.customer?.name || (ord as any).customer_name || 'Enterprise Client'}
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>
                      {ord.customer?.email || 'contact@client.com'}
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        padding: '3px 8px',
                        borderRadius: '9999px',
                        background: priBadge.bg,
                        color: priBadge.text,
                        textTransform: 'uppercase',
                      }}
                    >
                      {ord.priority}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', fontWeight: 600, color: '#059669' }}>
                    {formatCurrency(parseFloat(ord.total_amount))}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        padding: '3px 10px',
                        borderRadius: '9999px',
                        background: badge.bg,
                        color: badge.text,
                        border: `1px solid ${badge.border}`,
                      }}
                    >
                      {badge.label}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    {ord.workflow_id ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedOrder(ord);
                          setDrawerTab('decision-trail');
                        }}
                        title="Inspect Autonomous Decision Audit Trail"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          color: '#2563eb',
                          background: '#eff6ff',
                          border: '1px solid #bfdbfe',
                          borderRadius: '6px',
                          padding: '4px 8px',
                          fontSize: '11px',
                          fontFamily: 'monospace',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <Cpu className="w-3.5 h-3.5 text-blue-600" />
                        <span>{ord.workflow_id.slice(0, 8)}...</span>
                      </button>
                    ) : (
                      <span style={{ color: '#64748b', fontSize: '11px' }}>Direct Log</span>
                    )}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedOrder(ord);
                      }}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#2563eb',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '2px',
                        fontSize: '12px',
                        fontWeight: 500,
                      }}
                    >
                      <span>View</span>
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              );
            })}

            {filteredOrders.length === 0 && (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: '#64748b' }}>
                  No commercial orders found matching filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Order Detail Drawer */}
      {selectedOrder && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(2px)', display: 'flex', justifyContent: 'flex-end', zIndex: 110 }}>
          <div style={{ width: '600px', maxWidth: '100%', background: '#ffffff', height: '100%', padding: '24px', borderLeft: '1px solid #e2e8f0', boxShadow: '-4px 0 24px rgba(0,0,0,0.08)', overflowY: 'auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                  Commercial Order File
                </h2>
                <div style={{ fontSize: '12px', fontFamily: 'monospace', color: '#64748b', marginTop: '2px' }}>
                  {selectedOrder.order_id}
                </div>
              </div>
              <button
                onClick={() => setSelectedOrder(null)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tab selector */}
            <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #e2e8f0', paddingBottom: '10px', marginBottom: '20px' }}>
              <button
                onClick={() => setDrawerTab('overview')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: drawerTab === 'overview' ? 600 : 500,
                  color: drawerTab === 'overview' ? '#2563eb' : '#64748b',
                  background: drawerTab === 'overview' ? '#eff6ff' : 'transparent',
                  border: drawerTab === 'overview' ? '1px solid #bfdbfe' : '1px solid transparent',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Order Summary & Items</span>
              </button>

              <button
                onClick={() => setDrawerTab('decision-trail')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: drawerTab === 'decision-trail' ? 600 : 500,
                  color: drawerTab === 'decision-trail' ? '#2563eb' : '#64748b',
                  background: drawerTab === 'decision-trail' ? '#eff6ff' : 'transparent',
                  border: drawerTab === 'decision-trail' ? '1px solid #bfdbfe' : '1px solid transparent',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                <Cpu className="w-3.5 h-3.5" />
                <span>Autonomous Decision Trail</span>
                {selectedOrder.workflow_id && (
                  <span style={{ fontSize: '10px', background: '#dbeafe', color: '#1d4ed8', padding: '1px 5px', borderRadius: '4px', fontWeight: 700 }}>
                    Active
                  </span>
                )}
              </button>
            </div>

            {drawerTab === 'overview' ? (
              <div>
                <div style={{ background: '#f8fafc', borderRadius: '8px', padding: '16px', marginBottom: '20px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '8px' }}>
                    Customer Account
                  </div>
                  <div style={{ fontSize: '15px', fontWeight: 600, color: '#0f172a' }}>
                    {selectedOrder.customer?.name || (selectedOrder as any).customer_name || 'Enterprise Customer'}
                  </div>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                    {selectedOrder.customer?.email || 'procurement@client.com'}
                  </div>
                </div>

                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', marginBottom: '10px' }}>
                    Line Items ({selectedOrder.items?.length || 1})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {(selectedOrder.items || []).map((item, idx) => (
                      <div
                        key={item.order_item_id || idx}
                        style={{
                          background: '#f8fafc',
                          border: '1px solid #e2e8f0',
                          borderRadius: '6px',
                          padding: '12px',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, color: '#0f172a', fontSize: '13px' }}>
                            {(item as any).product_name || 'Industrial System Component'}
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748b' }}>
                            {(item as any).sku || 'SKU-001'} &bull; Qty: {item.quantity}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontWeight: 600, color: '#059669', fontSize: '13px' }}>
                            {formatCurrency(parseFloat(item.line_total || '0'))}
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748b' }}>
                            @{formatCurrency(parseFloat(item.unit_price || '0'))}/unit
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ background: '#f8fafc', borderRadius: 'var(--radius-md)', padding: '16px', border: '1px solid #e2e8f0', marginBottom: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: '#64748b', fontSize: '13px' }}>Total Commercial Value:</span>
                    <span style={{ fontSize: '18px', fontWeight: 700, color: '#059669' }}>
                      {formatCurrency(parseFloat(selectedOrder.total_amount))}
                    </span>
                  </div>
                </div>

                {selectedOrder.workflow_id ? (
                  <button
                    onClick={() => setDrawerTab('decision-trail')}
                    className="btn-primary"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      width: '100%',
                      padding: '12px',
                      cursor: 'pointer',
                      borderRadius: '6px',
                      border: 'none',
                    }}
                  >
                    <Cpu className="w-4 h-4" />
                    <span>View Multi-Agent Decision & Audit Trail</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                ) : (
                  <div style={{ textAlign: 'center', color: '#64748b', fontSize: '12px', padding: '12px' }}>
                    No automated decision audit trail attached to this manual transaction.
                  </div>
                )}
              </div>
            ) : (
              <div>
                {selectedOrder.workflow_id ? (
                  <OrderDecisionTrail
                    workflowId={selectedOrder.workflow_id}
                    orderId={selectedOrder.order_id}
                    onRefresh={loadData}
                  />
                ) : (
                  <div style={{ padding: '36px 16px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                    No multi-agent execution pipeline recorded for this direct order.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Order Modal */}
      {showCreateModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 'var(--radius-lg)', padding: '24px', width: '560px', maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 16px 0', color: '#0f172a' }}>
              Create Commercial Order (OMS)
            </h2>
            <form onSubmit={handleCreateOrderSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Customer Client</label>
                <select
                  value={formCustomerId}
                  onChange={(e) => setFormCustomerId(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                >
                  {BASELINE_CUSTOMERS.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.tier})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Priority Level</label>
                <select
                  value={formPriority}
                  onChange={(e) => setFormPriority(e.target.value as any)}
                  style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                >
                  <option value="standard">Standard Priority</option>
                  <option value="high">High Priority</option>
                  <option value="critical">Critical (Expedited)</option>
                  <option value="low">Low Priority</option>
                </select>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label style={{ fontSize: '12px', color: '#475569', fontWeight: 500 }}>Order Line Items</label>
                  <button
                    type="button"
                    onClick={handleAddItemRow}
                    style={{ background: 'transparent', border: 'none', color: '#2563eb', fontSize: '12px', cursor: 'pointer', fontWeight: 600 }}
                  >
                    + Add Product
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {orderItems.map((item, idx) => (
                    <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <select
                        value={item.product_id}
                        onChange={(e) => {
                          const newItems = [...orderItems];
                          newItems[idx].product_id = e.target.value;
                          setOrderItems(newItems);
                        }}
                        style={{ flex: 1, padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '12px' }}
                      >
                        {CATALOG_PRODUCTS.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name} ({p.sku}) - ${p.price}
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        min="1"
                        value={item.quantity}
                        onChange={(e) => {
                          const newItems = [...orderItems];
                          newItems[idx].quantity = Math.max(1, parseInt(e.target.value) || 1);
                          setOrderItems(newItems);
                        }}
                        style={{ width: '80px', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '12px' }}
                      />
                      {orderItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveItemRow(idx)}
                          style={{ background: 'transparent', border: 'none', color: '#dc2626', cursor: 'pointer', padding: '4px' }}
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ background: '#f8fafc', padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: '#475569' }}>Calculated Total:</span>
                <span style={{ fontSize: '16px', fontWeight: 700, color: '#059669' }}>
                  {formatCurrency(calculateFormTotal())}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                >
                  Submit Commercial Order
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
