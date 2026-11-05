import React, { useEffect, useState, useCallback, useRef } from 'react';
import { inventoryApi } from '../services/api';
import type { InventoryRecord, InventorySummary, PurchaseOrder } from '../types';
import { formatCurrency, formatPoId } from '../utils/formatters';
import {
  Sparkles,
  CheckCircle2,
  RefreshCw,
  Warehouse,
  Package,
  AlertTriangle,
  Target,
  Bot,
  Check,
  Boxes,
} from 'lucide-react';

const STATUS_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  ok:       { color: '#34d399', bg: 'rgba(16, 185, 129, 0.08)', border: 'rgba(16, 185, 129, 0.2)', label: 'Normal' },
  low:      { color: '#fbbf24', bg: 'rgba(245, 158, 11, 0.08)', border: 'rgba(245, 158, 11, 0.2)', label: 'Low Stock' },
  critical: { color: '#f87171', bg: 'rgba(239, 68, 68, 0.08)', border: 'rgba(239, 68, 68, 0.2)', label: 'Critical' },
};

const PO_STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  in_transit: { color: '#60a5fa', label: 'In Transit' },
  draft:      { color: '#94a3b8', label: 'Drafted' },
  received:   { color: '#34d399', label: 'Received' },
};

export const InventoryPage: React.FC = () => {
  const [items, setItems] = useState<InventoryRecord[]>([]);
  const [replenishmentOrders, setReplenishmentOrders] = useState<PurchaseOrder[]>([]);
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [lowOnly, setLowOnly] = useState(false);
  const [search, setSearch] = useState('');
  const [receivingPoId, setReceivingPoId] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [isScanning, setIsScanning] = useState(false);
  const [isAutoHealing, setIsAutoHealing] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const fetchInventory = useCallback(async (isSilent = false) => {
    try {
      const [invRes, sumRes, repRes] = await Promise.all([
        inventoryApi.list({ limit: 100, low_stock_only: lowOnly }),
        inventoryApi.getSummary(),
        inventoryApi.getReplenishmentOrders({ limit: 50 }),
      ]);
      if (isMountedRef.current) {
        setItems(invRes.items);
        setSummary(sumRes);
        setReplenishmentOrders(repRes.items);
        setLastUpdated(new Date());
      }
    } catch (err) {
      console.error('Inventory load failed:', err);
    } finally {
      if (isMountedRef.current && !isSilent) {
        setLoading(false);
      }
    }
  }, [lowOnly]);

  const handleAutonomousScan = async () => {
    setIsScanning(true);
    setScanMessage(null);
    try {
      const res = await inventoryApi.runAutonomousScan();
      if (isMountedRef.current) {
        setScanMessage(res.message);
        await fetchInventory(true);
      }
    } catch (err) {
      console.error('Autonomous scan error:', err);
    } finally {
      if (isMountedRef.current) setIsScanning(false);
    }
  };

  const handleAutoHealAll = async () => {
    setIsAutoHealing(true);
    setScanMessage(null);
    try {
      const res = await inventoryApi.autoHealAll();
      if (isMountedRef.current) {
        setScanMessage(res.message);
        await fetchInventory(true);
      }
    } catch (err) {
      console.error('Auto heal error:', err);
    } finally {
      if (isMountedRef.current) setIsAutoHealing(false);
    }
  };

  const handleReceiveStock = async (poId: string) => {
    setReceivingPoId(poId);
    try {
      await inventoryApi.receiveReplenishmentOrder(poId);
      await fetchInventory(true);
    } catch (err) {
      console.error('Failed to receive replenishment PO:', err);
    } finally {
      if (isMountedRef.current) {
        setReceivingPoId(null);
      }
    }
  };

  useEffect(() => {
    let ignore = false;
    isMountedRef.current = true;

    Promise.all([
      inventoryApi.list({ limit: 100, low_stock_only: lowOnly }),
      inventoryApi.getSummary(),
      inventoryApi.getReplenishmentOrders({ limit: 50 }),
    ]).then(([invRes, sumRes, repRes]) => {
      if (!ignore && isMountedRef.current) {
        setItems(invRes.items);
        setSummary(sumRes);
        setReplenishmentOrders(repRes.items);
        setLastUpdated(new Date());
        setLoading(false);
      }
    }).catch((err) => {
      console.error('Inventory load failed:', err);
      if (!ignore && isMountedRef.current) setLoading(false);
    });

    // Auto-sync inventory every 3.5 seconds
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchInventory(true);
      }
    }, 3500);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        fetchInventory(true);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      ignore = true;
      isMountedRef.current = false;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [fetchInventory, lowOnly]);

  const filtered = items.filter(
    (item) =>
      item.product_name.toLowerCase().includes(search.toLowerCase()) ||
      item.sku.toLowerCase().includes(search.toLowerCase()) ||
      item.warehouse_name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="page-content animate-fade-in" style={{ padding: '24px 28px', maxWidth: '1440px', margin: '0 auto', color: '#f8fafc' }}>
      <div className="page-header" style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 700, margin: 0, letterSpacing: '-0.02em', color: '#f8fafc' }}>
          Warehouse Inventory (WMS)
        </h1>
        <p style={{ color: '#64748b', fontSize: '13px', margin: '4px 0 0 0' }}>
          Stock levels across regional hubs with automated safety stock replenishment
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleAutonomousScan}
            disabled={isScanning || isAutoHealing}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: '#2563eb', border: 'none', borderRadius: '5px', fontWeight: 600, fontSize: '12px' }}
          >
            <Sparkles size={13} className={isScanning ? 'animate-spin' : ''} />
            {isScanning ? 'Scanning Network...' : 'Run Autonomous Agent Scan'}
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleAutoHealAll}
            disabled={isScanning || isAutoHealing}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', color: '#cbd5e1', borderRadius: '5px', fontSize: '12px' }}
          >
            <CheckCircle2 size={13} />
            Commit All Inbound Stock
          </button>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => { setLoading(true); fetchInventory(false); }}
            disabled={loading}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', color: '#cbd5e1', borderRadius: '5px', fontSize: '12px' }}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: '#94a3b8' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#34d399', display: 'inline-block' }} />
            Synced {lastUpdated.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {scanMessage && (
        <div style={{
          padding: '0.875rem 1.25rem',
          background: 'rgba(37,99,235,0.08)',
          border: '1px solid rgba(37,99,235,0.3)',
          borderRadius: '10px',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          color: 'var(--c-text-primary)',
          fontSize: '0.85rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Bot size={16} className="text-blue-400" />
            <span>{scanMessage}</span>
          </div>
          <button
            onClick={() => setScanMessage(null)}
            style={{ background: 'none', border: 'none', color: 'var(--c-text-muted)', cursor: 'pointer', fontSize: '1.1rem' }}
          >
            ×
          </button>
        </div>
      )}

      {/* Summary KPIs */}
      <div className="grid-4 mb-6">
        {[
          {
            label: 'Total Locations',
            value: summary?.total_sku_locations ?? '—',
            icon: Warehouse,
          },
          {
            label: 'Net Available Units',
            value: summary ? summary.net_available_units.toLocaleString() : '—',
            icon: Package,
          },
          {
            label: 'Low Stock Alerts',
            value: summary?.low_stock_locations ?? '—',
            icon: AlertTriangle,
          },
          {
            label: 'Stock Availability',
            value: summary ? `${summary.fill_rate_pct}%` : '—',
            sub: 'Target: ≥ 95%',
            icon: Target,
          },
        ].map(({ label, value, sub, icon: Icon }) => (
          <div key={label} className="card">
            <div className="flex justify-between items-start mb-2">
              <span className="kpi-label">{label}</span>
              <Icon size={16} className="text-slate-400" />
            </div>
            <div className="kpi-value" style={{ fontSize: '1.75rem', margin: '0.25rem 0' }}>
              {loading ? <div className="skeleton" style={{ height: '28px', width: '80px' }} /> : value}
            </div>
            {sub && <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>{sub}</div>}
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card mb-4">
        <div className="flex gap-3 items-center" style={{ flexWrap: 'wrap' }}>
          <input
            className="form-input"
            style={{ maxWidth: '300px' }}
            placeholder="Search by product, SKU, or warehouse…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <label className="flex items-center gap-2" style={{ cursor: 'pointer', color: '#94a3b8', fontSize: '0.875rem' }}>
            <input
              type="checkbox"
              checked={lowOnly}
              onChange={(e) => {
                setLoading(true);
                setLowOnly(e.target.checked);
              }}
              style={{ accentColor: '#f59e0b' }}
            />
            Show low-stock only
          </label>
          <span className="badge badge-info">{filtered.length} records</span>
        </div>
      </div>

      {/* Table */}
      <div className="card animate-fade-in">
        {loading ? (
          <div className="loading-overlay">
            <span className="loading-spinner" style={{ width: 32, height: 32 }} />
            <p>Loading inventory data…</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <Package size={32} className="text-slate-600 mb-2" />
            <p>No inventory records found</p>
            <p style={{ fontSize: '0.8rem', color: '#475569' }}>
              Run the rich seed script to populate data
            </p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Product / SKU</th>
                  <th>Warehouse</th>
                  <th>Available</th>
                  <th>Reserved</th>
                  <th>Net Available</th>
                  <th>Safety Stock</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const sc = STATUS_CONFIG[item.status];
                  return (
                    <tr key={item.inventory_id}>
                      <td>
                        <div>
                          <span style={{ fontWeight: 600 }}>{item.product_name}</span>
                          <div className="tag" style={{ marginTop: '2px', fontSize: '0.7rem' }}>
                            {item.sku}
                          </div>
                        </div>
                      </td>
                      <td>
                        <div>
                          <span>{item.warehouse_name}</span>
                          <div style={{ fontSize: '0.75rem', color: '#475569' }}>
                            {item.warehouse_city}
                          </div>
                        </div>
                      </td>
                      <td>{item.available_qty.toLocaleString()}</td>
                      <td style={{ color: '#f59e0b' }}>{item.reserved_qty.toLocaleString()}</td>
                      <td>
                        <span style={{ color: item.net_available < item.safety_stock ? '#ef4444' : '#10b981', fontWeight: 600 }}>
                          {item.net_available.toLocaleString()}
                        </span>
                      </td>
                      <td style={{ color: '#64748b' }}>{item.safety_stock.toLocaleString()}</td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            background: `${sc.color}22`,
                            color: sc.color,
                            border: `1px solid ${sc.color}44`,
                          }}
                        >
                          {sc.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Autonomous Inbound Replenishment & Purchase Orders */}
      <div className="card mt-6 animate-fade-in">
        <div className="section-header mb-4">
          <div>
            <h3 className="section-title flex items-center gap-2">
              <RefreshCw size={16} className="text-slate-400" />
              <span>Autonomous Inbound Replenishment (Self-Healing Digital Twin)</span>
            </h3>
            <p style={{ fontSize: '0.8125rem', color: '#64748b', marginTop: '0.25rem' }}>
              When order reservations breach safety stock thresholds, ADS-03 &amp; ADS-05 autonomously draft purchase orders to restore inventory buffers.
            </p>
          </div>
          <span className="badge badge-info">{replenishmentOrders.length} inbound POs</span>
        </div>

        {replenishmentOrders.length === 0 ? (
          <div className="empty-state">
            <Boxes size={32} className="text-slate-600 mb-2" />
            <p>No active replenishment purchase orders</p>
            <p style={{ fontSize: '0.8rem', color: '#475569' }}>
              All inventory levels are currently above reorder points
            </p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>PO Reference</th>
                  <th>Target SKU / Product</th>
                  <th>Assigned Supplier</th>
                  <th>Destination Hub</th>
                  <th>Order Qty</th>
                  <th>Unit Cost</th>
                  <th>Total Cost</th>
                  <th>Lead Time</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {replenishmentOrders.map((po) => {
                  const psc = PO_STATUS_CONFIG[po.status] ?? PO_STATUS_CONFIG.draft;
                  return (
                    <tr key={po.po_id}>
                      <td>
                        <span className="tag" style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                          {formatPoId(po.po_id)}
                        </span>
                      </td>
                      <td>
                        <div>
                          <strong>{po.product_name}</strong>
                          <div className="tag" style={{ marginTop: '2px', fontSize: '0.7rem' }}>
                            {po.sku}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span style={{ fontWeight: 500, color: 'var(--c-text-primary)' }}>
                          {po.supplier_name}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.8125rem', color: '#94a3b8' }}>
                          {po.warehouse_name || 'Main Fulfillment Hub'}
                        </span>
                      </td>
                      <td>
                        <span className="badge badge-info">{po.quantity.toLocaleString()} units</span>
                      </td>
                      <td>{formatCurrency(po.unit_cost)}</td>
                      <td style={{ fontWeight: 600, color: '#10b981' }}>
                        {formatCurrency(po.total_cost)}
                      </td>
                      <td>
                        <span style={{ fontSize: '0.8125rem', color: '#64748b' }}>
                          {po.lead_time_days} days
                        </span>
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            background: `${psc.color}22`,
                            color: psc.color,
                            border: `1px solid ${psc.color}44`,
                            textTransform: 'uppercase',
                          }}
                        >
                          {psc.label}
                        </span>
                      </td>
                      <td>
                        {po.status === 'received' ? (
                          <span style={{ color: '#10b981', fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <Check size={13} /> Stock Restored
                          </span>
                        ) : (
                          <button
                            className="btn btn-sm flex items-center gap-1.5"
                            style={{
                              background: '#10b981',
                              color: '#fff',
                              border: 'none',
                              fontSize: '0.75rem',
                              padding: '4px 10px',
                              fontWeight: 600,
                            }}
                            onClick={() => handleReceiveStock(po.po_id)}
                            disabled={receivingPoId === po.po_id}
                          >
                            <Check size={13} />
                            <span>{receivingPoId === po.po_id ? 'Receiving…' : 'Receive Stock'}</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
