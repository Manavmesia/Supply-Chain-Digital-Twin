import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { eventsApi, inventoryApi } from '../services/api';
import type { EventRecord } from '../types';
import {
  AlertTriangle,
  Zap,
  Activity,
  Search,
  Plus,
  ChevronDown,
  ChevronRight,
  Clock,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { formatTimeAgo } from '../utils/formatters';
import { BusinessDataView } from '../components/common/BusinessDataView';

const EXCEPTION_TYPES = [
  'DeliveryDelayed',
  'InventoryLow',
  'QualityAlertRaised',
  'CarrierDelayed',
  'WarehouseStockout',
  'SupplierUnavailable',
  'AnomalyDetected',
];

const getExceptionSummary = (ev: EventRecord): {
  title: string;
  details: string;
  linkText?: string;
  linkTo?: string;
  secondaryLinkText?: string;
  secondaryLinkTo?: string;
} => {
  const p = ev.payload || {};
  switch (ev.event_type) {
    case 'InventoryLow':
    case 'WarehouseStockout':
      return {
        title: `Low Inventory Deficit: ${p.product_name || p.sku || 'SKU'}`,
        details: `Available: ${p.available_qty ?? 0} units vs Safety Buffer: ${p.safety_stock ?? 0} units at ${p.warehouse_name || 'Warehouse'}`,
        linkText: 'View in Inventory',
        linkTo: '/inventory',
        secondaryLinkText: 'Check Replenishment PO',
        secondaryLinkTo: '/procurement',
      };
    case 'DeliveryDelayed':
    case 'CarrierDelayed':
      return {
        title: `Transit Bottleneck: ${p.location || 'Transit Corridor'}`,
        details: typeof p.description === 'string' ? p.description : 'Shipment route experienced transit delay and dynamic rerouting is underway.',
        linkText: 'Track Shipments',
        linkTo: '/shipments',
      };
    case 'QualityAlertRaised':
      return {
        title: `Quality Defect: ${p.defect_type || 'Defect detected'}`,
        details: typeof p.defect_type === 'string' ? `Lot inspection flagged: ${p.defect_type} on ${p.product_name || 'batch'}.` : `Lot inspection flagged for ${p.product_name || 'product batch'}.`,
        linkText: 'View Orders',
        linkTo: '/orders',
      };
    default:
      return {
        title: `${ev.event_type} Exception`,
        details: typeof p.description === 'string' ? p.description : (typeof p.reason === 'string' ? p.reason : 'Operational bottleneck detected and placed under multi-agent mitigation.'),
      };
  }
};

export const ControlTowerPage: React.FC = () => {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [filterExceptionsOnly, setFilterExceptionsOnly] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showDeclareModal, setShowDeclareModal] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Modal form states
  const [formType, setFormType] = useState('DeliveryDelayed');
  const [formSource, setFormSource] = useState('Operator-Cockpit');
  const [formLocation, setFormLocation] = useState('Newark Distribution Center');
  const [formDescription, setFormDescription] = useState('Severe transit bottleneck detected by regional control hub.');
  const [submitting, setSubmitting] = useState(false);

  const isMountedRef = useRef(true);

  const loadEvents = useCallback(async (isSilent = false) => {
    try {
      const res = await eventsApi.list({ limit: 100 });
      if (isMountedRef.current) {
        setEvents(res.items || []);
      }
    } catch (err) {
      console.error('Failed to load events:', err);
    } finally {
      if (isMountedRef.current && !isSilent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    loadEvents();
    const interval = setInterval(() => loadEvents(true), 8000);
    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
    };
  }, [loadEvents]);

  const handleAutonomousScan = async () => {
    setIsScanning(true);
    setActionNotice(null);
    try {
      const res = await inventoryApi.runAutonomousScan();
      setActionNotice(res.message);
      await loadEvents(true);
    } catch (err: any) {
      setActionNotice(`Scan failed: ${err.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  const handleDeclareSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await eventsApi.inject({
        event_type: formType,
        source_agent: formSource,
        payload: {
          location: formLocation,
          description: formDescription,
          reported_at: new Date().toISOString(),
        },
      });
      setShowDeclareModal(false);
      const rem = res.remediation?.remediation_summary || 'Autonomous multi-agent remediation executed.';
      setActionNotice(`Incident logged! ${rem}`);
      await loadEvents(true);
    } catch (err: any) {
      setActionNotice(`Incident declaration failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const activeExceptions = events.filter((ev) =>
    EXCEPTION_TYPES.includes(ev.event_type)
  );

  const filteredEvents = events.filter((ev) => {
    if (filterExceptionsOnly && !EXCEPTION_TYPES.includes(ev.event_type)) return false;
    if (selectedType !== 'all' && ev.event_type !== selectedType) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchType = ev.event_type.toLowerCase().includes(q);
      const matchSource = ev.source_agent.toLowerCase().includes(q);
      const matchId = ev.event_id.toLowerCase().includes(q);
      const matchPayload = JSON.stringify(ev.payload || {}).toLowerCase().includes(q);
      return matchType || matchSource || matchId || matchPayload;
    }
    return true;
  });

  const exceptionCount = activeExceptions.length;

  return (
    <div className="page-container animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Incident Control Tower
          </h1>
          <p className="page-subtitle">
            Monitor operational exceptions, logistics delays, and automated incident resolution.
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={handleAutonomousScan}
            disabled={isScanning}
            className="btn-secondary"
          >
            <Sparkles className={`w-3.5 h-3.5 text-amber-500 ${isScanning ? 'animate-spin' : ''}`} />
            {isScanning ? 'Scanning...' : 'Scan for Exceptions'}
          </button>
          <button
            onClick={() => setShowDeclareModal(true)}
            className="btn-primary"
            style={{ background: '#dc2626' }}
          >
            <Plus className="w-4 h-4" />
            Report Incident
          </button>
        </div>
      </div>

      {actionNotice && (
        <div className="banner-info">
          <Zap className="w-4 h-4 text-blue-600 flex-shrink-0" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* Control Tower Operational Metrics */}
      <div className="stat-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card">
          <div className="stat-label">TOTAL TELEMETRY EVENTS</div>
          <div className="stat-value" style={{ color: '#0f172a' }}>
            {loading ? '—' : events.length}
          </div>
          <div className="stat-sub">Live supply chain signals</div>
        </div>

        <div
          className="stat-card"
          onClick={() => {
            setFilterExceptionsOnly((prev) => !prev);
            if (!filterExceptionsOnly) setSelectedType('all');
          }}
          style={{
            cursor: 'pointer',
            border: filterExceptionsOnly ? '2px solid #dc2626' : undefined,
            background: filterExceptionsOnly ? '#fef2f2' : undefined,
            transition: 'all 0.15s ease',
          }}
          title="Click to toggle filter for active exceptions"
        >
          <div className="stat-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>ACTIVE EXCEPTIONS</span>
            {exceptionCount > 0 && (
              <span
                style={{
                  fontSize: '10px',
                  background: filterExceptionsOnly ? '#dc2626' : '#fee2e2',
                  color: filterExceptionsOnly ? '#ffffff' : '#dc2626',
                  padding: '1px 6px',
                  borderRadius: '4px',
                  fontWeight: 700,
                }}
              >
                {filterExceptionsOnly ? 'FILTERED ON' : 'CLICK TO FILTER'}
              </span>
            )}
          </div>
          <div className="stat-value" style={{ color: exceptionCount > 0 ? '#dc2626' : '#059669' }}>
            {loading ? '—' : exceptionCount}
          </div>
          <div className="stat-sub">{exceptionCount > 0 ? 'Bottlenecks under mitigation' : 'All lanes nominal'}</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">AUTOMATED MITIGATIONS</div>
          <div className="stat-value" style={{ color: '#059669' }}>
            {loading ? '—' : events.length}
          </div>
          <div className="stat-sub">Autonomous resolutions active</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">SUPERVISED HUBS</div>
          <div className="stat-value" style={{ color: '#2563eb' }}>
            4 Nodes
          </div>
          <div className="stat-sub">TMS, WMS, QA & Demand Engine</div>
        </div>
      </div>

      {/* Active Exceptions Under Mitigation Banner */}
      {activeExceptions.length > 0 && (
        <div
          style={{
            background: '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: 'var(--radius-lg)',
            padding: '16px 20px',
            marginBottom: '24px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: '#92400e' }}>
                Active Exceptions ({activeExceptions.length} Bottleneck{activeExceptions.length > 1 ? 's' : ''} Under Autonomous Mitigation)
              </h3>
            </div>
            <button
              onClick={() => {
                setFilterExceptionsOnly((prev) => !prev);
                if (!filterExceptionsOnly) setSelectedType('all');
              }}
              className="btn-secondary"
              style={{
                fontSize: '11px',
                padding: '3px 10px',
                height: '28px',
                background: '#ffffff',
                borderColor: '#fcd34d',
                color: '#92400e',
                fontWeight: 600,
              }}
            >
              {filterExceptionsOnly ? 'Show All Telemetry Events' : 'Filter Telemetry Stream Below'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {activeExceptions.map((ex) => {
              const info = getExceptionSummary(ex);
              return (
                <div
                  key={ex.event_id}
                  style={{
                    background: '#ffffff',
                    border: '1px solid #fef3c7',
                    borderRadius: '6px',
                    padding: '12px 16px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                  }}
                >
                  <div style={{ flex: 1, minWidth: '240px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
                        {info.title}
                      </span>
                      <span style={{ fontSize: '11px', background: '#fef3c7', color: '#b45309', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                        Source: {ex.source_agent}
                      </span>
                      <span style={{ fontSize: '11px', background: '#ecfdf5', color: '#059669', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                        Mitigation Active
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>
                      {info.details}
                    </div>
                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px', fontFamily: 'monospace' }}>
                      Event ID: {ex.event_id} • Reported {formatTimeAgo(ex.timestamp)}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {info.linkTo && (
                      <Link
                        to={info.linkTo}
                        className="btn-secondary"
                        style={{ fontSize: '11px', padding: '4px 10px', height: '28px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        <span>{info.linkText}</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    )}
                    {info.secondaryLinkTo && (
                      <Link
                        to={info.secondaryLinkTo}
                        className="btn-primary"
                        style={{ fontSize: '11px', padding: '4px 10px', height: '28px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        <span>{info.secondaryLinkText}</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Incident Stream & Telemetry Log */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '18px', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity className="w-4 h-4 text-emerald-600" />
            <h2 style={{ fontSize: '15px', fontWeight: 600, margin: 0, color: '#0f172a' }}>
              Live Telemetry & Exception Stream
            </h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <button
                onClick={() => {
                  setFilterExceptionsOnly((prev) => !prev);
                  if (!filterExceptionsOnly) setSelectedType('all');
                }}
                className={`filter-pill ${filterExceptionsOnly ? 'active' : ''}`}
                style={filterExceptionsOnly ? { background: '#dc2626', color: '#ffffff', borderColor: '#dc2626' } : { borderColor: '#fca5a5', color: '#b91c1c', fontWeight: 600 }}
              >
                Exceptions Only ({exceptionCount})
              </button>
              {['all', 'DeliveryDelayed', 'InventoryLow', 'QualityAlertRaised'].map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setSelectedType(t);
                    setFilterExceptionsOnly(false);
                  }}
                  className={`filter-pill ${selectedType === t && !filterExceptionsOnly ? 'active' : ''}`}
                >
                  {t === 'all' ? 'All' : t.replace('Detected', '').replace('Raised', '')}
                </button>
              ))}
            </div>

            <div className="search-box">
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search event type, sensor, ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="search-input"
                style={{ width: '180px' }}
              />
            </div>
          </div>
        </div>

        {/* Events Table */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {filteredEvents.map((ev) => {
            const isExpanded = expandedId === ev.event_id;
            const isException = EXCEPTION_TYPES.includes(ev.event_type);
            const info = getExceptionSummary(ev);

            return (
              <div
                key={ev.event_id}
                style={{
                  background: '#f8fafc',
                  border: isException ? '1px solid #fde68a' : '1px solid #e2e8f0',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px 18px',
                  transition: 'all 0.15s ease',
                }}
              >
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={() => setExpandedId(isExpanded ? null : ev.event_id)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ color: isException ? '#d97706' : '#2563eb' }}>
                      {isException ? <AlertTriangle className="w-4 h-4" /> : <Activity className="w-4 h-4" />}
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 700, fontSize: '13px', color: isException ? '#92400e' : '#0f172a' }}>
                          {isException ? info.title : ev.event_type}
                        </span>
                        {isException && (
                          <span style={{ fontSize: '10px', background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                            {ev.event_type}
                          </span>
                        )}
                        <span style={{ fontSize: '11px', background: '#ffffff', color: '#475569', border: '1px solid #e2e8f0', padding: '2px 8px', borderRadius: '9999px' }}>
                          Source: {ev.source_agent}
                        </span>
                      </div>
                      {isException && (
                        <div style={{ fontSize: '12px', color: '#475569', marginTop: '3px' }}>
                          {info.details}
                        </div>
                      )}
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px', fontFamily: 'monospace' }}>
                        ID: {ev.event_id}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <span style={{ fontSize: '11px', color: '#059669', background: '#ecfdf5', padding: '3px 10px', borderRadius: '9999px', border: '1px solid #a7f3d0', fontWeight: 600 }}>
                      Automated Resolution Active
                    </span>
                    <span style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock className="w-3 h-3 text-slate-400" />
                      {formatTimeAgo(ev.timestamp)}
                    </span>
                    {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                  </div>
                </div>

                {/* Expanded Incident Telemetry & Impact Assessment */}
                {isExpanded && (
                  <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '11px', color: '#475569', fontWeight: 600, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Incident Telemetry & Impact Details
                    </div>
                    <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 'var(--radius-md)', padding: '16px' }}>
                      <BusinessDataView
                        data={ev.payload || {}}
                        layout="grid"
                        emptyMessage="No additional telemetry recorded for this incident."
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {filteredEvents.length === 0 && !loading && (
            <div style={{ textAlign: 'center', padding: '36px', color: '#64748b' }}>
              No incidents or exceptions match current search criteria.
            </div>
          )}
        </div>
      </div>

      {/* Declare Exception Modal */}
      {showDeclareModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 'var(--radius-lg)', padding: '24px', width: '480px', maxWidth: '90%', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 8px 0', color: '#0f172a' }}>
              Declare Supply Chain Exception
            </h2>
            <p style={{ fontSize: '12px', color: '#64748b', margin: '0 0 16px 0' }}>
              Broadcasts an operational incident across fulfillment pipelines for immediate automated remediation.
            </p>

            <form onSubmit={handleDeclareSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Exception Category</label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                >
                  <option value="DeliveryDelayed">DeliveryDelayed (Carrier Delay / Storm)</option>
                  <option value="InventoryLow">InventoryLow (Warehouse Stockout Threat)</option>
                  <option value="QualityAlertRaised">QualityAlertRaised (Component Inspection Failure)</option>
                  <option value="DemandSpikeDetected">DemandSpikeDetected (Regional Demand Surge)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Reporting Sensor / Telemetry Source</label>
                <input
                  type="text"
                  value={formSource}
                  onChange={(e) => setFormSource(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Affected Facility / Checkpoint</label>
                <input
                  type="text"
                  value={formLocation}
                  onChange={(e) => setFormLocation(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px' }}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px', fontWeight: 500 }}>Incident Description & Impact</label>
                <textarea
                  rows={3}
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 'var(--radius-md)', color: '#0f172a', fontSize: '13px', resize: 'vertical' }}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setShowDeclareModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary"
                  style={{ background: '#dc2626' }}
                >
                  {submitting ? 'Broadcasting...' : 'Broadcast Exception'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
