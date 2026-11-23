import React, { useEffect, useState, useCallback, useRef } from 'react';
import { procurementApi } from '../services/api';
import type { ProcurementPO, ProcurementStats, SupplierScorecard } from '../types';
import {
  Building2,
  Package,
  CheckCircle2,
  Plus,
  RefreshCw,
  Search,
  ArrowDownLeft,
} from 'lucide-react';
import { formatCurrency, CATALOG_PRODUCTS } from '../utils/formatters';

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  in_transit: { label: 'In Transit', bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe' },
  received:   { label: 'Received', bg: '#ecfdf5', text: '#059669', border: '#a7f3d0' },
  draft:      { label: 'Draft', bg: '#f8fafc', text: '#64748b', border: '#e2e8f0' },
  cancelled:  { label: 'Cancelled', bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
};

export const ProcurementPage: React.FC = () => {
  const [orders, setOrders] = useState<ProcurementPO[]>([]);
  const [suppliers, setSuppliers] = useState<SupplierScorecard[]>([]);
  const [stats, setStats] = useState<ProcurementStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [receivingId, setReceivingId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New PO form states
  const [selectedSupplierId, setSelectedSupplierId] = useState('sup00000-0000-0000-0000-000000000001');
  const [selectedProductId, setSelectedProductId] = useState('30000000-0000-0000-0000-000000000001');
  const [selectedWarehouseId, setSelectedWarehouseId] = useState('10000000-0000-0000-0000-000000000001');
  const [poQty, setPoQty] = useState(250);
  const [poUnitCost, setPoUnitCost] = useState(115.0);

  const isMountedRef = useRef(true);

  const loadData = useCallback(async (isSilent = false) => {
    try {
      const [ordRes, supRes, statRes] = await Promise.all([
        procurementApi.listOrders({ limit: 100 }),
        procurementApi.getSuppliers(),
        procurementApi.getStats(),
      ]);
      if (isMountedRef.current) {
        setOrders(ordRes.items || []);
        const sups = supRes.items || [];
        setSuppliers(sups);
        setSelectedSupplierId((prev) => {
          if (sups.some((s: SupplierScorecard) => s.supplier_id === prev)) return prev;
          return sups[0]?.supplier_id || prev;
        });
        setStats(statRes);
      }
    } catch (err) {
      console.error('Failed to load procurement data:', err);
    } finally {
      if (isMountedRef.current && !isSilent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    loadData();
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadData(true);
      }
    }, 3500);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        loadData(true);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [loadData]);

  const handleReceiveStock = async (po: ProcurementPO) => {
    setReceivingId(po.po_id);
    setActionMessage(null);
    try {
      const res = await procurementApi.receiveOrder(po.po_id);
      setActionMessage(`Stock received! ${res.details?.quantity_replenished ?? po.quantity} units replenished into warehouse.`);
      await loadData(true);
    } catch (err: any) {
      setActionMessage(`Receipt failed: ${err.message}`);
    } finally {
      setReceivingId(null);
    }
  };

  const handleCreatePoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const matchedSupplier = suppliers.find((s) => s.supplier_id === selectedSupplierId);
      await procurementApi.createOrder({
        supplier_id: selectedSupplierId,
        supplier_name: matchedSupplier?.name,
        product_id: selectedProductId,
        warehouse_id: selectedWarehouseId,
        quantity: poQty,
        unit_cost: poUnitCost,
      });
      setShowCreateModal(false);
      setActionMessage(`Purchase order successfully issued to ${matchedSupplier?.name || 'supplier'}! Replenishment consignment dispatched.`);
      await loadData(true);
    } catch (err: any) {
      setActionMessage(`PO creation failed: ${err.message}`);
    }
  };

  const filteredOrders = orders.filter((o) => {
    if (statusFilter !== 'all' && o.status !== statusFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        o.po_id.toLowerCase().includes(q) ||
        o.supplier_name.toLowerCase().includes(q) ||
        o.product_name.toLowerCase().includes(q) ||
        o.sku.toLowerCase().includes(q) ||
        o.warehouse_name.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="page-container animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Procurement & Suppliers</h1>
          <p className="page-subtitle">
            Purchase orders, supplier scorecards, and warehouse stock replenishment.
          </p>
        </div>
        <div className="page-actions">
          <button onClick={() => loadData()} className="btn-secondary">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            <Plus className="w-4 h-4" />
            Issue Purchase Order
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="banner-info" style={{ background: '#ecfdf5', borderColor: '#a7f3d0', color: '#065f46' }}>
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">INBOUND SPEND</div>
          <div className="stat-value">
            {formatCurrency(stats?.total_spend ?? 0)}
          </div>
          <div className="stat-sub">{stats?.total_po_count ?? orders.length} orders issued</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">IN TRANSIT</div>
          <div className="stat-value" style={{ color: '#2563eb' }}>
            {formatCurrency(stats?.in_transit_spend ?? 0)}
          </div>
          <div className="stat-sub">{stats?.in_transit_count ?? 0} active consignments</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">RECEIVED</div>
          <div className="stat-value" style={{ color: '#059669' }}>
            {stats?.received_count ?? 0}
          </div>
          <div className="stat-sub">Added to warehouse inventory</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">SUPPLIERS</div>
          <div className="stat-value" style={{ color: '#7c3aed' }}>
            {suppliers.length}
          </div>
          <div className="stat-sub">Active supply partners</div>
        </div>
      </div>

      {/* Supplier Scorecards Section */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Building2 className="w-4 h-4 text-emerald-600" />
            <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 600, margin: 0, color: 'var(--c-text-primary)', letterSpacing: 'var(--track-snug)' }}>
              Tier-1 Supplier Scorecard & Resilience Ranking
            </h2>
          </div>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)' }}>Automated Supplier Risk & Resilience Auditing</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
          {suppliers.map((s) => {
            const riskColor = s.risk_tier === 'low' ? 'var(--c-success)' : s.risk_tier === 'medium' ? 'var(--c-warning)' : 'var(--c-danger)';
            const riskBg = s.risk_tier === 'low' ? 'var(--c-success-bg)' : s.risk_tier === 'medium' ? 'var(--c-warning-bg)' : 'var(--c-danger-bg)';
            const riskBorder = s.risk_tier === 'low' ? 'var(--c-success-border)' : s.risk_tier === 'medium' ? 'var(--c-warning-border)' : 'var(--c-danger-border)';

            return (
              <div
                key={s.supplier_id}
                style={{
                  background: 'var(--c-bg-subtle)',
                  border: '1px solid var(--c-border)',
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--space-4)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 'var(--text-base)', color: 'var(--c-text-primary)' }}>{s.name}</div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)' }}>{s.country} &bull; {s.lead_time_days}d lead time</div>
                  </div>
                  <span
                    style={{
                      fontSize: 'var(--text-xs)',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-full)',
                      background: riskBg,
                      color: riskColor,
                      border: `1px solid ${riskBorder}`,
                      textTransform: 'uppercase',
                      letterSpacing: 'var(--track-wide)',
                    }}
                  >
                    {s.risk_tier}
                  </span>
                </div>

                <div style={{ marginTop: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)', marginBottom: '4px' }}>
                    <span>Reliability</span>
                    <strong style={{ color: 'var(--c-text-primary)' }}>{s.reliability_score}%</strong>
                  </div>
                  <div style={{ height: '6px', background: 'var(--c-border)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${s.reliability_score}%`, background: riskColor, borderRadius: 'var(--radius-full)' }} />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px', fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)' }}>
                  <span>Rating: {s.rating}</span>
                  <span>Open POs: {s.open_purchase_orders}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Inbound Purchase Orders Section */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Package className="w-4 h-4 text-emerald-600" />
            <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 600, margin: 0, color: 'var(--c-text-primary)', letterSpacing: 'var(--track-snug)' }}>
              Inbound Replenishment Consignments
            </h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {['all', 'in_transit', 'received', 'draft'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`filter-pill ${statusFilter === st ? 'active' : ''}`}
                >
                  {st === 'all' ? 'All' : st.replace('_', ' ')}
                </button>
              ))}
            </div>

            <div className="search-box">
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search PO, supplier, SKU..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="search-input"
                style={{ width: '180px' }}
              />
            </div>
          </div>
        </div>

        {/* PO Table */}
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>PO NUMBER</th>
                <th>SUPPLIER</th>
                <th>PRODUCT & SKU</th>
                <th>DESTINATION WAREHOUSE</th>
                <th>QUANTITY</th>
                <th>TOTAL VALUE</th>
                <th>STATUS</th>
                <th style={{ textAlign: 'right' }}>DOCK ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((po) => {
                const badge = STATUS_CONFIG[po.status] || STATUS_CONFIG.in_transit;
                const canReceive = po.status === 'in_transit' || po.status === 'draft';

                return (
                  <tr key={po.po_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--c-text-primary)' }}>
                      {po.po_id.slice(0, 16)}...
                    </td>
                    <td>{po.supplier_name}</td>
                    <td>
                      <div style={{ color: 'var(--c-text-primary)', fontWeight: 600 }}>{po.product_name}</div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)', fontFamily: 'var(--font-mono)' }}>{po.sku}</div>
                    </td>
                    <td style={{ color: 'var(--c-text-muted)' }}>{po.warehouse_name}</td>
                    <td style={{ color: 'var(--c-text-primary)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{po.quantity.toLocaleString()} units</td>
                    <td style={{ color: 'var(--c-success)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{formatCurrency(po.total_cost)}</td>
                    <td>
                      <span
                        style={{
                          fontSize: 'var(--text-xs)',
                          fontWeight: 600,
                          padding: '3px 10px',
                          borderRadius: 'var(--radius-full)',
                          background: badge.bg,
                          color: badge.text,
                          border: `1px solid ${badge.border}`,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: badge.text }} />
                        {badge.label}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {canReceive ? (
                        <button
                          onClick={() => handleReceiveStock(po)}
                          disabled={receivingId === po.po_id}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '5px 12px',
                            background: '#ecfdf5',
                            border: '1px solid #a7f3d0',
                            borderRadius: '4px',
                            color: '#059669',
                            fontWeight: 600,
                            cursor: 'pointer',
                            fontSize: '11px',
                          }}
                        >
                          <ArrowDownLeft className="w-3.5 h-3.5" />
                          {receivingId === po.po_id ? 'Receiving...' : 'Receive'}
                        </button>
                      ) : (
                        <span style={{ color: '#94a3b8', fontSize: '11px' }}>Received</span>
                      )}
                    </td>
                  </tr>
                );
              })}

              {filteredOrders.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '36px', color: '#64748b' }}>
                    No purchase orders match current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create PO Modal */}
      {showCreateModal && (
        <div
          onClick={() => setShowCreateModal(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 'var(--radius-lg)', padding: '24px', width: '500px', maxWidth: '90%', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}
          >
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 16px 0', color: '#0f172a' }}>
              Issue Purchase Order
            </h2>
            <form onSubmit={handleCreatePoSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Supplier</label>
                <select
                  value={selectedSupplierId}
                  onChange={(e) => setSelectedSupplierId(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                >
                  {suppliers.map((s) => (
                    <option key={s.supplier_id} value={s.supplier_id}>
                      {s.name} ({s.country} — {s.reliability_score}% Rel)
                    </option>
                  ))}
                  {suppliers.length === 0 && (
                    <option value="33333333-0000-0000-0000-000000000001">Apex Microelectronics Inc. (Japan — 96.5% Rel)</option>
                  )}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Component / Product</label>
                <select
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                >
                  {CATALOG_PRODUCTS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.sku})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Destination Hub</label>
                <select
                  value={selectedWarehouseId}
                  onChange={(e) => setSelectedWarehouseId(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                >
                  <option value="10000000-0000-0000-0000-000000000001">Newark Distribution Center (US)</option>
                  <option value="10000000-0000-0000-0000-000000000002">Birmingham Fulfilment Hub (GB)</option>
                  <option value="10000000-0000-0000-0000-000000000003">Frankfurt Logistics Centre (DE)</option>
                  <option value="22222222-0000-0000-0000-000000000001">Pacific Northwest MegaHub (Seattle)</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Units to Procure</label>
                  <input
                    type="number"
                    value={poQty}
                    onChange={(e) => setPoQty(Math.max(1, parseInt(e.target.value) || 1))}
                    style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Unit Contract Cost ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={poUnitCost}
                    onChange={(e) => setPoUnitCost(Math.max(0.1, parseFloat(e.target.value) || 1))}
                    style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                    required
                  />
                </div>
              </div>

              <div style={{ background: '#f8fafc', padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: '#475569' }}>Total PO Financial Commitment:</span>
                <span style={{ fontSize: '16px', fontWeight: 700, color: '#059669' }}>{formatCurrency(poQty * poUnitCost)}</span>
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
                  style={{ background: '#059669' }}
                >
                  Issue & Dispatch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
