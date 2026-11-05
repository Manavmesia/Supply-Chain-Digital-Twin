import React, { useEffect, useState, useCallback, useRef } from 'react';
import { eventsApi, inventoryApi } from '../services/api';
import type { EventRecord } from '../types';
import {
  formatEventId,
  formatTimeAgo,
} from '../utils/formatters';

export const EventsPage: React.FC = () => {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [eventTypes, setEventTypes] = useState<{ type: string; producer: string; layer: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const isMountedRef = useRef(true);
  const [form, setForm] = useState({
    event_type: 'InventoryLow',
    source_agent: 'manual',
    workflow_id: '',
    payload: '{\n  "sku": "ELEC-001",\n  "quantity": 100\n}',
  });
  const [injecting, setInjecting] = useState(false);
  const [lastInjected, setLastInjected] = useState<string | null>(null);
  const [latestRemediation, setLatestRemediation] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const load = useCallback(async (isSilent = false) => {
    try {
      const [evRes, typesRes] = await Promise.all([
        eventsApi.list({ limit: 50 }),
        eventsApi.getTypes(),
      ]);
      if (isMountedRef.current) {
        setEvents(evRes.items);
        setEventTypes(typesRes.event_types);
        setLastUpdated(new Date());
      }
    } catch (err) {
      console.error('Events load error:', err);
    } finally {
      if (isMountedRef.current && !isSilent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    isMountedRef.current = true;

    Promise.all([
      eventsApi.list({ limit: 50 }),
      eventsApi.getTypes(),
    ]).then(([evRes, typesRes]) => {
      if (!ignore && isMountedRef.current) {
        setEvents(evRes.items);
        setEventTypes(typesRes.event_types);
        setLastUpdated(new Date());
        setLoading(false);
      }
    }).catch((err) => {
      console.error('Events load error:', err);
      if (!ignore && isMountedRef.current) setLoading(false);
    });

    // Live auto-sync every 3 seconds
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        load(true);
      }
    }, 3000);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        load(true);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      ignore = true;
      isMountedRef.current = false;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [load]);

  const inject = async () => {
    setInjecting(true);
    setLatestRemediation(null);
    try {
      let payload: Record<string, unknown> = {};
      try { payload = JSON.parse(form.payload); } catch { /* ignore */ }

      const result = await eventsApi.inject({
        event_type: form.event_type,
        source_agent: form.source_agent || 'manual',
        payload,
        workflow_id: form.workflow_id || undefined,
      });
      setLastInjected(result.event_id);
      if (result.message) {
        setLatestRemediation(result.message);
      }
      await load(false);
    } catch (err) {
      console.error(err);
    } finally {
      setInjecting(false);
    }
  };

  const handleAutonomousScan = async () => {
    setIsScanning(true);
    setScanMessage(null);
    try {
      const res = await inventoryApi.runAutonomousScan();
      if (isMountedRef.current) {
        setScanMessage(res.message);
        await load(true);
      }
    } catch (err) {
      console.error('Scan error:', err);
    } finally {
      if (isMountedRef.current) setIsScanning(false);
    }
  };

  const LAYER_COLORS: Record<string, string> = {
    operational:  '#10b981',
    business:     '#f59e0b',
    coordination: '#8b5cf6',
  };

  return (
    <div className="page-content animate-fade-in">
      <div className="page-header">
        <h1><span className="gradient-text">Event Bus & Autonomous Remediation</span></h1>
        <p>Inject synthetic events, trigger closed-loop multi-agent remediation, and monitor real-time event telemetry</p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleAutonomousScan}
            disabled={isScanning}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: 'linear-gradient(135deg, #2563eb, #7c3aed)' }}
          >
            {isScanning ? <span className="loading-spinner" style={{ width: 12, height: 12 }} /> : '⚡'} Run Autonomous Digital Twin Scan
          </button>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => load(false)}
            disabled={loading}
          >
            ↻ Refresh Stream
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: '#10b981' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 6px #10b981' }} />
            Live Event Stream (3s) • Updated {lastUpdated.toLocaleTimeString()}
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
            <span style={{ fontSize: '1.1rem' }}>🤖</span>
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

      <div className="grid-2">
        {/* Inject form */}
        <div className="card">
          <h3 className="section-title mb-4">⚡ Inject Manual Event</h3>

          <div className="form-group mb-3">
            <label className="form-label">Event Type</label>
            <select
              className="form-select"
              value={form.event_type}
              onChange={(e) => setForm({ ...form, event_type: e.target.value })}
            >
              {eventTypes.map((et) => (
                <option key={et.type} value={et.type}>{et.type}</option>
              ))}
            </select>
          </div>

          <div className="form-group mb-3">
            <label className="form-label">Source Agent (optional)</label>
            <input
              className="form-input"
              value={form.source_agent}
              onChange={(e) => setForm({ ...form, source_agent: e.target.value })}
              placeholder="e.g. ADS-03"
            />
          </div>

          <div className="form-group mb-3">
            <label className="form-label">Workflow Reference (optional)</label>
            <input
              className="form-input"
              value={form.workflow_id}
              onChange={(e) => setForm({ ...form, workflow_id: e.target.value })}
              placeholder="e.g. #WF-63B555BE or leave blank for system-wide"
            />
          </div>

          <div className="form-group mb-4">
            <label className="form-label">Payload (JSON)</label>
            <textarea
              className="form-textarea"
              value={form.payload}
              onChange={(e) => setForm({ ...form, payload: e.target.value })}
              rows={4}
              style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem' }}
            />
          </div>

          {lastInjected && (
            <div className="mb-3" style={{
              padding: '0.875rem',
              background: 'rgba(16,185,129,0.08)',
              border: '1px solid rgba(16,185,129,0.3)',
              borderRadius: '8px',
              fontSize: '0.8125rem',
            }}>
              <div style={{ color: '#10b981', fontWeight: 600, marginBottom: '0.25rem' }}>
                ✅ Event Injected: <code style={{ fontFamily: 'var(--font-mono)' }}>{formatEventId(lastInjected)}</code>
              </div>
              {latestRemediation && (
                <div style={{ color: 'var(--c-text-primary)', fontSize: '0.75rem', marginTop: '0.35rem', lineHeight: '1.4' }}>
                  <span style={{ color: '#60a5fa', fontWeight: 600 }}>🤖 Autonomous Remediation:</span> {latestRemediation}
                </div>
              )}
            </div>
          )}

          <button
            className="btn btn-primary"
            style={{ width: '100%' }}
            onClick={inject}
            disabled={injecting}
          >
            {injecting ? (
              <><span className="loading-spinner" style={{ width: 14, height: 14 }} /> Injecting…</>
            ) : '⚡ Inject Event'}
          </button>
        </div>

        {/* Event type catalogue */}
        <div className="card">
          <h3 className="section-title mb-4">📚 Event Type Catalogue</h3>
          <div style={{ maxHeight: '400px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            {eventTypes.map((et) => (
              <div
                key={et.type}
                className="flex items-center gap-3"
                style={{
                  padding: '0.5rem 0.75rem',
                  background: 'var(--c-bg-subtle)',
                  borderRadius: '6px',
                  border: '1px solid var(--c-border)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                onClick={() => setForm({ ...form, event_type: et.type })}
              >
                <span
                  style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: LAYER_COLORS[et.layer] ?? '#64748b',
                    flexShrink: 0,
                  }}
                />
                <span style={{ fontSize: '0.8125rem', color: 'var(--c-text-primary)', flex: 1 }}>{et.type}</span>
                <span className="tag" style={{ fontSize: '0.65rem' }}>{et.producer}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Event log */}
      <div className="card mt-6 animate-fade-in">
        <div className="section-header">
          <h3 className="section-title">📋 Injected Event Log</h3>
          <button className="btn btn-ghost btn-sm" onClick={() => { setLoading(true); load(false); }} disabled={loading}>
            ↻ Refresh
          </button>
        </div>

        {loading ? (
          <div className="loading-overlay">
            <span className="loading-spinner" style={{ width: 28, height: 28 }} />
          </div>
        ) : events.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">📭</span>
            <p>No events injected yet</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Event Type & Autonomous Remediation</th>
                  <th>Subscribers</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Timeline</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e) => {
                  const isExpanded = expandedEventId === e.event_id;
                  const hasActions = e.autonomous_actions && e.autonomous_actions.length > 0;
                  return (
                    <React.Fragment key={e.event_id}>
                      <tr
                        style={{ cursor: hasActions ? 'pointer' : 'default', background: isExpanded ? 'var(--c-bg-subtle)' : undefined }}
                        onClick={() => hasActions && setExpandedEventId(isExpanded ? null : e.event_id)}
                      >
                        <td>
                          <div>
                            <span style={{ color: 'var(--c-brand-1)', fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', fontWeight: 600 }}>
                              {e.event_type}
                            </span>
                            <span className="tag ml-2" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', marginLeft: '0.5rem' }}>
                              {formatEventId(e.event_id)}
                            </span>
                            {e.remediation_summary && (
                              <div style={{ fontSize: '0.75rem', color: 'var(--c-text-secondary)', marginTop: '0.25rem' }}>
                                <span style={{ color: '#10b981', fontWeight: 600 }}>✦ Remediated:</span> {e.remediation_summary}
                              </div>
                            )}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                            {e.subscribers && e.subscribers.length > 0 ? (
                              e.subscribers.map((sub) => (
                                <span key={sub} className="badge badge-info" style={{ fontSize: '0.65rem' }}>
                                  {sub}
                                </span>
                              ))
                            ) : (
                              <span style={{ color: 'var(--c-text-muted)', fontSize: '0.72rem' }}>—</span>
                            )}
                          </div>
                        </td>
                        <td>
                          <span className="tag">{e.source_agent}</span>
                        </td>
                        <td>
                          <span
                            className="badge"
                            style={{
                              background: e.status === 'replayed' ? 'rgba(59,130,246,0.15)' : 'rgba(16,185,129,0.15)',
                              color: e.status === 'replayed' ? '#60a5fa' : '#10b981',
                              border: e.status === 'replayed' ? '1px solid rgba(59,130,246,0.3)' : '1px solid rgba(16,185,129,0.3)',
                              textTransform: 'uppercase',
                            }}
                          >
                            {e.status}
                          </span>
                        </td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--c-text-muted)' }}>
                          {formatTimeAgo(e.timestamp)}
                        </td>
                        <td>
                          {hasActions && (
                            <button
                              className="btn btn-ghost btn-sm"
                              style={{ fontSize: '0.72rem', padding: '2px 8px' }}
                              onClick={(evt) => {
                                evt.stopPropagation();
                                setExpandedEventId(isExpanded ? null : e.event_id);
                              }}
                            >
                              {isExpanded ? '▲ Hide Trace' : `▼ Actions (${e.autonomous_actions?.length})`}
                            </button>
                          )}
                        </td>
                      </tr>
                      {isExpanded && hasActions && (
                        <tr>
                          <td colSpan={6} style={{ background: 'var(--c-bg-subtle)', padding: '1rem 1.5rem', borderBottom: '1px solid var(--c-border)' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#60a5fa', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                              🤖 Autonomous Multi-Agent Action Log
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                              {e.autonomous_actions?.map((act, idx) => (
                                <div
                                  key={idx}
                                  style={{
                                    display: 'flex',
                                    gap: '0.75rem',
                                    alignItems: 'flex-start',
                                    background: 'var(--c-bg-card)',
                                    border: '1px solid var(--c-border)',
                                    borderRadius: '6px',
                                    padding: '0.5rem 0.75rem',
                                    fontSize: '0.75rem',
                                  }}
                                >
                                  <span className="badge badge-info" style={{ fontWeight: 700, minWidth: '60px', textAlign: 'center' }}>
                                    {act.agent}
                                  </span>
                                  <div style={{ flex: 1 }}>
                                    <div style={{ fontWeight: 600, color: 'var(--c-text-primary)' }}>{act.action}</div>
                                    <div style={{ color: 'var(--c-text-secondary)', marginTop: '0.15rem' }}>{act.details}</div>
                                  </div>
                                  <div style={{ color: 'var(--c-text-muted)', fontSize: '0.7rem' }}>
                                    {act.timestamp ? new Date(act.timestamp).toLocaleTimeString() : ''}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
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
