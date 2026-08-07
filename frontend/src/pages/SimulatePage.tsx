import React, { useState, useEffect, useRef } from 'react';
import { simulateApi } from '../services/api';
import type { SimulationResult } from '../types';

const SAMPLE_CUSTOMER = '50000000-0000-0000-0000-000000000001';
const SAMPLE_ITEMS = [{ product_id: '30000000-0000-0000-0000-000000000001', quantity: 10 }];

const SCENARIOS = [
  {
    type: 'demand_spike',
    icon: '📈',
    title: 'Demand Spike',
    desc: '2× demand — tests inventory strain and supplier fallback',
    color: '#3b82f6',
  },
  {
    type: 'supplier_outage',
    icon: '🏭',
    title: 'Supplier Outage',
    desc: 'Primary supplier unavailable — tests alternate sourcing logic',
    color: '#ef4444',
  },
  {
    type: 'logistics_delay',
    icon: '🚢',
    title: 'Logistics Delay',
    desc: 'Doubled transit days — triggers risk escalation and CEO review',
    color: '#f59e0b',
  },
  {
    type: 'bulk_order',
    icon: '📦',
    title: 'Bulk Order',
    desc: 'High-value enterprise order — tests finance thresholds and CEO approval',
    color: '#8b5cf6',
  },
  {
    type: 'quality_crisis',
    icon: '⚠️',
    title: 'Quality Crisis',
    desc: 'All QA batches fail — triggers manufacturing reorder path',
    color: '#10b981',
  },
];

