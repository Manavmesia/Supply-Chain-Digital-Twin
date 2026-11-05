import React, { useEffect, useState, useCallback, useRef } from 'react';
import { eventsApi, inventoryApi } from '../services/api';
import type { EventRecord } from '../types';
import {
  ShieldAlert,
  AlertTriangle,
  Zap,
  Activity,
  Radio,
  Search,
  Plus,
  ChevronDown,
  ChevronRight,
  Truck,
  Box,
  Clock,
  Sparkles,
} from 'lucide-react';
import { formatTimeAgo } from '../utils/formatters';

const INCIDENT_TEMPLATES = [
  {
    type: 'DeliveryDelayed',
    label: 'Carrier Logistics Disruption',
    source: 'TMS-Sensor',
    defaultPayload: { carrier: 'Global Intermodal Logistics', route: 'North Atlantic', delay_hours: 48, reason: 'Severe maritime weather cell' },
    icon: <Truck className="w-4 h-4 text-slate-600" />,
    badgeColor: '#2563eb',
  },
  {
    type: 'InventoryLow',
    label: 'Safety Stock Critical Breach',
    source: 'WMS-Telemetry',
    defaultPayload: { sku: 'ELEC-001', warehouse: 'Newark Distribution Center', current_qty: 15, safety_stock: 100 },
    icon: <Box className="w-4 h-4 text-slate-600" />,
    badgeColor: '#dc2626',
  },
  {
    type: 'QualityAlertRaised',
    label: 'Batch QA Defect Alert',
    source: 'ADS-14',
    defaultPayload: { batch_id: 'BATCH-2026-981', defect_rate: '6.4%', inspection_node: 'Inbound Dock 2' },
    icon: <ShieldAlert className="w-4 h-4 text-slate-600" />,
    badgeColor: '#d97706',
  },
  {
    type: 'DemandSpikeDetected',
    label: 'Demand Anomaly (+250%)',
    source: 'ADS-02',
    defaultPayload: { sku: 'ELEC-003', region: 'North America', multiplier: 2.5 },
    icon: <Activity className="w-4 h-4 text-slate-600" />,
    badgeColor: '#475569',
  },
];

