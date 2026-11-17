import React from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';
import { formatDateTime, formatOrderId, formatWorkflowId, formatEventId } from '../../utils/formatters';

interface BusinessDataViewProps {
  data: unknown;
  layout?: 'grid' | 'list' | 'compact';
  title?: string;
  emptyMessage?: string;
}

/** Humanizes camelCase or snake_case keys into Title Case enterprise labels */
export function humanizeKey(key: string): string {
  if (!key) return '';

  const acronyms: Record<string, string> = {
    id: 'ID',
    sku: 'SKU',
    co2: 'CO₂',
    esg: 'ESG',
    kpi: 'KPI',
    po: 'PO',
    so: 'SO',
    mo: 'Work Order',
    qa: 'QA',
    qc: 'QC',
    qty: 'Quantity',
    dc: 'Distribution Center',
    dc_id: 'DC ID',
    eta: 'ETA',
    etd: 'ETD',
    sla: 'SLA',
    crm: 'CRM',
    erp: 'ERP',
    wms: 'WMS',
    tms: 'TMS',
    oms: 'OMS',
    carrier_id: 'Carrier ID',
    batch_id: 'Batch ID',
  };

  const lower = key.toLowerCase();
  if (acronyms[lower]) return acronyms[lower];

  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .trim()
    .split(' ')
    .map(word => {
      const wLower = word.toLowerCase();
      if (acronyms[wLower]) return acronyms[wLower];
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
}

/** Determines if a string is an ISO date string */
function isIsoDateString(val: string): boolean {
  if (typeof val !== 'string' || val.length < 10) return false;
  return /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?/.test(val) && !isNaN(Date.parse(val));
}

/** Formats a single primitive or array value for business users */
export const BusinessValue: React.FC<{ value: unknown; fieldKey?: string }> = ({ value, fieldKey = '' }) => {
  const lowerKey = fieldKey.toLowerCase();

  if (value === null || value === undefined || value === '') {
    return <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.85rem' }}>Not specified</span>;
  }

  // Boolean values
  if (typeof value === 'boolean') {
    return value ? (
      <span className="badge badge-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}>
        <CheckCircle2 size={12} /> Yes / Handled
      </span>
    ) : (
      <span className="badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', background: '#f1f5f9', color: '#64748b' }}>
        <XCircle size={12} /> No / None
      </span>
    );
  }

  // Numbers and currency/percentages
  if (typeof value === 'number') {
    if (lowerKey.includes('cost') || lowerKey.includes('price') || lowerKey.includes('margin_usd') || lowerKey.includes('revenue')) {
      return <strong style={{ color: '#0f172a' }}>${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>;
    }
    if (lowerKey.includes('pct') || lowerKey.includes('rate') || lowerKey.includes('percent')) {
      return <strong style={{ color: '#0f172a' }}>{value.toLocaleString()}%</strong>;
    }
    if (lowerKey.includes('score')) {
      const color = value >= 80 ? '#10b981' : value >= 50 ? '#f59e0b' : '#ef4444';
      return <span style={{ color, fontWeight: 700 }}>{value.toLocaleString()} / 100</span>;
    }
    if (lowerKey.includes('hours') || lowerKey.includes('delay')) {
      return <strong style={{ color: '#d97706' }}>{value} hrs</strong>;
    }
    if (lowerKey.includes('kg') || lowerKey.includes('co2')) {
      return <strong>{value.toLocaleString()} kg</strong>;
    }
    return <strong style={{ color: '#0f172a' }}>{value.toLocaleString()}</strong>;
  }

  // Strings
  if (typeof value === 'string') {
    // Check if it's an ISO date
    if (isIsoDateString(value)) {
      return <span style={{ fontSize: '0.825rem', color: '#334155' }}>{formatDateTime(value)}</span>;
    }

    // Check if it's an ID
    if (/^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(value)) {
      if (lowerKey.includes('order')) return <span className="tag" style={{ color: '#2563eb' }}>{formatOrderId(value)}</span>;
      if (lowerKey.includes('workflow')) return <span className="tag" style={{ color: '#8b5cf6' }}>{formatWorkflowId(value)}</span>;
      if (lowerKey.includes('event')) return <span className="tag" style={{ color: '#10b981' }}>{formatEventId(value)}</span>;
      return <span className="tag" style={{ fontFamily: 'monospace' }}>#{value.slice(0, 8).toUpperCase()}</span>;
    }

    // Status or compliance badges
    if (['ready', 'active', 'completed', 'approved', 'success', 'a+', 'low'].includes(value.toLowerCase())) {
      return <span className="badge badge-success" style={{ textTransform: 'capitalize' }}>{value}</span>;
    }
    if (['critical', 'high', 'failed', 'rejected', 'severe'].includes(value.toLowerCase())) {
      return <span className="badge badge-danger" style={{ textTransform: 'capitalize' }}>{value}</span>;
    }
    if (['warning', 'medium', 'pending', 'generating'].includes(value.toLowerCase())) {
      return <span className="badge badge-warning" style={{ textTransform: 'capitalize' }}>{value}</span>;
    }

    return <span style={{ color: '#334155', fontSize: '0.875rem' }}>{value}</span>;
  }

  // Arrays
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>None</span>;
    }

    // Array of primitives
    const allPrimitives = value.every(v => typeof v !== 'object' || v === null);
    if (allPrimitives) {
      return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {value.map((item, idx) => (
            <span key={idx} className="tag" style={{ fontSize: '0.75rem', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
              {String(item)}
            </span>
          ))}
        </div>
      );
    }

    // Array of objects
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
        {value.map((item, idx) => (
          <div
            key={idx}
            style={{
              padding: '8px 12px',
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
            }}
          >
            <BusinessDataView data={item} layout="list" />
          </div>
        ))}
      </div>
    );
  }

  // Nested object
  if (typeof value === 'object') {
    return (
      <div style={{ padding: '8px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', marginTop: '4px' }}>
        <BusinessDataView data={value} layout="list" />
      </div>
    );
  }

  return <span>{String(value)}</span>;
};

/**
 * Main Business Data View Component.
 * Transforms any backend object or payload into human-friendly business tiles and cards.
 */
export const BusinessDataView: React.FC<BusinessDataViewProps> = ({
  data,
  layout = 'grid',
  title,
  emptyMessage = 'No details recorded.',
}) => {
  if (!data || typeof data !== 'object') {
    return (
      <div style={{ color: '#64748b', fontSize: '0.85rem', fontStyle: 'italic', padding: '0.5rem 0' }}>
        {emptyMessage}
      </div>
    );
  }

  const entries = Object.entries(data as Record<string, unknown>).filter(
    ([k]) => !k.startsWith('_') && k !== 'password' && k !== 'token'
  );

  if (entries.length === 0) {
    return (
      <div style={{ color: '#64748b', fontSize: '0.85rem', fontStyle: 'italic', padding: '0.5rem 0' }}>
        {emptyMessage}
      </div>
    );
  }

  // Grid layout for executive summaries & dashboards
  if (layout === 'grid') {
    return (
      <div>
        {title && (
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
            {title}
          </div>
        )}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '10px',
          }}
        >
          {entries.map(([key, val]) => {
            const isComplex = typeof val === 'object' && val !== null;
            return (
              <div
                key={key}
                style={{
                  background: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  gridColumn: isComplex ? '1 / -1' : 'span 1',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
                }}
              >
                <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 500, textTransform: 'capitalize', marginBottom: '4px' }}>
                  {humanizeKey(key)}
                </div>
                <div style={{ fontSize: '0.95rem' }}>
                  <BusinessValue value={val} fieldKey={key} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // List layout for drawer details and telemetry cards
  return (
    <div>
      {title && (
        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
          {title}
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {entries.map(([key, val]) => (
          <div
            key={key}
            style={{
              display: 'flex',
              flexDirection: typeof val === 'object' && val !== null ? 'column' : 'row',
              justifyContent: 'space-between',
              alignItems: typeof val === 'object' && val !== null ? 'flex-start' : 'center',
              padding: '6px 10px',
              background: '#ffffff',
              border: '1px solid #f1f5f9',
              borderRadius: '6px',
              gap: '8px',
            }}
          >
            <span style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 500 }}>
              {humanizeKey(key)}
            </span>
            <div style={{ textAlign: typeof val === 'object' && val !== null ? 'left' : 'right', width: typeof val === 'object' && val !== null ? '100%' : 'auto' }}>
              <BusinessValue value={val} fieldKey={key} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