export const SimulatePage: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'failed'>('idle');
  const [recentSims, setRecentSims] = useState<SimulationResult[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  useEffect(() => {
    simulateApi.list(10).then((res) => setRecentSims(res.items));
    return () => stopPoll();
  }, []);

  const runSimulation = async () => {
    if (!selectedScenario) return;
    setStatus('running');
    setResult(null);
    stopPoll();

    try {
      const accepted = await simulateApi.run({
        scenario_type: selectedScenario,
        customer_id: SAMPLE_CUSTOMER,
        items: SAMPLE_ITEMS,
      });
      setSimulationId(accepted.simulation_id);

      pollRef.current = setInterval(async () => {
        const r = await simulateApi.getResult(accepted.simulation_id);
        if (r.status === 'completed' || r.status === 'failed') {
          stopPoll();
          setResult(r);
          setStatus(r.status === 'completed' ? 'done' : 'failed');
        }
      }, 2000);
    } catch (err) {
      setStatus('failed');
    }
  };

  const scenarioInfo = SCENARIOS.find((s) => s.type === selectedScenario);

  return (
    <div className="page-content animate-fade-in">
      <div className="page-header">
        <h1><span className="gradient-text">What-If Simulator</span></h1>
        <p>Run scenario simulations through the full 18-agent pipeline to test system resilience</p>
      </div>

      <div className="grid-2">
        {/* Scenario picker */}
        <div>
          <div className="card mb-4">
            <h3 className="section-title mb-4">🎮 Choose a Scenario</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {SCENARIOS.map((s) => (
                <div
                  key={s.type}
                  className="scenario-card"
                  style={{
                    borderColor: selectedScenario === s.type ? s.color : 'rgba(56,90,155,0.22)',
                    background: selectedScenario === s.type ? `${s.color}10` : 'rgba(12,18,32,0.5)',
                    cursor: 'pointer',
                    padding: '1rem',
                    borderRadius: '10px',
                    border: '1px solid',
                    transition: 'all 0.2s ease',
                  }}
                  onClick={() => setSelectedScenario(s.type)}
                >
                  <div className="flex items-center gap-3">
                    <span style={{ fontSize: '1.5rem' }}>{s.icon}</span>
                    <div>
                      <p style={{ fontWeight: 600, color: selectedScenario === s.type ? s.color : '#f0f4ff' }}>
                        {s.title}
                      </p>
                      <p style={{ fontSize: '0.8rem', color: '#64748b' }}>{s.desc}</p>
                    </div>
                    {selectedScenario === s.type && (
                      <span style={{ marginLeft: 'auto', color: s.color }}>✓</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <button
              className="btn btn-primary mt-4"
              style={{ width: '100%' }}
              onClick={runSimulation}
              disabled={!selectedScenario || status === 'running'}
            >
              {status === 'running' ? (
                <><span className="loading-spinner" style={{ width: 16, height: 16 }} /> Simulating…</>
              ) : `⚡ Run "${scenarioInfo?.title ?? 'Scenario'}" Simulation`}
            </button>
          </div>

          {/* Recent simulations */}
          <div className="card">
            <h3 className="section-title mb-3">🕐 Recent Simulations</h3>
            {recentSims.length === 0 ? (
              <p style={{ color: '#475569', fontSize: '0.875rem' }}>No simulations run yet</p>
            ) : (
              recentSims.map((s) => (
                <div
                  key={s.simulation_id}
                  className="flex justify-between items-center"
                  style={{ padding: '0.5rem 0', borderBottom: '1px solid rgba(56,90,155,0.1)' }}
                >
                  <div>
                    <span style={{ fontSize: '0.875rem', color: '#f0f4ff' }}>
                      {s.scenario_type.replace('_', ' ')}
                    </span>
                    <p style={{ fontSize: '0.75rem', color: '#475569' }}>
                      {s.agents_executed} agents executed
                    </p>
                  </div>
                  <span
                    className="badge"
                    style={{
                      background: s.status === 'completed' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                      color: s.status === 'completed' ? '#10b981' : '#ef4444',
                      border: `1px solid ${s.status === 'completed' ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
                    }}
                  >
                    {s.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Results panel */}
        <div className="card">
          <h3 className="section-title mb-4">📊 Simulation Results</h3>

          {status === 'idle' && !simulationId && (
            <div className="empty-state">
              <span className="empty-icon">🔬</span>
              <p>Select a scenario and run simulation</p>
              <p style={{ fontSize: '0.8rem', color: '#475569' }}>
                Results will appear here in real time
              </p>
            </div>
          )}

          {status === 'running' && (
            <div className="loading-overlay">
              <span className="loading-spinner" style={{ width: 40, height: 40 }} />
              <p>Running 18-agent pipeline…</p>
              <p style={{ fontSize: '0.8rem', color: '#475569' }}>
                Simulation ID: {simulationId?.slice(0, 12)}…
              </p>
            </div>
          )}

          {result && result.summary && (
            <div className="animate-fade-in">
              <div className="mb-4">
                <div className="flex gap-2 flex-wrap mb-3">
                  <span className="badge badge-success">{result.agents_executed} agents executed</span>
                  <span className="tag">{result.scenario_type.replace('_', ' ')}</span>
                </div>
              </div>

              <div className="grid-2" style={{ gap: '0.75rem', marginBottom: '1.25rem' }}>
                {[
                  { label: 'Workflow Status', value: result.summary.workflow_status, color: '#10b981' },
                  { label: 'Order Status',    value: result.summary.order_status ?? '—',    color: '#3b82f6' },
                  { label: 'Risk Level',      value: result.summary.risk_level ?? '—',      color: '#f59e0b' },
                  { label: 'Risk Score',      value: result.summary.risk_score != null ? String(result.summary.risk_score) : '—', color: '#ef4444' },
                  { label: 'CEO Approved',    value: result.summary.ceo_approved != null ? (result.summary.ceo_approved ? 'Yes ✅' : 'No ❌') : '—', color: result.summary.ceo_approved ? '#10b981' : '#ef4444' },
                  { label: 'Carrier',         value: result.summary.carrier ?? '—',         color: '#8b5cf6' },
                  { label: 'Decisions Made',  value: String(result.summary.decision_count ?? 0),  color: '#06b6d4' },
                  { label: 'Events Fired',    value: String(result.summary.event_count ?? 0),    color: '#06b6d4' },
                ].map(({ label, value, color }) => (
                  <div
                    key={label}
                    style={{
                      background: 'rgba(12,18,32,0.6)',
                      border: '1px solid rgba(56,90,155,0.2)',
                      borderRadius: '8px',
                      padding: '0.75rem',
                    }}
                  >
                    <p style={{ fontSize: '0.7rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      {label}
                    </p>
                    <p style={{ color, fontWeight: 600, marginTop: '0.25rem' }}>{value}</p>
                  </div>
                ))}
              </div>

              <div className="divider" />

              <h4 style={{ marginBottom: '0.75rem' }}>
                Agent Execution Trace ({result.trace.length})
              </h4>
              <div style={{ maxHeight: '300px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                {result.trace.map((t, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3"
                    style={{
                      padding: '0.5rem 0.75rem',
                      background: 'rgba(12,18,32,0.5)',
                      borderRadius: '6px',
                      border: '1px solid rgba(56,90,155,0.15)',
                    }}
                  >
                    <span
                      style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: t.status === 'completed' ? '#10b981' : '#ef4444',
                        flexShrink: 0,
                      }}
                    />
                    <span className="tag" style={{ fontSize: '0.7rem' }}>{t.agent_code}</span>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8', flex: 1 }}>{t.agent_name}</span>
                    <span style={{ fontSize: '0.75rem', color: '#475569' }}>{t.duration_ms}ms</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
