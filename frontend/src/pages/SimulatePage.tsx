import React, { useState, useEffect, useRef } from 'react';
import { simulateApi } from '../services/api';
import type { SimulationResult } from '../types';
import { formatSimulationId } from '../utils/formatters';

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

  const loadSimulation = async (id: string) => {
    try {
      setSimulationId(id);
      localStorage.setItem('active_sim_id', id);
      const url = new URL(window.location.href);
      url.searchParams.set('id', id);
      window.history.replaceState(null, '', url.toString());

      const r = await simulateApi.getResult(id);
      setResult(r);
      setSelectedScenario(r.scenario_type);
      setStatus(r.status === 'completed' ? 'done' : r.status === 'failed' ? 'failed' : 'running');

      if (r.status !== 'completed' && r.status !== 'failed') {
        stopPoll();
        let pollCount = 0;
        pollRef.current = setInterval(async () => {
          pollCount += 1;
          try {
            const updated = await simulateApi.getResult(id);
            if (updated.status === 'completed' || updated.status === 'failed') {
              stopPoll();
              setResult(updated);
              setStatus(updated.status === 'completed' ? 'done' : 'failed');
            } else if (pollCount > 60) {
              stopPoll();
            }
          } catch {
            if (pollCount > 30) stopPoll();
          }
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to load simulation:', err);
    }
  };

  useEffect(() => {
    simulateApi.list(15).then((res) => {
      const items = res.items || [];
      setRecentSims(items);
      const params = new URLSearchParams(window.location.search);
      const urlId = params.get('id');
      const savedId = localStorage.getItem('active_sim_id');
      const targetId = urlId || savedId || (items.length > 0 ? items[0].simulation_id : null);
      if (targetId) {
        loadSimulation(targetId);
      }
    }).catch(err => console.error('Recent simulations fetch error:', err));

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
      localStorage.setItem('active_sim_id', accepted.simulation_id);
      const url = new URL(window.location.href);
      url.searchParams.set('id', accepted.simulation_id);
      window.history.replaceState(null, '', url.toString());

      // Refresh list
      simulateApi.list(15).then((res) => setRecentSims(res.items || []));

      let pollCount = 0;
      pollRef.current = setInterval(async () => {
        pollCount += 1;
        try {
          const r = await simulateApi.getResult(accepted.simulation_id);
          if (r.status === 'completed' || r.status === 'failed') {
            stopPoll();
            setResult(r);
            setStatus(r.status === 'completed' ? 'done' : 'failed');
            simulateApi.list(15).then((res) => setRecentSims(res.items || []));
          } else if (pollCount > 60) {
            // Stop after 2 minutes of polling
            stopPoll();
            setStatus('failed');
          }
        } catch (err) {
          console.error('Polling simulation failed:', err);
          if (pollCount > 30) {
            stopPoll();
            setStatus('failed');
          }
        }
      }, 2000);
    } catch {
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
                    border: `1px solid ${selectedScenario === s.type ? s.color : 'var(--c-border)'}`,
                    background: selectedScenario === s.type ? `${s.color}14` : 'var(--c-bg-card)',
                    cursor: 'pointer',
                    padding: '1rem',
                    borderRadius: '10px',
                    transition: 'all 0.2s ease',
                  }}
                  onClick={() => setSelectedScenario(s.type)}
                >
                  <div className="flex items-center gap-3">
                    <span style={{ fontSize: '1.5rem' }}>{s.icon}</span>
                    <div>
                      <p style={{ fontWeight: 600, color: selectedScenario === s.type ? s.color : 'var(--c-text-primary)' }}>
                        {s.title}
                      </p>
                      <p style={{ fontSize: '0.8rem', color: 'var(--c-text-muted)' }}>{s.desc}</p>
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
              recentSims.map((s) => {
                const isSelected = simulationId === s.simulation_id;
                return (
                  <div
                    key={s.simulation_id}
                    className="flex justify-between items-center"
                    style={{
                      padding: '0.6rem 0.75rem',
                      marginBottom: '0.25rem',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      border: `1px solid ${isSelected ? 'var(--c-brand-1)' : 'var(--c-border)'}`,
                      background: isSelected ? 'rgba(79, 70, 229, 0.08)' : 'var(--c-bg-subtle)',
                      transition: 'all 0.15s ease',
                    }}
                    onClick={() => loadSimulation(s.simulation_id)}
                    title={`Click to view results of ${s.simulation_id}`}
                  >
                    <div>
                      <span style={{ fontSize: '0.875rem', fontWeight: isSelected ? 600 : 500, color: 'var(--c-text-primary)' }}>
                        {s.scenario_type.replace('_', ' ')}
                      </span>
                      <p style={{ fontSize: '0.72rem', color: 'var(--c-text-muted)' }}>
                        {formatSimulationId(s.simulation_id)} • {s.agents_executed} agents
                      </p>
                    </div>
                    <span
                      className="badge"
                      style={{
                        background: s.status === 'completed' ? 'rgba(5,150,105,0.12)' : 'rgba(220,38,38,0.12)',
                        color: s.status === 'completed' ? 'var(--c-success)' : 'var(--c-danger)',
                        border: `1px solid ${s.status === 'completed' ? 'rgba(5,150,105,0.25)' : 'rgba(220,38,38,0.25)'}`,
                        fontSize: '0.7rem',
                      }}
                    >
                      {s.status}
                    </span>
                  </div>
                );
              })
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
              <p style={{ fontSize: '0.8rem', color: 'var(--c-text-muted)' }}>
                Results will appear here in real time
              </p>
            </div>
          )}

          {status === 'running' && (
            <div className="loading-overlay">
              <span className="loading-spinner" style={{ width: 40, height: 40 }} />
              <p>Running 18-agent consensus pipeline…</p>
              <p style={{ fontSize: '0.8rem', color: 'var(--c-text-muted)' }}>
                Target: {formatSimulationId(simulationId)}
              </p>
            </div>
          )}

          {result && result.summary && (
            <div className="animate-fade-in">
              <div className="mb-4">
                <div className="flex gap-2 flex-wrap mb-3 items-center">
                  <span className="badge badge-info" style={{ fontFamily: 'var(--font-mono)' }}>
                    {formatSimulationId(result.simulation_id)}
                  </span>
                  <span className="badge badge-success">{result.agents_executed} agents executed</span>
                  <span className="tag" style={{ textTransform: 'uppercase' }}>{result.scenario_type.replace('_', ' ')}</span>
                </div>
              </div>

              <div className="grid-2" style={{ gap: '0.75rem', marginBottom: '1.25rem' }}>
                {[
                  { label: 'Workflow Status', value: result.summary.workflow_status, color: 'var(--c-success)' },
                  { label: 'Order Status',    value: result.summary.order_status ?? '—',    color: 'var(--c-brand-1)' },
                  { label: 'Risk Level',      value: result.summary.risk_level ?? '—',      color: 'var(--c-warning)' },
                  { label: 'Risk Score',      value: result.summary.risk_score != null ? String(result.summary.risk_score) : '—', color: 'var(--c-danger)' },
                  { label: 'CEO Approved',    value: result.summary.ceo_approved != null ? (result.summary.ceo_approved ? 'Yes ✅' : 'No ❌') : '—', color: result.summary.ceo_approved ? 'var(--c-success)' : 'var(--c-danger)' },
                  { label: 'Carrier',         value: result.summary.carrier ?? '—',         color: 'var(--c-coordination)' },
                  { label: 'Decisions Made',  value: String(result.summary.decision_count ?? 0),  color: 'var(--c-brand-3)' },
                  { label: 'Events Fired',    value: String(result.summary.event_count ?? 0),    color: 'var(--c-brand-3)' },
                ].map(({ label, value, color }) => (
                  <div
                    key={label}
                    style={{
                      background: 'var(--c-bg-subtle)',
                      border: '1px solid var(--c-border)',
                      borderRadius: '8px',
                      padding: '0.75rem',
                    }}
                  >
                    <p style={{ fontSize: '0.7rem', color: 'var(--c-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
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
                      background: 'var(--c-bg-subtle)',
                      borderRadius: '6px',
                      border: '1px solid var(--c-border)',
                    }}
                  >
                    <span
                      style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: t.status === 'completed' ? 'var(--c-success)' : 'var(--c-danger)',
                        flexShrink: 0,
                      }}
                    />
                    <span className="tag" style={{ fontSize: '0.7rem' }}>{t.agent_code}</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--c-text-primary)', flex: 1 }}>{t.agent_name}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--c-text-muted)' }}>{t.duration_ms}ms</span>
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
