import React, { useState, useEffect, useCallback, useRef } from 'react';
import { workflowApi } from '../services/api';
import type { WorkflowStatus, AgentTrace } from '../types';

const SAMPLE_CUSTOMER_ID = '50000000-0000-0000-0000-000000000001';
const SAMPLE_PRODUCTS = [
  { id: '30000000-0000-0000-0000-000000000001', name: 'Industrial Sensor Module', sku: 'ELEC-001' },
  { id: '30000000-0000-0000-0000-000000000002', name: 'High-Torque Servo Motor', sku: 'ELEC-002' },
  { id: '30000000-0000-0000-0000-000000000004', name: 'Precision Ball Bearing Set', sku: 'MECH-001' },
  { id: '30000000-0000-0000-0000-000000000009', name: 'Safety Relay Module', sku: 'SAFE-001' },
];

interface OrderItem {
  product_id: string;
  quantity: number;
}

type WorkflowPhase = 'idle' | 'running' | 'completed' | 'failed';

const STATUS_COLORS: Record<string, string> = {
  completed: '#10b981',
  failed: '#ef4444',
  running: '#3b82f6',
  received: '#f59e0b',
};

type TraceTab = 'input' | 'output' | 'decision' | 'events';

const AGENT_LAYER: Record<string, { color: string; label: string }> = {
  'ADS-01': { color: '#3b82f6', label: 'Operational' },
  'ADS-02': { color: '#8b5cf6', label: 'Business' },
  'ADS-03': { color: '#3b82f6', label: 'Operational' },
  'ADS-04': { color: '#3b82f6', label: 'Operational' },
  'ADS-05': { color: '#3b82f6', label: 'Operational' },
  'ADS-06': { color: '#3b82f6', label: 'Operational' },
  'ADS-07': { color: '#3b82f6', label: 'Operational' },
  'ADS-08': { color: '#3b82f6', label: 'Operational' },
  'ADS-09': { color: '#8b5cf6', label: 'Business' },
  'ADS-10': { color: '#8b5cf6', label: 'Business' },
  'ADS-11': { color: '#8b5cf6', label: 'Business' },
  'ADS-12': { color: '#8b5cf6', label: 'Business' },
  'ADS-13': { color: '#8b5cf6', label: 'Business' },
  'ADS-14': { color: '#8b5cf6', label: 'Business' },
  'ADS-15': { color: '#f59e0b', label: 'Coordination' },
  'ADS-16': { color: '#f59e0b', label: 'Coordination' },
  'ADS-17': { color: '#f59e0b', label: 'Coordination' },
  'ADS-18': { color: '#f59e0b', label: 'Coordination' },
};

function JsonBlock({ data }: { data: unknown }) {
  const text = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  return (
    <pre
      style={{
        background: '#020617',
        border: '1px solid #1e293b',
        borderRadius: '8px',
        padding: '1rem',
        fontSize: '0.72rem',
        lineHeight: '1.6',
        color: '#94a3b8',
        overflowX: 'auto',
        maxHeight: '400px',
        overflowY: 'auto',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-all',
        margin: 0,
      }}
    >
      {text}
    </pre>
  );
}