export const ControlTowerPage: React.FC = () => {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showDeclareModal, setShowDeclareModal] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Modal form states
  const [formType, setFormType] = useState(INCIDENT_TEMPLATES[0].type);
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

  const handleQuickTrigger = async (tpl: typeof INCIDENT_TEMPLATES[0]) => {
    try {
      const res = await eventsApi.inject({
        event_type: tpl.type,
        source_agent: tpl.source,
        payload: tpl.defaultPayload,
      });
      const rem = res.remediation?.remediation_summary || 'Autonomous multi-agent remediation executed.';
      setActionNotice(`Exception reported: ${tpl.label}. ${rem}`);
      await loadEvents(true);
    } catch (err: any) {
      alert(`Exception report failed: ${err.message}`);
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
      setActionNotice(`Exception logged! ${rem}`);
      await loadEvents(true);
    } catch (err: any) {
      alert(`Declaration failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredEvents = events.filter((ev) => {
    if (selectedType !== 'all' && ev.event_type !== selectedType) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchType = ev.event_type.toLowerCase().includes(q);
      const matchSource = ev.source_agent.toLowerCase().includes(q);
      const matchId = ev.event_id.toLowerCase().includes(q);
      return matchType || matchSource || matchId;
    }
    return true;
  });

  return (
    <div style={{ padding: '28px', maxWidth: '1440px', margin: '0 auto', color: '#0f172a' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0, letterSpacing: '-0.02em', color: '#0f172a' }}>
              Supply Chain Control Tower
            </h1>
            <span style={{ fontSize: '11px', background: '#fef2f2', color: '#dc2626', padding: '3px 8px', borderRadius: '4px', border: '1px solid #fecaca', fontWeight: 600 }}>
              Live Incident Cockpit
            </span>
          </div>
          <p style={{ color: '#64748b', fontSize: '13px', margin: '4px 0 0 0' }}>
            Closed-loop multi-agent exception handling, disruption mitigation, and automated event audit trail.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleAutonomousScan}
            disabled={isScanning}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              color: '#0f172a',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 600,
            }}
          >
            <Sparkles className={`w-3.5 h-3.5 text-amber-500 ${isScanning ? 'animate-spin' : ''}`} />
            {isScanning ? 'Scanning Network...' : 'Run Autonomous Scan'}
          </button>
          <button
            onClick={() => setShowDeclareModal(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              background: '#dc2626',
              border: 'none',
              borderRadius: '6px',
              color: '#ffffff',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <Plus className="w-4 h-4" />
            Declare Exception
          </button>
        </div>
      </div>

      {actionNotice && (
        <div style={{ marginBottom: '20px', padding: '12px 16px', borderRadius: '8px', background: '#eff6ff', border: '1px solid #bfdbfe', color: '#1d4ed8', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap className="w-4 h-4 text-blue-600 flex-shrink-0" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* Quick Incident Triggers / Exception Playbooks */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontSize: '12px', color: '#475569', fontWeight: 600, textTransform: 'uppercase', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Radio className="w-3.5 h-3.5 text-red-600 animate-pulse" />
          Autonomous Exception Playbooks (One-Click Multi-Agent Resolution)
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
          {INCIDENT_TEMPLATES.map((tpl) => (
            <div
              key={tpl.type}
              style={{
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '16px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  {tpl.icon}
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>{tpl.label}</span>
                </div>
                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '12px', lineHeight: 1.4 }}>
                  Triggers closed-loop consensus remediation across subscribed ADS agents.
                </div>
              </div>
              <button
                onClick={() => handleQuickTrigger(tpl)}
                style={{
                  padding: '7px 10px',
                  background: '#f8fafc',
                  border: '1px solid #cbd5e1',
                  borderRadius: '5px',
                  color: '#475569',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '4px',
                }}
              >
                <span>Trigger Remediation</span>
                <ChevronRight className="w-3 h-3 text-slate-400" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Incident Stream & Telemetry Log */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '18px', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity className="w-4 h-4 text-emerald-600" />
            <h2 style={{ fontSize: '15px', fontWeight: 600, margin: 0, color: '#0f172a' }}>
              Live Telemetry & Exception Stream
            </h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ display: 'flex', gap: '4px' }}>
              {['all', 'DeliveryDelayed', 'InventoryLow', 'QualityAlertRaised'].map((t) => (
                <button
                  key={t}
                  onClick={() => setSelectedType(t)}
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: selectedType === t ? 600 : 400,
                    border: '1px solid',
                    borderColor: selectedType === t ? '#bfdbfe' : '#cbd5e1',
                    background: selectedType === t ? '#eff6ff' : '#ffffff',
                    color: selectedType === t ? '#2563eb' : '#475569',
                    cursor: 'pointer',
                  }}
                >
                  {t === 'all' ? 'All' : t.replace('Detected', '').replace('Raised', '')}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#f8fafc', borderRadius: '6px', padding: '6px 12px', border: '1px solid #cbd5e1' }}>
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search event type, agent, ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ background: 'transparent', border: 'none', outline: 'none', color: '#0f172a', fontSize: '12px', width: '200px' }}
              />
            </div>
          </div>
        </div>

        {/* Events Table */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {filteredEvents.map((ev) => {
            const isExpanded = expandedId === ev.event_id;
            const isException = ['DeliveryDelayed', 'InventoryLow', 'QualityAlertRaised', 'CarrierDelayed'].includes(ev.event_type);

            return (
              <div
                key={ev.event_id}
                style={{
                  background: '#f8fafc',
                  border: isException ? '1px solid #fde68a' : '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '12px 16px',
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
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 700, fontSize: '13px', color: '#0f172a' }}>
                          {ev.event_type}
                        </span>
                        <span style={{ fontSize: '11px', background: '#ffffff', color: '#475569', border: '1px solid #e2e8f0', padding: '2px 6px', borderRadius: '4px' }}>
                          Source: {ev.source_agent}
                        </span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px', fontFamily: 'monospace' }}>
                        ID: {ev.event_id}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <span style={{ fontSize: '11px', color: '#059669', background: '#ecfdf5', padding: '2px 8px', borderRadius: '4px', border: '1px solid #a7f3d0', fontWeight: 600 }}>
                      Closed-Loop Remediated
                    </span>
                    <span style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock className="w-3 h-3 text-slate-400" />
                      {formatTimeAgo(ev.timestamp)}
                    </span>
                    {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                  </div>
                </div>

                {/* Expanded Payload & Multi-Agent Consensus */}
                {isExpanded && (
                  <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '11px', color: '#475569', fontWeight: 600, marginBottom: '6px' }}>
                      EVENT TELEMETRY PAYLOAD:
                    </div>
                    <pre
                      style={{
                        background: '#ffffff',
                        border: '1px solid #e2e8f0',
                        padding: '10px 14px',
                        borderRadius: '5px',
                        fontSize: '11px',
                        fontFamily: 'monospace',
                        color: '#0f172a',
                        margin: '0 0 10px 0',
                        overflowX: 'auto',
                      }}
                    >
                      {JSON.stringify(ev.payload || {}, null, 2)}
                    </pre>
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
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '24px', width: '480px', maxWidth: '90%', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 8px 0', color: '#0f172a' }}>
              Declare Supply Chain Exception
            </h2>
            <p style={{ fontSize: '12px', color: '#64748b', margin: '0 0 16px 0' }}>
              Broadcasts a real operational incident to the 18 autonomous LangGraph agents for immediate remediation.
            </p>

            <form onSubmit={handleDeclareSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px' }}>Exception Category</label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '5px', color: '#0f172a', fontSize: '13px' }}
                >
                  <option value="DeliveryDelayed">DeliveryDelayed (Carrier Delay / Storm)</option>
                  <option value="InventoryLow">InventoryLow (Warehouse Stockout Threat)</option>
                  <option value="QualityAlertRaised">QualityAlertRaised (Component Inspection Failure)</option>
                  <option value="DemandSpikeDetected">DemandSpikeDetected (Regional Demand Surge)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px' }}>Reporting Sensor / Telemetry Source</label>
                <input
                  type="text"
                  value={formSource}
                  onChange={(e) => setFormSource(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '5px', color: '#0f172a', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px' }}>Affected Facility / Checkpoint</label>
                <input
                  type="text"
                  value={formLocation}
                  onChange={(e) => setFormLocation(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '5px', color: '#0f172a', fontSize: '13px' }}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#475569', marginBottom: '4px' }}>Incident Description & Impact</label>
                <textarea
                  rows={3}
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '5px', color: '#0f172a', fontSize: '13px', resize: 'vertical' }}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setShowDeclareModal(false)}
                  style={{ padding: '8px 14px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '5px', color: '#475569', cursor: 'pointer', fontSize: '13px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  style={{ padding: '8px 18px', background: '#dc2626', border: 'none', borderRadius: '5px', color: '#ffffff', fontWeight: 600, cursor: 'pointer', fontSize: '13px' }}
                >
                  {submitting ? 'Broadcasting...' : 'Broadcast to Agents'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
