import React, { useEffect, useState, useCallback, useRef } from 'react';
import { ordersApi } from '../services/api';
import type { Order } from '../types';
import {
  Plus,
  RefreshCw,
  Search,
  ExternalLink,
  ChevronRight,
  X,
  Zap,
} from 'lucide-react';
import { formatCurrency } from '../utils/formatters';
import { Link } from 'react-router-dom';

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  pending:    { label: 'Evaluating', bg: 'rgba(245, 158, 11, 0.08)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.2)' },
  processing: { label: 'Processing', bg: 'rgba(59, 130, 246, 0.08)', text: '#60a5fa', border: 'rgba(59, 130, 246, 0.2)' },
  in_transit: { label: 'In Transit', bg: 'rgba(59, 130, 246, 0.08)', text: '#60a5fa', border: 'rgba(59, 130, 246, 0.2)' },
  delivered:  { label: 'Delivered', bg: 'rgba(16, 185, 129, 0.08)', text: '#34d399', border: 'rgba(16, 185, 129, 0.2)' },
  cancelled:  { label: 'Cancelled', bg: 'rgba(239, 68, 68, 0.08)', text: '#f87171', border: 'rgba(239, 68, 68, 0.2)' },
};

const PRIORITY_BADGES: Record<string, { bg: string; text: string }> = {
  critical: { bg: 'rgba(239, 68, 68, 0.1)', text: '#fca5a5' },
  high:     { bg: 'rgba(245, 158, 11, 0.1)', text: '#fcd34d' },
  standard: { bg: 'rgba(255, 255, 255, 0.04)', text: '#cbd5e1' },
  low:      { bg: 'rgba(255, 255, 255, 0.03)', text: '#94a3b8' },
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
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
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

  const handleCreateOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await ordersApi.create({
        customer_id: formCustomerId,
        priority: formPriority,
        items: orderItems,
      });
      setShowCreateModal(false);
      setActionMessage(`Commercial Order ${res.order_id} created! Autonomous LangGraph workflow kicked off (WF: ${res.workflow_id.slice(0, 8)}).`);
      await loadData(true);
    } catch (err: any) {
      alert(`Order creation failed: ${err.message}`);
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
    <div style={{ padding: '28px', maxWidth: '1440px', margin: '0 auto', color: '#f1f5f9' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>
              Commercial Orders (OMS)
            </h1>
            <span style={{ fontSize: '11px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', padding: '3px 8px', borderRadius: '4px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              Autonomous 18-Agent Fulfillment
            </span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0 0' }}>
            Commercial order intake, autonomous consensus evaluation (ADS-01 to ADS-18), and real-time fulfillment pipelines.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => loadData()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#cbd5e1',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              background: '#2563eb',
              border: 'none',
              borderRadius: '6px',
              color: '#ffffff',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <Plus className="w-4 h-4" />
            Create Commercial Order
          </button>
        </div>
      </div>

      {actionMessage && (
        <div style={{ marginBottom: '20px', padding: '12px 16px', borderRadius: '8px', background: 'rgba(37, 99, 235, 0.15)', border: '1px solid rgba(37, 99, 235, 0.3)', color: '#93c5fd', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap className="w-4 h-4 text-sky-400" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>TOTAL COMMERCIAL REVENUE</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>
            {formatCurrency(parseFloat(stats?.total_revenue || '176900'))}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Across enterprise contracts</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>TOTAL ORDERS PLACED</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#60a5fa' }}>
            {stats?.total_orders ?? orders.length}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Autonomous agent intake</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>FULFILLED / DELIVERED</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#34d399' }}>
            {stats?.by_status?.delivered ?? 0}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Closed customer deliveries</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>IN ACTIVE PIPELINE</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#c084fc' }}>
            {(stats?.by_status?.in_transit ?? 0) + (stats?.by_status?.pending ?? 0)}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Staging, in-transit or evaluating</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 500 }}>Status:</span>
          {['all', 'pending', 'in_transit', 'delivered'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              style={{
                padding: '5px 10px',
                borderRadius: '5px',
                fontSize: '12px',
                border: '1px solid',
                borderColor: statusFilter === st ? '#3b82f6' : '#334155',
                background: statusFilter === st ? 'rgba(59, 130, 246, 0.2)' : '#1e293b',
                color: statusFilter === st ? '#93c5fd' : '#cbd5e1',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {st === 'all' ? 'All' : st.replace('_', ' ')}
            </button>
          ))}
          <span style={{ margin: '0 8px', color: '#334155' }}>|</span>
          <span style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 500 }}>Priority:</span>
          {['all', 'high', 'standard', 'critical'].map((pr) => (
            <button
              key={pr}
              onClick={() => setPriorityFilter(pr)}
              style={{
                padding: '5px 10px',
                borderRadius: '5px',
                fontSize: '12px',
                border: '1px solid',
                borderColor: priorityFilter === pr ? '#3b82f6' : '#334155',
                background: priorityFilter === pr ? 'rgba(59, 130, 246, 0.2)' : '#1e293b',
                color: priorityFilter === pr ? '#93c5fd' : '#cbd5e1',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {pr}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#1e293b', borderRadius: '6px', padding: '6px 12px', border: '1px solid #334155' }}>
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search order ID or customer..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ background: 'transparent', border: 'none', outline: 'none', color: '#f8fafc', fontSize: '12px', width: '220px' }}
          />
        </div>
      </div>

      {/* Orders Table */}
      <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1e293b', color: '#94a3b8', textAlign: 'left', background: '#131e33' }}>
              <th style={{ padding: '12px 16px' }}>ORDER ID</th>
              <th style={{ padding: '12px 16px' }}>CUSTOMER</th>
              <th style={{ padding: '12px 16px' }}>PRIORITY</th>
              <th style={{ padding: '12px 16px' }}>ORDER VALUE</th>
              <th style={{ padding: '12px 16px' }}>STATUS</th>
              <th style={{ padding: '12px 16px' }}>AI WORKFLOW</th>
              <th style={{ padding: '12px 16px', textAlign: 'right' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map((ord) => {
              const badge = STATUS_CONFIG[ord.status] || STATUS_CONFIG.pending;
              const priBadge = PRIORITY_BADGES[ord.priority] || PRIORITY_BADGES.standard;

              return (
                <tr
                  key={ord.order_id}
                  style={{ borderBottom: '1px solid #131e33', cursor: 'pointer', transition: 'background 0.15s ease' }}
                  onClick={() => setSelectedOrder(ord)}
                >
                  <td style={{ padding: '14px 16px', fontFamily: 'monospace', fontWeight: 600, color: '#f8fafc' }}>
                    {ord.order_id.slice(0, 16)}...
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ color: '#f8fafc', fontWeight: 500 }}>
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
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: priBadge.bg,
                        color: priBadge.text,
                        textTransform: 'uppercase',
                      }}
                    >
                      {ord.priority}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', fontWeight: 600, color: '#34d399' }}>
                    {formatCurrency(parseFloat(ord.total_amount))}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: '4px',
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
                      <Link
                        to={`/workflows?workflow_id=${ord.workflow_id}`}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          color: '#60a5fa',
                          textDecoration: 'none',
                          fontSize: '11px',
                          fontFamily: 'monospace',
                        }}
                      >
                        <span>{ord.workflow_id.slice(0, 8)}...</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    ) : (
                      <span style={{ color: '#64748b', fontSize: '11px' }}>Manual</span>
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
                        color: '#60a5fa',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '2px',
                        fontSize: '12px',
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
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'flex-end', zIndex: 110 }}>
          <div style={{ width: '520px', maxWidth: '100%', background: '#0f172a', height: '100%', padding: '24px', borderLeft: '1px solid #1e293b', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                  Order Details
                </h2>
                <div style={{ fontSize: '12px', fontFamily: 'monospace', color: '#94a3b8', marginTop: '2px' }}>
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

            <div style={{ background: '#131e33', borderRadius: '8px', padding: '16px', marginBottom: '20px', border: '1px solid #1e293b' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600, marginBottom: '8px' }}>
                Customer Account
              </div>
              <div style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc' }}>
                {selectedOrder.customer?.name || (selectedOrder as any).customer_name || 'Enterprise Customer'}
              </div>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                {selectedOrder.customer?.email || 'procurement@client.com'}
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', marginBottom: '10px' }}>
                Line Items ({selectedOrder.items?.length || 1})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {(selectedOrder.items || []).map((item, idx) => (
                  <div
                    key={item.order_item_id || idx}
                    style={{
                      background: '#131e33',
                      border: '1px solid #1e293b',
                      borderRadius: '6px',
                      padding: '12px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>
                        {(item as any).product_name || 'Industrial System Component'}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        {(item as any).sku || 'SKU-001'} &bull; Qty: {item.quantity}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 600, color: '#34d399', fontSize: '13px' }}>
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

            <div style={{ background: '#131e33', borderRadius: '8px', padding: '16px', border: '1px solid #1e293b', marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#94a3b8', fontSize: '13px' }}>Total Commercial Value:</span>
                <span style={{ fontSize: '18px', fontWeight: 700, color: '#34d399' }}>
                  {formatCurrency(parseFloat(selectedOrder.total_amount))}
                </span>
              </div>
            </div>

            {selectedOrder.workflow_id && (
              <Link
                to={`/workflows?workflow_id=${selectedOrder.workflow_id}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '12px',
                  background: '#2563eb',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontWeight: 600,
                  textDecoration: 'none',
                  fontSize: '13px',
                }}
              >
                <span>Inspect 18-Agent Blackboard Workflow</span>
                <ExternalLink className="w-4 h-4" />
              </Link>
            )}
          </div>
        </div>
      )}

      {/* Create Order Modal */}
      {showCreateModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', padding: '24px', width: '560px', maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 16px 0', color: '#f8fafc' }}>
              Create Commercial Order (OMS)
            </h2>
            <form onSubmit={handleCreateOrderSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Customer Client</label>
                <select
                  value={formCustomerId}
                  onChange={(e) => setFormCustomerId(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                >
                  {BASELINE_CUSTOMERS.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.tier})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Priority Level</label>
                <select
                  value={formPriority}
                  onChange={(e) => setFormPriority(e.target.value as any)}
                  style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                >
                  <option value="standard">Standard Priority</option>
                  <option value="high">High Priority</option>
                  <option value="critical">Critical (Expedited)</option>
                  <option value="low">Low Priority</option>
                </select>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label style={{ fontSize: '12px', color: '#94a3b8' }}>Order Line Items</label>
                  <button
                    type="button"
                    onClick={handleAddItemRow}
                    style={{ background: 'transparent', border: 'none', color: '#60a5fa', fontSize: '11px', cursor: 'pointer', fontWeight: 600 }}
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
                        style={{ flex: 1, padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '12px' }}
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
                        style={{ width: '80px', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '12px' }}
                      />
                      {orderItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveItemRow(idx)}
                          style={{ background: 'transparent', border: 'none', color: '#f87171', cursor: 'pointer', padding: '4px' }}
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ background: '#131e33', padding: '12px 16px', borderRadius: '6px', border: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>Calculated Total:</span>
                <span style={{ fontSize: '16px', fontWeight: 700, color: '#34d399' }}>
                  {formatCurrency(calculateFormTotal())}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{ padding: '8px 14px', background: 'transparent', border: '1px solid #334155', borderRadius: '5px', color: '#cbd5e1', cursor: 'pointer', fontSize: '13px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: '8px 18px', background: '#2563eb', border: 'none', borderRadius: '5px', color: '#ffffff', fontWeight: 600, cursor: 'pointer', fontSize: '13px' }}
                >
                  Submit Order & Trigger Agents
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