function OutputDiff({ input, output }: { input: Record<string, unknown>; output: Record<string, unknown> }) {
  const changedKeys = Object.keys(output).filter(
    k => JSON.stringify(output[k]) !== JSON.stringify(input[k])
  );
  const unchangedKeys = Object.keys(output).filter(
    k => JSON.stringify(output[k]) === JSON.stringify(input[k])
  );

  return (
    <div>
      {changedKeys.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <p style={{ fontSize: '0.72rem', color: '#10b981', fontWeight: 600, marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            ✦ Changed / Added Keys ({changedKeys.length})
          </p>
          {changedKeys.map(k => (
            <div key={k} style={{ marginBottom: '0.75rem' }}>
              <span style={{
                display: 'inline-block',
                fontSize: '0.68rem',
                background: 'rgba(16,185,129,0.12)',
                color: '#10b981',
                border: '1px solid rgba(16,185,129,0.3)',
                borderRadius: '4px',
                padding: '1px 8px',
                marginBottom: '0.25rem',
                fontFamily: 'monospace',
              }}>{k}</span>
              <JsonBlock data={output[k]} />
            </div>
          ))}
        </div>
      )}
      {unchangedKeys.length > 0 && (
        <details>
          <summary style={{ fontSize: '0.72rem', color: '#475569', cursor: 'pointer', marginBottom: '0.5rem' }}>
            ↳ {unchangedKeys.length} unchanged keys (pass-through from previous state)
          </summary>
          <div style={{ opacity: 0.5 }}>
            {unchangedKeys.map(k => (
              <div key={k} style={{ marginBottom: '0.5rem' }}>
                <span style={{
                  display: 'inline-block',
                  fontSize: '0.68rem',
                  background: 'rgba(71,85,105,0.2)',
                  color: '#64748b',
                  border: '1px solid #1e293b',
                  borderRadius: '4px',
                  padding: '1px 8px',
                  marginBottom: '0.25rem',
                  fontFamily: 'monospace',
                }}>{k}</span>
                <JsonBlock data={output[k]} />
              </div>
            ))}
          </div>
        </details>
      )}
      {changedKeys.length === 0 && unchangedKeys.length === 0 && (
        <p style={{ color: '#475569', fontSize: '0.8rem', fontStyle: 'italic' }}>No output fields captured.</p>
      )}
    </div>
  );
}

interface AgentTracePanelProps { trace: AgentTrace[]; }

function AgentTracePanel({ trace }: AgentTracePanelProps) {
  const [openIdx, setOpenIdx] = React.useState<number | null>(null);
  const [activeTab, setActiveTab] = React.useState<Record<number, TraceTab>>({});
  const [allOpen, setAllOpen] = React.useState(false);

  const maxDuration = Math.max(...trace.map(t => t.duration_ms), 1);

  const getTab = (idx: number): TraceTab => activeTab[idx] ?? 'output';
  const setTab = (idx: number, tab: TraceTab) =>
    setActiveTab(prev => ({ ...prev, [idx]: tab }));

  const toggleAll = () => {
    if (allOpen) {
      setOpenIdx(null);
      setAllOpen(false);
    } else {
      setAllOpen(true);
    }
  };

  const isOpen = (idx: number) => allOpen || openIdx === idx;

  const totalDuration = trace.reduce((s, t) => s + t.duration_ms, 0);
  const completedCount = trace.filter(t => t.status === 'completed').length;
  const failedCount = trace.filter(t => t.status === 'failed').length;

  const TABS: { id: TraceTab; label: string; icon: string }[] = [
    { id: 'output', label: 'Output Diff', icon: '⬆' },
    { id: 'input', label: 'Input State', icon: '⬇' },
    { id: 'decision', label: 'Decision', icon: '⚖' },
    { id: 'events', label: 'Events', icon: '📡' },
  ];

  return (
    <div className="card mt-6 animate-fade-in" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '1.25rem 1.5rem',
        borderBottom: '1px solid #1e293b',
        background: 'rgba(15,23,42,0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
      }}>
        <div className="flex items-center gap-3" style={{ flexWrap: 'wrap' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
            🔬 Exact Agent Trace
          </h3>
          <span className="badge badge-info">{trace.length} agents</span>
          <span style={{ fontSize: '0.72rem', color: '#10b981', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', padding: '2px 8px', borderRadius: '4px' }}>
            ✓ {completedCount} completed
          </span>
          {failedCount > 0 && (
            <span style={{ fontSize: '0.72rem', color: '#ef4444', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', padding: '2px 8px', borderRadius: '4px' }}>
              ✗ {failedCount} failed
            </span>
          )}
          <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
            Total: {totalDuration.toFixed(1)}ms
          </span>
        </div>
        <button
          onClick={toggleAll}
          style={{
            background: 'rgba(59,130,246,0.12)',
            border: '1px solid rgba(59,130,246,0.3)',
            color: '#60a5fa',
            borderRadius: '6px',
            padding: '4px 14px',
            fontSize: '0.75rem',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          {allOpen ? '▲ Collapse All' : '▼ Expand All'}
        </button>
      </div>

      {/* Timeline bar */}
      <div style={{ padding: '0.75rem 1.5rem', borderBottom: '1px solid #0f172a', background: 'rgba(2,6,23,0.6)' }}>
        <p style={{ fontSize: '0.68rem', color: '#475569', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Execution Timeline</p>
        <div style={{ display: 'flex', gap: '2px', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
          {trace.map((t, i) => (
            <div
              key={i}
              title={`${t.agent_code}: ${t.duration_ms}ms`}
              style={{
                flex: `${t.duration_ms}`,
                background: t.status === 'completed'
                  ? (AGENT_LAYER[t.agent_code]?.color ?? '#10b981')
                  : '#ef4444',
                opacity: 0.85,
                cursor: 'pointer',
                transition: 'opacity 0.15s',
              }}
              onClick={() => setOpenIdx(isOpen(i) ? null : i)}
            />
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#334155', marginTop: '0.25rem' }}>
          <span>0ms</span>
          <span>{totalDuration.toFixed(1)}ms</span>
        </div>
      </div>

      {/* Agent rows */}
      <div>
        {trace.map((t, idx) => {
          const layer = AGENT_LAYER[t.agent_code] ?? { color: '#64748b', label: 'Unknown' };
          const pct = (t.duration_ms / maxDuration) * 100;
          const tab = getTab(idx);
          const open = isOpen(idx);
          const eventsWithPayload = (t.events_published as Array<Record<string, unknown>>);
          const outputKeys = Object.keys(t.output || {}).filter(k => !['messages'].includes(k));
          const inputKeys = Object.keys(t.input || {});

          return (
            <div
              key={idx}
              style={{
                borderBottom: '1px solid #0f172a',
                background: open ? 'rgba(15,23,42,0.6)' : 'transparent',
                transition: 'background 0.2s',
              }}
            >
              {/* Row header */}
              <div
                onClick={() => {
                  if (allOpen) { setAllOpen(false); setOpenIdx(open ? null : idx); }
                  else setOpenIdx(open ? null : idx);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                  padding: '0.75rem 1.5rem',
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
              >
                {/* Index */}
                <span style={{
                  fontSize: '0.65rem',
                  fontFamily: 'monospace',
                  color: '#334155',
                  minWidth: '22px',
                  textAlign: 'right',
                }}>
                  {String(idx + 1).padStart(2, '0')}
                </span>

                {/* Status dot */}
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                  background: t.status === 'completed' ? '#10b981' : '#ef4444',
                  boxShadow: t.status === 'completed' ? '0 0 6px #10b98166' : '0 0 6px #ef444466',
                }} />

                {/* Agent code + name */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{
                      fontFamily: 'monospace',
                      fontWeight: 700,
                      fontSize: '0.8rem',
                      color: '#f8fafc',
                    }}>{t.agent_code}</span>
                    <span style={{
                      fontSize: '0.75rem',
                      color: '#94a3b8',
                    }}>{t.agent_name}</span>
                    <span style={{
                      fontSize: '0.62rem',
                      padding: '1px 6px',
                      borderRadius: '3px',
                      background: `${layer.color}18`,
                      color: layer.color,
                      border: `1px solid ${layer.color}40`,
                      fontWeight: 600,
                    }}>{layer.label}</span>
                  </div>
                  {/* Duration mini-bar */}
                  <div style={{ marginTop: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{ flex: 1, height: 3, background: '#0f172a', borderRadius: 2, maxWidth: 200 }}>
                      <div style={{
                        width: `${pct}%`,
                        height: '100%',
                        background: layer.color,
                        borderRadius: 2,
                        opacity: 0.7,
                      }} />
                    </div>
                    <span style={{ fontSize: '0.68rem', color: '#475569', fontFamily: 'monospace' }}>
                      {t.duration_ms}ms
                    </span>
                  </div>
                </div>

                {/* Meta badges */}
                <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexShrink: 0, flexWrap: 'wrap' }}>
                  {t.decision && (
                    <span style={{ fontSize: '0.62rem', padding: '1px 6px', borderRadius: '3px', background: 'rgba(245,158,11,0.12)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.25)' }}>
                      ⚖ decision
                    </span>
                  )}
                  {eventsWithPayload.length > 0 && (
                    <span style={{ fontSize: '0.62rem', padding: '1px 6px', borderRadius: '3px', background: 'rgba(167,139,250,0.12)', color: '#a78bfa', border: '1px solid rgba(167,139,250,0.25)' }}>
                      📡 {eventsWithPayload.length} event{eventsWithPayload.length > 1 ? 's' : ''}
                    </span>
                  )}
                  <span style={{ fontSize: '0.62rem', padding: '1px 6px', borderRadius: '3px', background: 'rgba(96,165,250,0.1)', color: '#60a5fa', border: '1px solid rgba(96,165,250,0.2)' }}>
                    {outputKeys.length}↑ {inputKeys.length}↓ keys
                  </span>
                  <span style={{ color: '#334155', fontSize: '0.7rem' }}>{open ? '▲' : '▼'}</span>
                </div>
              </div>

              {/* Expanded detail */}
              {open && (
                <div style={{ padding: '0 1.5rem 1.5rem' }} className="animate-fade-in">
                  {/* Timestamps */}
                  <div style={{
                    display: 'flex',
                    gap: '1.5rem',
                    fontSize: '0.68rem',
                    color: '#475569',
                    fontFamily: 'monospace',
                    marginBottom: '1rem',
                    padding: '0.5rem 0.75rem',
                    background: 'rgba(0,0,0,0.3)',
                    borderRadius: '6px',
                    flexWrap: 'wrap',
                  }}>
                    <span>▶ Started: <span style={{ color: '#60a5fa' }}>{t.started_at}</span></span>
                    <span>■ Finished: <span style={{ color: '#60a5fa' }}>{t.finished_at}</span></span>
                    <span>⏱ Duration: <span style={{ color: '#10b981', fontWeight: 700 }}>{t.duration_ms}ms</span></span>
                    <span>Status: <span style={{ color: t.status === 'completed' ? '#10b981' : '#ef4444', fontWeight: 700 }}>{t.status}</span></span>
                  </div>

                  {/* Tabs */}
                  <div style={{ display: 'flex', gap: '2px', marginBottom: '1rem', borderBottom: '1px solid #1e293b', paddingBottom: '0' }}>
                    {TABS.map(tb => (
                      <button
                        key={tb.id}
                        onClick={() => setTab(idx, tb.id)}
                        style={{
                          background: tab === tb.id ? 'rgba(59,130,246,0.15)' : 'transparent',
                          border: 'none',
                          borderBottom: tab === tb.id ? '2px solid #3b82f6' : '2px solid transparent',
                          color: tab === tb.id ? '#60a5fa' : '#475569',
                          padding: '0.4rem 1rem',
                          fontSize: '0.75rem',
                          cursor: 'pointer',
                          fontWeight: tab === tb.id ? 600 : 400,
                          borderRadius: '4px 4px 0 0',
                          transition: 'all 0.15s',
                        }}
                      >
                        {tb.icon} {tb.label}
                      </button>
                    ))}
                  </div>

                  {/* Tab content */}
                  {tab === 'output' && (
                    <OutputDiff
                      input={t.input as Record<string, unknown>}
                      output={t.output as Record<string, unknown>}
                    />
                  )}

                  {tab === 'input' && (
                    <div>
                      <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                        Full state snapshot this agent received ({inputKeys.length} keys):
                      </p>
                      <JsonBlock data={t.input} />
                    </div>
                  )}

                  {tab === 'decision' && (
                    t.decision ? (
                      <div>
                        <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                          Decision recorded by this agent on the shared state:
                        </p>
                        <JsonBlock data={t.decision} />
                      </div>
                    ) : (
                      <p style={{ color: '#334155', fontSize: '0.8rem', fontStyle: 'italic', padding: '0.5rem 0' }}>
                        This agent did not record a decision (pass-through or coordination node).
                      </p>
                    )
                  )}

                  {tab === 'events' && (
                    eventsWithPayload.length > 0 ? (
                      <div>
                        <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
                          {eventsWithPayload.length} event{eventsWithPayload.length > 1 ? 's' : ''} published by this agent to the event bus:
                        </p>
                        {eventsWithPayload.map((ev, ei) => (
                          <div key={ei} style={{ marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                              <span style={{ fontSize: '0.68rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(167,139,250,0.15)', color: '#a78bfa', border: '1px solid rgba(167,139,250,0.3)', fontFamily: 'monospace', fontWeight: 700 }}>
                                {String(ev['event_type'] ?? '?')}
                              </span>
                              {ev['timestamp'] && (
                                <span style={{ fontSize: '0.65rem', color: '#334155', fontFamily: 'monospace' }}>
                                  @ {String(ev['timestamp'])}
                                </span>
                              )}
                            </div>
                            <JsonBlock data={ev['payload'] ?? ev} />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ color: '#334155', fontSize: '0.8rem', fontStyle: 'italic', padding: '0.5rem 0' }}>
                        No events published by this agent.
                      </p>
                    )
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const WorkflowPage: React.FC = () => {

  const [customerId, setCustomerId] = useState(SAMPLE_CUSTOMER_ID);
  const [items, setItems] = useState<OrderItem[]>([
    { product_id: SAMPLE_PRODUCTS[0].id, quantity: 5 },
  ]);
  const [phase, setPhase] = useState<WorkflowPhase>('idle');
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [trace, setTrace] = useState<AgentTrace[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const poll = useCallback(async (id: string) => {
    try {
      const [statusRes, traceRes] = await Promise.all([
        workflowApi.getStatus(id),
        workflowApi.getTrace(id),
      ]);
      setStatus(statusRes);
      setTrace(traceRes.traces);

      const done = ['completed', 'failed'].includes(statusRes.workflow_status);
      if (done) {
        stopPolling();
        setPhase(statusRes.workflow_status === 'completed' ? 'completed' : 'failed');
      }
    } catch (err) {
      console.error('Polling failed:', err);
    }
  }, [stopPolling]);

  const submit = async () => {
    if (!customerId || items.length === 0) return;
    setError(null);
    setPhase('running');
    setStatus(null);
    setTrace([]);
    stopPolling();

    try {
      const accepted = await workflowApi.start({
        customer_id: customerId,
        items,
      });
      setWorkflowId(accepted.workflow_id);
      // Start polling every 2s
      pollRef.current = setInterval(() => poll(accepted.workflow_id), 2000);
      // Initial poll
      poll(accepted.workflow_id);
    } catch (err) {
      setError((err as Error).message);
      setPhase('failed');
    }
  };

  const handleOverride = async (topic: string, action: 'pin' | 'revert', value: any) => {
    if (!workflowId) return;
    try {
      setError(null);
      await workflowApi.overrideDecision(workflowId, {
        topic,
        action,
        value,
      });
      // Reset phase to running and resume polling
      setPhase('running');
      stopPolling();
      pollRef.current = setInterval(() => poll(workflowId), 2000);
      poll(workflowId);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => () => stopPolling(), [stopPolling]);

  const addItem = () =>
    setItems((prev) => [...prev, { product_id: SAMPLE_PRODUCTS[0].id, quantity: 1 }]);

  const removeItem = (idx: number) =>
    setItems((prev) => prev.filter((_, i) => i !== idx));

  const updateItem = (idx: number, field: 'product_id' | 'quantity', val: string) =>
    setItems((prev) =>
      prev.map((item, i) =>
        i === idx ? { ...item, [field]: field === 'quantity' ? parseInt(val, 10) : val } : item,
      ),
    );

  return (
    <div className="page-content animate-fade-in">
      <div className="page-header">
        <h1><span className="gradient-text">Workflow Management</span></h1>
        <p>Submit orders to the 18-agent pipeline and watch decisions in real time</p>
      </div>

      <div className="grid-2">
        {/* Submit form */}
        <div className="card">
          <h3 className="section-title mb-4">🛒 New Order Workflow</h3>

          <div className="form-group mb-4">
            <label className="form-label">Customer ID</label>
            <input
              className="form-input"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              placeholder="UUID of customer"
            />
            <p style={{ fontSize: '0.75rem', color: '#475569', marginTop: '0.25rem' }}>
              Try: <code style={{ color: '#60a5fa' }}>{SAMPLE_CUSTOMER_ID}</code> (Siemens — Enterprise)
            </p>
          </div>

          <div className="form-group mb-4">
            <label className="form-label">Order Items</label>
            {items.map((item, i) => (
              <div key={i} className="flex gap-2 mb-2 items-center">
                <select
                  className="form-select flex-1"
                  value={item.product_id}
                  onChange={(e) => updateItem(i, 'product_id', e.target.value)}
                >
                  {SAMPLE_PRODUCTS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} — {p.name}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  className="form-input"
                  style={{ width: '80px' }}
                  value={item.quantity}
                  min={1}
                  onChange={(e) => updateItem(i, 'quantity', e.target.value)}
                />
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => removeItem(i)}
                  disabled={items.length === 1}
                >✕</button>
              </div>
            ))}
            <button className="btn btn-ghost btn-sm mt-2" onClick={addItem}>
              + Add Item
            </button>
          </div>

          {error && (
            <div className="alert-error mb-4">
              ⚠️ {error}
            </div>
          )}

          <button
            className="btn btn-primary"
            style={{ width: '100%' }}
            onClick={submit}
            disabled={phase === 'running'}
          >
            {phase === 'running' ? (
              <><span className="loading-spinner" style={{ width: 16, height: 16 }} /> Running 18-Agent Pipeline…</>
            ) : '🚀 Start Workflow'}
          </button>
        </div>

        {/* Status panel */}
        <div className="card flex flex-col justify-between">
          <div>
            <h3 className="section-title mb-4">📡 Workflow Status</h3>
            {phase === 'idle' && !workflowId && (
              <div className="empty-state">
                <span className="empty-icon">⚡</span>
                <p>Submit an order to start the workflow</p>
              </div>
            )}

            {workflowId && (
              <div>
                <div className="flex gap-2 items-center mb-4">
                  <span className="badge badge-info">ID: {workflowId.slice(0, 12)}…</span>
                  {status && (
                    <span
                      className="badge"
                      style={{
                        background: `${STATUS_COLORS[status.workflow_status] ?? '#64748b'}22`,
                        color: STATUS_COLORS[status.workflow_status] ?? '#64748b',
                        border: `1px solid ${STATUS_COLORS[status.workflow_status] ?? '#64748b'}44`,
                      }}
                    >
                      {status.workflow_status}
                    </span>
                  )}
                </div>

                {/* Agent progress */}
                {status && (
                  <div className="mb-4">
                    <p className="form-label mb-2">
                      Agents executed: {status.active_agents.length} / 17
                    </p>
                    <div className="progress-bar">
                      <div
                        className="progress-bar-fill"
                        style={{ width: `${(status.active_agents.length / 17) * 100}%` }}
                      />
                    </div>
                    <div className="flex gap-1 mt-2" style={{ flexWrap: 'wrap' }}>
                      {status.active_agents.map((code) => (
                        <span key={code} className="tag" style={{ color: '#10b981' }}>{code}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {status?.workflow_status === 'escalated' && (
            <div className="alert-error" style={{ background: 'rgba(245,158,11,0.08)', borderColor: '#f59e0b', color: '#f59e0b' }}>
              <strong>⚠️ Consensus Escalated</strong>
              <p style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                Unresolved objections detected on the blackboard. The system is awaiting user intervention below.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Versioned Blackboard Monitor */}
      {status?.blackboard && Object.keys(status.blackboard).length > 0 && (
        <div className="card mt-6 animate-fade-in">
          <h3 className="section-title mb-4">🎛️ Shared Blackboard Store & Override Control</h3>
          <p className="form-label mb-4" style={{ color: '#94a3b8' }}>
            All peer agents read/write to this decentralized board. Objections flag topics as <span style={{ color: '#f59e0b', fontWeight: 'bold' }}>contested</span>.
          </p>
          <div className="grid-1 gap-4">
            {Object.entries(status.blackboard).map(([topic, entries]) => {
              const latest = entries[entries.length - 1];
              if (!latest) return null;

              const isContested = latest.status === 'contested';
              const isAccepted = latest.status === 'accepted';
              const isPinned = latest.agent_id === 'human_override';

              return (
                <div 
                  key={topic} 
                  className="flex justify-between items-center p-4 rounded-lg"
                  style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: `1px solid ${isContested ? '#f59e0b' : isAccepted ? '#10b981' : '#334155'}`,
                  }}
                >
                  <div className="flex-1">
                    <div className="flex gap-2 items-center">
                      <strong className="capitalize text-lg" style={{ color: '#f8fafc' }}>{topic}</strong>
                      <span 
                        className="badge" 
                        style={{
                          fontSize: '0.7rem',
                          background: isContested ? 'rgba(245,158,11,0.15)' : isAccepted ? 'rgba(16,185,129,0.15)' : 'rgba(59,130,246,0.15)',
                          color: isContested ? '#f59e0b' : isAccepted ? '#10b981' : '#3b82f6',
                          borderColor: isContested ? '#f59e0b44' : isAccepted ? '#10b98144' : '#3b82f644',
                        }}
                      >
                        {latest.status}
                      </span>
                      {isPinned && <span className="tag" style={{ color: '#60a5fa' }}>PINNED BY USER</span>}
                    </div>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                      <strong>Agent:</strong> {latest.agent_id} • <strong>Confidence:</strong> {(latest.confidence * 100).toFixed(0)}%
                    </p>
                    <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '0.5rem', fontStyle: 'italic' }}>
                      &ldquo;{latest.rationale || 'No explanation provided.'}&rdquo;
                    </p>
                    <details className="mt-2">
                      <summary style={{ cursor: 'pointer', fontSize: '0.75rem', color: '#60a5fa' }}>View Proposal Payload</summary>
                      <pre className="code-block mt-2" style={{ fontSize: '0.75rem' }}>
                        {JSON.stringify(latest.data, null, 2)}
                      </pre>
                    </details>
                  </div>

                  <div className="flex flex-col gap-2 justify-end items-end ml-4">
                    {isContested && (
                      <button 
                        className="btn btn-primary btn-sm"
                        onClick={() => handleOverride(topic, 'pin', latest.data)}
                      >
                        📌 Approve (Override)
                      </button>
                    )}
                    {isPinned && (
                      <button 
                        className="btn btn-danger btn-sm"
                        onClick={() => handleOverride(topic, 'revert', {})}
                      >
                        ↩ Revert Override
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}


      {/* Agent Trace — Full Exact Tracing */}
      {trace.length > 0 && (
        <AgentTracePanel trace={trace} />
      )}
    </div>
  );
};
