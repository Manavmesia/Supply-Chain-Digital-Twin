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
import { formatCurrency } from '../utils/formatters';

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  in_transit: { label: 'In Transit', bg: 'rgba(59, 130, 246, 0.08)', text: '#60a5fa', border: 'rgba(59, 130, 246, 0.2)' },
  received:   { label: 'Received (Stock Added)', bg: 'rgba(16, 185, 129, 0.08)', text: '#34d399', border: 'rgba(16, 185, 129, 0.2)' },
  draft:      { label: 'Drafted', bg: 'rgba(255, 255, 255, 0.04)', text: '#94a3b8', border: 'rgba(255, 255, 255, 0.08)' },
  cancelled:  { label: 'Cancelled', bg: 'rgba(239, 68, 68, 0.08)', text: '#f87171', border: 'rgba(239, 68, 68, 0.2)' },
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
        setSuppliers(supRes.items || []);
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
    const interval = setInterval(() => loadData(true), 12000);
    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
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
      await procurementApi.createOrder({
        supplier_id: selectedSupplierId,
        product_id: selectedProductId,
        warehouse_id: selectedWarehouseId,
        quantity: poQty,
        unit_cost: poUnitCost,
      });
      setShowCreateModal(false);
      setActionMessage(`Purchase order successfully issued! Replenishment consignment dispatched.`);
      await loadData(true);
    } catch (err: any) {
      alert(`PO creation failed: ${err.message}`);
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
    <div style={{ padding: '28px', maxWidth: '1440px', margin: '0 auto', color: '#f1f5f9' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>
              Procurement & Supplier Inbound (SRM)
            </h1>
            <span style={{ fontSize: '11px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '3px 8px', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              Live Warehouse Dock Loop
            </span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0 0' }}>
            Inbound purchase orders, automated supplier scorecards (ADS-05/12), and 1-click warehouse dock stock replenishment.
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
              background: '#059669',
              border: 'none',
              borderRadius: '6px',
              color: '#ffffff',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <Plus className="w-4 h-4" />
            Issue Purchase Order
          </button>
        </div>
      </div>

      {actionMessage && (
        <div style={{ marginBottom: '20px', padding: '12px 16px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#6ee7b7', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>TOTAL INBOUND SPEND</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>
            {formatCurrency(stats?.total_spend ?? 0)}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>{stats?.total_po_count ?? orders.length} procurement orders issued</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>IN-TRANSIT REPLENISHMENT</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#60a5fa' }}>
            {formatCurrency(stats?.in_transit_spend ?? 0)}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>{stats?.in_transit_count ?? 0} consignments en route</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>RECEIVED AT DOCK</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#34d399' }}>
            {stats?.received_count ?? 0}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Directly added to warehouse stock</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>ACTIVE TIER-1 SUPPLIERS</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#a78bfa' }}>
            {suppliers.length}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Global supply network scorecards</div>
        </div>
      </div>

      {/* Supplier Scorecards Section */}
      <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '18px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Building2 className="w-4 h-4 text-emerald-400" />
            <h2 style={{ fontSize: '15px', fontWeight: 600, margin: 0, color: '#f8fafc' }}>
              Tier-1 Supplier Scorecard & Resilience Ranking
            </h2>
          </div>
          <span style={{ fontSize: '12px', color: '#64748b' }}>Audited by ADS-05 & ADS-10 Risk Engine</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
          {suppliers.map((s) => {
            const riskColor = s.risk_tier === 'low' ? '#34d399' : s.risk_tier === 'medium' ? '#fbbf24' : '#f87171';
            return (
              <div
                key={s.supplier_id}
                style={{
                  background: '#131e33',
                  border: '1px solid #1e293b',
                  borderRadius: '6px',
                  padding: '14px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '13px', color: '#f8fafc' }}>{s.name}</div>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Country: {s.country} &bull; Lead Time: {s.lead_time_days}d</div>
                  </div>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: 'rgba(255,255,255,0.05)',
                      color: riskColor,
                      border: `1px solid ${riskColor}40`,
                      textTransform: 'uppercase',
                    }}
                  >
                    {s.risk_tier} Risk
                  </span>
                </div>

                <div style={{ marginTop: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
                    <span>Reliability Score</span>
                    <strong style={{ color: '#f8fafc' }}>{s.reliability_score}%</strong>
                  </div>
                  <div style={{ height: '5px', background: '#1e293b', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${s.reliability_score}%`, background: riskColor, borderRadius: '3px' }} />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', fontSize: '11px', color: '#64748b' }}>
                  <span>Rating: {s.rating} / 5.0</span>
                  <span>Open POs: {s.open_purchase_orders}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Inbound Purchase Orders Section */}
      <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Package className="w-4 h-4 text-sky-400" />
            <h2 style={{ fontSize: '15px', fontWeight: 600, margin: 0, color: '#f8fafc' }}>
              Inbound Replenishment Consignments
            </h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {['all', 'in_transit', 'received', 'draft'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    border: '1px solid',
                    borderColor: statusFilter === st ? '#10b981' : '#334155',
                    background: statusFilter === st ? 'rgba(16, 185, 129, 0.2)' : '#1e293b',
                    color: statusFilter === st ? '#6ee7b7' : '#cbd5e1',
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                  }}
                >
                  {st === 'all' ? 'All' : st.replace('_', ' ')}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#1e293b', borderRadius: '6px', padding: '4px 10px', border: '1px solid #334155' }}>
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search PO, supplier, SKU..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ background: 'transparent', border: 'none', outline: 'none', color: '#f8fafc', fontSize: '12px', width: '200px' }}
              />
            </div>
          </div>
        </div>

        {/* PO Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #1e293b', color: '#94a3b8', textAlign: 'left' }}>
                <th style={{ padding: '10px 12px' }}>PO NUMBER</th>
                <th style={{ padding: '10px 12px' }}>SUPPLIER</th>
                <th style={{ padding: '10px 12px' }}>PRODUCT & SKU</th>
                <th style={{ padding: '10px 12px' }}>DESTINATION WAREHOUSE</th>
                <th style={{ padding: '10px 12px' }}>QUANTITY</th>
                <th style={{ padding: '10px 12px' }}>TOTAL VALUE</th>
                <th style={{ padding: '10px 12px' }}>STATUS</th>
                <th style={{ padding: '10px 12px', textAlign: 'right' }}>DOCK ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((po) => {
                const badge = STATUS_CONFIG[po.status] || STATUS_CONFIG.in_transit;
                const canReceive = po.status === 'in_transit' || po.status === 'draft';

                return (
                  <tr key={po.po_id} style={{ borderBottom: '1px solid #131e33', transition: 'background 0.15s ease' }}>
                    <td style={{ padding: '12px', fontFamily: 'monospace', fontWeight: 600, color: '#f8fafc' }}>
                      {po.po_id.slice(0, 16)}...
                    </td>
                    <td style={{ padding: '12px', color: '#cbd5e1' }}>{po.supplier_name}</td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ color: '#f8fafc', fontWeight: 500 }}>{po.product_name}</div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>{po.sku}</div>
                    </td>
                    <td style={{ padding: '12px', color: '#94a3b8' }}>{po.warehouse_name}</td>
                    <td style={{ padding: '12px', color: '#cbd5e1', fontWeight: 600 }}>{po.quantity.toLocaleString()} units</td>
                    <td style={{ padding: '12px', color: '#34d399', fontWeight: 600 }}>{formatCurrency(po.total_cost)}</td>
                    <td style={{ padding: '12px' }}>
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
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      {canReceive ? (
                        <button
                          onClick={() => handleReceiveStock(po)}
                          disabled={receivingId === po.po_id}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '5px 12px',
                            background: 'rgba(16, 185, 129, 0.2)',
                            border: '1px solid rgba(16, 185, 129, 0.4)',
                            borderRadius: '4px',
                            color: '#34d399',
                            fontWeight: 600,
                            cursor: 'pointer',
                            fontSize: '11px',
                          }}
                        >
                          <ArrowDownLeft className="w-3.5 h-3.5" />
                          {receivingId === po.po_id ? 'Receiving...' : '1-Click Dock Receipt'}
                        </button>
                      ) : (
                        <span style={{ color: '#64748b', fontSize: '11px' }}>Processed</span>
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
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', padding: '24px', width: '500px', maxWidth: '90%' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 16px 0', color: '#f8fafc' }}>
              Issue Inbound Replenishment Purchase Order
            </h2>
            <form onSubmit={handleCreatePoSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Supplier</label>
                <select
                  value={selectedSupplierId}
                  onChange={(e) => setSelectedSupplierId(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                >
                  <option value="sup00000-0000-0000-0000-000000000001">Apex Microelectronics Inc. (Japan - 96.5% Rel)</option>
                  <option value="sup00000-0000-0000-0000-000000000002">Global Precision Systems GmbH (Germany - 91.2% Rel)</option>
                  <option value="sup00000-0000-0000-0000-000000000003">Nexus Advanced Circuits (USA - 88.0% Rel)</option>
                  <option value="sup00000-0000-0000-0000-000000000004">Pacific Freight Logistics Ltd. (Taiwan - 82.3% Rel)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Component / Product</label>
                <select
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                >
                  <option value="30000000-0000-0000-0000-000000000001">Industrial Sensor Module (ELEC-001)</option>
                  <option value="30000000-0000-0000-0000-000000000002">High-Torque Servo Motor (ELEC-002)</option>
                  <option value="30000000-0000-0000-0000-000000000004">Precision Ball Bearing Set (MECH-001)</option>
                  <option value="30000000-0000-0000-0000-000000000005">Hydraulic Actuator Cylinder (MECH-002)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Destination Hub</label>
                <select
                  value={selectedWarehouseId}
                  onChange={(e) => setSelectedWarehouseId(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                >
                  <option value="10000000-0000-0000-0000-000000000001">Newark Distribution Center (US)</option>
                  <option value="10000000-0000-0000-0000-000000000002">Birmingham Fulfilment Hub (GB)</option>
                  <option value="10000000-0000-0000-0000-000000000003">Frankfurt Logistics Centre (DE)</option>
                  <option value="22222222-0000-0000-0000-000000000001">Pacific Northwest MegaHub (Seattle)</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Units to Procure</label>
                  <input
                    type="number"
                    value={poQty}
                    onChange={(e) => setPoQty(Math.max(1, parseInt(e.target.value) || 1))}
                    style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Unit Contract Cost ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={poUnitCost}
                    onChange={(e) => setPoUnitCost(Math.max(0.1, parseFloat(e.target.value) || 1))}
                    style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                    required
                  />
                </div>
              </div>

              <div style={{ background: '#131e33', padding: '10px 14px', borderRadius: '6px', border: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>Total PO Financial Commitment:</span>
                <span style={{ fontSize: '16px', fontWeight: 700, color: '#34d399' }}>{formatCurrency(poQty * poUnitCost)}</span>
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
                  style={{ padding: '8px 18px', background: '#059669', border: 'none', borderRadius: '5px', color: '#ffffff', fontWeight: 600, cursor: 'pointer', fontSize: '13px' }}
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
