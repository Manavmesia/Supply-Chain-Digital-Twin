import React, { useEffect, useState } from 'react';
import { inventoryApi } from '../services/api';
import type { InventoryRecord, InventorySummary } from '../types';

const STATUS_CONFIG = {
  ok:       { color: '#10b981', label: 'OK' },
  low:      { color: '#f59e0b', label: 'Low Stock' },
  critical: { color: '#ef4444', label: 'Critical' },
};

export const InventoryPage: React.FC = () => {
  const [items, setItems] = useState<InventoryRecord[]>([]);
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [lowOnly, setLowOnly] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    let ignore = false;
    Promise.all([
      inventoryApi.list({ limit: 100, low_stock_only: lowOnly }),
      inventoryApi.getSummary(),
    ]).then(([invRes, sumRes]) => {
      if (!ignore) {
        setItems(invRes.items);
        setSummary(sumRes);
        setLoading(false);
      }
    }).catch((err) => {
      console.error(err);
      if (!ignore) setLoading(false);
    });
    return () => { ignore = true; };
  }, [lowOnly]);

  const filtered = items.filter(
    (item) =>
      item.product_name.toLowerCase().includes(search.toLowerCase()) ||
      item.sku.toLowerCase().includes(search.toLowerCase()) ||
      item.warehouse_name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="page-content animate-fade-in">
      <div className="page-header">
        <h1><span className="gradient-text">Inventory Intelligence</span></h1>
        <p>Live stock levels across all warehouses with safety stock monitoring</p>
      </div>

      {/* Summary KPIs */}
      <div className="grid-4 mb-6">
        {[
          {
            label: 'Total Locations',
            value: summary?.total_sku_locations ?? '—',
            color: '#3b82f6',
            icon: '🏪',
          },
          {
            label: 'Net Available Units',
            value: summary ? summary.net_available_units.toLocaleString() : '—',
            color: '#10b981',
            icon: '📦',
          },
          {
            label: 'Low Stock Alerts',
            value: summary?.low_stock_locations ?? '—',
            color: '#f59e0b',
            icon: '⚠️',
          },
          {
            label: 'Stock Availability',
            value: summary ? `${summary.fill_rate_pct}%` : '—',
            sub: 'Target: ≥ 95%',
            color: summary && summary.fill_rate_pct >= 95 ? '#10b981' : '#ef4444',
            icon: '🎯',
          },
        ].map(({ label, value, sub, color, icon }) => (
          <div key={label} className="card" style={{ borderTop: `2px solid ${color}` }}>
            <span style={{ fontSize: '1.5rem' }}>{icon}</span>
            <div className="kpi-value" style={{ color, fontSize: '1.75rem', margin: '0.5rem 0' }}>
              {loading ? <div className="skeleton" style={{ height: '28px', width: '80px' }} /> : value}
            </div>
            <div className="kpi-label">{label}</div>
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
            <span className="empty-icon">📦</span>
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
    </div>
  );
};
