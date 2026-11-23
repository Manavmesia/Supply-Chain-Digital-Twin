import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { inventoryApi } from '../services/api';
import type { InventoryRecord, InventorySummary, PurchaseOrder } from '../types';
import {
  Sparkles,
  CheckCircle2,
  RefreshCw,
  Warehouse,
  Package,
  AlertTriangle,
  Target,
  Bot,
  Building2,
  ArrowRight,
} from 'lucide-react';

const STATUS_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  ok:       { color: '#34d399', bg: 'rgba(16, 185, 129, 0.08)', border: 'rgba(16, 185, 129, 0.2)', label: 'Normal' },
  low:      { color: '#fbbf24', bg: 'rgba(245, 158, 11, 0.08)', border: 'rgba(245, 158, 11, 0.2)', label: 'Low Stock' },
  critical: { color: '#f87171', bg: 'rgba(239, 68, 68, 0.08)', border: 'rgba(239, 68, 68, 0.2)', label: 'Critical' },
};

export const InventoryPage: React.FC = () => {
  const [items, setItems] = useState<InventoryRecord[]>([]);
  const [replenishmentOrders, setReplenishmentOrders] = useState<PurchaseOrder[]>([]);
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [lowOnly, setLowOnly] = useState(false);
  const [search, setSearch] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [isAutoHealing, setIsAutoHealing] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const fetchInventory = useCallback(async (isSilent = false) => {
    try {
      const [invRes, sumRes, repRes] = await Promise.all([
        inventoryApi.list({ limit: 100, low_stock_only: lowOnly }),
        inventoryApi.getSummary(),
        inventoryApi.getReplenishmentOrders({ limit: 50, status: 'in_transit' }),
      ]);
      if (isMountedRef.current) {
        setItems(invRes.items);
        setSummary(sumRes);
        setReplenishmentOrders(repRes.items);
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
        if (res.deficits_detected > 0) {
          setLowOnly(true);
        }
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

  useEffect(() => {
    let ignore = false;
    isMountedRef.current = true;

    Promise.all([
      inventoryApi.list({ limit: 100, low_stock_only: lowOnly }),
      inventoryApi.getSummary(),
      inventoryApi.getReplenishmentOrders({ limit: 50, status: 'in_transit' }),
    ]).then(([invRes, sumRes, repRes]) => {
      if (!ignore && isMountedRef.current) {
        setItems(invRes.items);
        setSummary(sumRes);
        setReplenishmentOrders(repRes.items);
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
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Warehouse Inventory
          </h1>
          <p className="page-subtitle">
            Stock levels across regional hubs with automated safety stock replenishment.
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={() => { setLoading(true); fetchInventory(false); }}
            disabled={loading}
            className="btn-secondary"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={handleAutonomousScan}
            disabled={isScanning || isAutoHealing}
            className="btn-primary"
          >
            <Sparkles size={13} className={isScanning ? 'animate-spin' : ''} />
            {isScanning ? 'Scanning...' : 'Scan Stock'}
          </button>
          <button
            onClick={handleAutoHealAll}
            disabled={isScanning || isAutoHealing}
            className="btn-secondary"
            style={{ color: '#059669', borderColor: '#a7f3d0', background: '#ecfdf5', fontWeight: 600 }}
          >
            <CheckCircle2 size={14} className="text-emerald-600" />
            Receive Stock
          </button>
        </div>
      </div>

      {scanMessage && (
        <div className="banner-info" style={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
            <Bot size={16} className="text-blue-600" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '13px' }}>{scanMessage}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setLowOnly(!lowOnly)}
              className="btn-secondary"
              style={{ fontSize: '11px', padding: '3px 10px', height: '28px', whiteSpace: 'nowrap' }}
            >
              {lowOnly ? 'Show All' : 'Show Deficits'}
            </button>
            <button
              onClick={() => setScanMessage(null)}
              style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '16px' }}
              title="Dismiss"
            >
              &times;
            </button>
          </div>
        </div>
      )}

      {/* Summary KPIs */}
      <div className="stat-grid">
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
          <div key={label} className="stat-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <span className="stat-label">{label}</span>
              <Icon size={16} className="text-slate-400" />
            </div>
            <div className="stat-value">
              {loading ? <div className="skeleton" style={{ height: '28px', width: '80px' }} /> : value}
            </div>
            {sub && <div className="stat-sub">{sub}</div>}
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="filter-toolbar">
        <div className="filter-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', color: '#475569', fontSize: '13px', fontWeight: 500 }}>
            <input
              type="checkbox"
              checked={lowOnly}
              onChange={(e) => {
                setLoading(true);
                setLowOnly(e.target.checked);
              }}
              style={{ accentColor: '#2563eb' }}
            />
            Show low-stock SKUs only
          </label>
          <span style={{ fontSize: '12px', color: '#64748b', padding: '2px 8px', background: '#f1f5f9', borderRadius: '9999px', fontWeight: 600 }}>
            {filtered.length} records
          </span>
        </div>

        <div className="search-box">
          <input
            className="search-input"
            style={{ width: '260px' }}
            placeholder="Search by product, SKU, or warehouse..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
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
                          <div className="tag" style={{ marginTop: '2px', fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}>
                            {item.sku}
                          </div>
                        </div>
                      </td>
                      <td>
                        <div>
                          <span style={{ fontWeight: 500 }}>{item.warehouse_name}</span>
                          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)' }}>
                            {item.warehouse_city}
                          </div>
                        </div>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{item.available_qty.toLocaleString()}</td>
                      <td style={{ color: 'var(--c-warning)', fontFamily: 'var(--font-mono)' }}>{item.reserved_qty.toLocaleString()}</td>
                      <td>
                        <span style={{ color: item.net_available < item.safety_stock ? 'var(--c-danger)' : 'var(--c-success)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                          {item.net_available.toLocaleString()}
                        </span>
                      </td>
                      <td style={{ color: 'var(--c-text-muted)', fontFamily: 'var(--font-mono)' }}>{item.safety_stock.toLocaleString()}</td>
                      <td>
                        <span
                          style={{
                            fontSize: 'var(--text-xs)',
                            fontWeight: 600,
                            padding: '3px 10px',
                            borderRadius: 'var(--radius-full)',
                            background: `${sc.color}18`,
                            color: sc.color,
                            border: `1px solid ${sc.color}44`,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: sc.color }} />
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

      {/* Inbound Replenishment & Safety Stock Buffer Card */}
      <div
        style={{
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: 'var(--radius-lg)',
          padding: '20px 24px',
          marginTop: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '8px',
              background: '#eff6ff',
              border: '1px solid #bfdbfe',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#2563eb',
            }}
          >
            <Building2 size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', margin: 0 }}>
              Inbound Replenishment
            </h3>
            <p style={{ fontSize: '12px', color: '#64748b', margin: '3px 0 0 0' }}>
              {replenishmentOrders.length > 0
                ? `${replenishmentOrders.length} purchase order${replenishmentOrders.length > 1 ? 's' : ''} in transit.`
                : 'All warehouses operating within safety buffers.'}
            </p>
          </div>
        </div>

        <Link
          to="/procurement"
          className="btn-primary"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            textDecoration: 'none',
            padding: '8px 14px',
            fontSize: '12px',
          }}
        >
          <span>View in Procurement</span>
          <ArrowRight size={13} />
        </Link>
      </div>
    </div>
  );
};
