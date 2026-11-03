import React, { useEffect, useState } from 'react';
import { eventsApi } from '../services/api';
import type { EventRecord } from '../types';
import {
  formatEventId,
  formatWorkflowId,
  formatTimeAgo,
} from '../utils/formatters';

export const EventsPage: React.FC = () => {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [eventTypes, setEventTypes] = useState<{ type: string; producer: string; layer: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    event_type: 'InventoryLow',
    source_agent: 'manual',
    workflow_id: '',
    payload: '{}',
  });
  const [injecting, setInjecting] = useState(false);
  const [lastInjected, setLastInjected] = useState<string | null>(null);

  const load = async () => {
    try {
      const [evRes, typesRes] = await Promise.all([
        eventsApi.list({ limit: 50 }),
        eventsApi.getTypes(),
      ]);
      setEvents(evRes.items);
      setEventTypes(typesRes.event_types);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const inject = async () => {
    setInjecting(true);
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
      setLoading(true);
      await load();
    } catch (err) {
      console.error(err);
    } finally {
      setInjecting(false);
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
        <h1><span className="gradient-text">Event Bus Monitor</span></h1>
        <p>Inject synthetic events and monitor the supply chain event stream</p>
      </div>

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
              padding: '0.75rem',
              background: 'rgba(16,185,129,0.1)',
              border: '1px solid rgba(16,185,129,0.3)',
              borderRadius: '8px',
              fontSize: '0.8125rem',
              color: '#10b981',
            }}>
              ✅ Event injected: <code style={{ fontFamily: 'var(--font-mono)' }}>{formatEventId(lastInjected)}</code>
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
          <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
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
                  <th>Event Type</th>
                  <th>Event Ref</th>
                  <th>Source Agent</th>
                  <th>Status</th>
                  <th>Timeline</th>
                  <th>Linked Workflow</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.event_id}>
                    <td>
                      <span style={{ color: 'var(--c-brand-1)', fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', fontWeight: 600 }}>
                        {e.event_type}
                      </span>
                    </td>
                    <td>
                      <span className="tag" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>
                        {formatEventId(e.event_id)}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-info">{e.source_agent}</span>
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
                      {e.workflow_id ? (
                        <a
                          href={`/workflow?id=${e.workflow_id}`}
                          className="tag"
                          style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', textDecoration: 'none' }}
                        >
                          {formatWorkflowId(e.workflow_id)} ↗
                        </a>
                      ) : (
                        <span style={{ color: 'var(--c-text-muted)', fontSize: '0.75rem' }}>System-Wide</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
