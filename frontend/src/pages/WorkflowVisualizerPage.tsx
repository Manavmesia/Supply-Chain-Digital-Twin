import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Layers,
  Zap,
  Cpu,
  Activity,
} from 'lucide-react';
import { LiveWorkflowGraph } from '../components/workflow/LiveWorkflowGraph';
import { LiveEventGraph } from '../components/workflow/LiveEventGraph';
import { apiClient } from '../services/api';

export const WorkflowVisualizerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialMode = (searchParams.get('mode') as 'workflow' | 'events' | 'simulation') || 'workflow';
  const initialWorkflowId = searchParams.get('workflow_id') || searchParams.get('id') || '';
  const initialEventId = searchParams.get('event_id') || '';

  const [activeMode, setActiveMode] = useState<'workflow' | 'events' | 'simulation'>(initialMode);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState(initialWorkflowId);
  const [selectedEventId, setSelectedEventId] = useState(initialEventId);

  // Simulation states
  const [simScenario, setSimScenario] = useState('demand_spike');
  const [simRunning, setSimRunning] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);

  useEffect(() => {
    const params = new URLSearchParams(searchParams);
    params.set('mode', activeMode);
    if (selectedWorkflowId && activeMode === 'workflow') {
      params.set('workflow_id', selectedWorkflowId);
    } else {
      params.delete('workflow_id');
    }
    if (selectedEventId && activeMode === 'events') {
      params.set('event_id', selectedEventId);
    } else {
      params.delete('event_id');
    }
    setSearchParams(params, { replace: true });
  }, [activeMode, selectedWorkflowId, selectedEventId, setSearchParams]);

  const handleRunSimulation = async () => {
    setSimRunning(true);
    setSimResult(null);
    try {
      const { data } = await apiClient.post('/simulate', {
        scenario_type: simScenario,
        customer_id: '50000000-0000-0000-0000-000000000001',
        items: [{ product_id: '22222222-0000-0000-0000-000000000001', quantity: 45 }],
      });

      // Poll simulation result
      const simId = data.simulation_id;
      const poll = setInterval(async () => {
        try {
          const res = await apiClient.get(`/simulate/${simId}`);
          if (res.data.status === 'completed' || res.data.status === 'failed') {
            clearInterval(poll);
            setSimResult(res.data);
            setSimRunning(false);
          }
        } catch {
          clearInterval(poll);
          setSimRunning(false);
        }
      }, 700);
    } catch (e: any) {
      alert(`Simulation failed: ${e.message}`);
      setSimRunning(false);
    }
  };

  return (
    <div className="page-container animate-fade-in" style={{ maxWidth: '1440px', margin: '0 auto', padding: '24px 28px' }}>
      {/* Header */}
      <div className="page-header" style={{ marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
              }}
            >
              <Activity size={18} />
            </div>
            <h1 className="page-title" style={{ margin: 0, fontSize: '22px' }}>
              Multi-Agent Workflow & Event Visualizer
            </h1>
          </div>
          <p className="page-subtitle" style={{ margin: '4px 0 0' }}>
            Real-time visual pacing, interactive topology inspection, and autonomous multi-agent remediation telemetry.
          </p>
        </div>

        {/* View Mode Switcher */}
        <div
          style={{
            display: 'flex',
            background: 'var(--c-bg-subtle)',
            borderRadius: '8px',
            padding: '3px',
            border: '1px solid var(--c-border)',
          }}
        >
          <button
            onClick={() => setActiveMode('workflow')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: activeMode === 'workflow' ? 600 : 500,
              background: activeMode === 'workflow' ? 'var(--c-bg-card)' : 'transparent',
              color: activeMode === 'workflow' ? 'var(--c-brand-accent)' : 'var(--c-text-secondary)',
              border: activeMode === 'workflow' ? '1px solid var(--c-border)' : 'none',
              cursor: 'pointer',
              boxShadow: activeMode === 'workflow' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <Layers size={14} />
            <span>Order Fulfillment (18 Agents)</span>
          </button>

          <button
            onClick={() => setActiveMode('events')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: activeMode === 'events' ? 600 : 500,
              background: activeMode === 'events' ? 'var(--c-bg-card)' : 'transparent',
              color: activeMode === 'events' ? 'var(--c-brand-accent)' : 'var(--c-text-secondary)',
              border: activeMode === 'events' ? '1px solid var(--c-border)' : 'none',
              cursor: 'pointer',
              boxShadow: activeMode === 'events' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <Zap size={14} />
            <span>Event Bus Remediation</span>
          </button>

          <button
            onClick={() => setActiveMode('simulation')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: activeMode === 'simulation' ? 600 : 500,
              background: activeMode === 'simulation' ? 'var(--c-bg-card)' : 'transparent',
              color: activeMode === 'simulation' ? 'var(--c-brand-accent)' : 'var(--c-text-secondary)',
              border: activeMode === 'simulation' ? '1px solid var(--c-border)' : 'none',
              cursor: 'pointer',
              boxShadow: activeMode === 'simulation' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <Cpu size={14} />
            <span>Scenario Stress-Test</span>
          </button>
        </div>
      </div>

      {/* Main View Panels */}
      {activeMode === 'workflow' && (
        <LiveWorkflowGraph
          initialWorkflowId={selectedWorkflowId}
          onWorkflowSelect={(id) => setSelectedWorkflowId(id)}
        />
      )}

      {activeMode === 'events' && (
        <LiveEventGraph
          initialEventId={selectedEventId}
          onEventSelect={(id) => setSelectedEventId(id)}
        />
      )}

      {activeMode === 'simulation' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div
            style={{
              background: 'var(--c-bg-card)',
              border: '1px solid var(--c-border)',
              borderRadius: '12px',
              padding: '20px',
              boxShadow: 'var(--shadow-card)',
            }}
          >
            <h3 style={{ fontSize: '15px', fontWeight: 700, margin: '0 0 14px', color: 'var(--c-text-primary)' }}>
              What-If Multi-Agent Simulation Engine
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--c-text-secondary)', margin: '0 0 18px' }}>
              Simulate disruptive stress-test scenarios across all 18 supply chain agents with live execution tracing and resilience scoring.
            </p>

            <div style={{ display: 'flex', gap: '14px', alignItems: 'center', flexWrap: 'wrap' }}>
              <select
                value={simScenario}
                onChange={(e) => setSimScenario(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--c-border)',
                  background: 'var(--c-bg-subtle)',
                  fontSize: '13px',
                  color: 'var(--c-text-primary)',
                }}
              >
                <option value="demand_spike">Demand Surge (2.5x Market Spike)</option>
                <option value="supplier_outage">Supplier Capacity Outage (Vendor Failover)</option>
                <option value="logistics_delay">Logistics Bottleneck (+14 Days Transit)</option>
                <option value="bulk_order">Bulk Enterprise Order (CapEx Approval)</option>
                <option value="quality_crisis">Quality Crisis (100% Lot Quarantine)</option>
              </select>

              <button
                onClick={handleRunSimulation}
                disabled={simRunning}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 18px',
                  borderRadius: '8px',
                  fontSize: '13px',
                  fontWeight: 600,
                  background: simRunning ? 'var(--c-bg-subtle)' : 'var(--c-brand-accent)',
                  color: '#ffffff',
                  border: 'none',
                  cursor: simRunning ? 'not-allowed' : 'pointer',
                }}
              >
                {simRunning ? 'Running Simulation...' : 'Launch Simulation'}
              </button>
            </div>
          </div>

          {/* Simulation Output */}
          {simResult && (
            <div
              style={{
                background: 'var(--c-bg-card)',
                border: '1px solid var(--c-border)',
                borderRadius: '12px',
                padding: '20px',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>
                  Simulation Outcome: <span style={{ textTransform: 'capitalize' }}>{simResult.scenario_type}</span>
                </h4>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: '10px',
                    background: simResult.status === 'completed' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                    color: simResult.status === 'completed' ? '#059669' : '#ef4444',
                  }}
                >
                  {simResult.status}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                <div style={{ background: 'var(--c-bg-subtle)', padding: '12px', borderRadius: '8px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--c-text-muted)' }}>Agents Executed</span>
                  <div style={{ fontSize: '18px', fontWeight: 700, marginTop: '2px' }}>{simResult.agents_executed || simResult.trace?.length || 0}</div>
                </div>
                <div style={{ background: 'var(--c-bg-subtle)', padding: '12px', borderRadius: '8px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--c-text-muted)' }}>Risk Assessment</span>
                  <div style={{ fontSize: '18px', fontWeight: 700, marginTop: '2px' }}>
                    {simResult.summary?.risk_score !== undefined ? `${simResult.summary.risk_score} / 100` : 'Evaluated'}
                  </div>
                </div>
                <div style={{ background: 'var(--c-bg-subtle)', padding: '12px', borderRadius: '8px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--c-text-muted)' }}>CEO Approval Tier</span>
                  <div style={{ fontSize: '18px', fontWeight: 700, marginTop: '2px' }}>
                    {simResult.summary?.ceo_approved ? 'Approved' : 'Standard'}
                  </div>
                </div>
              </div>

              {simResult.trace && simResult.trace.length > 0 && (
                <div>
                  <h5 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--c-text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                    Agent Execution Trail ({simResult.trace.length})
                  </h5>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {simResult.trace.map((t: any, i: number) => (
                      <div
                        key={i}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '8px 12px',
                          background: 'var(--c-bg-subtle)',
                          borderRadius: '6px',
                          fontSize: '12px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--c-brand-accent)' }}>
                            {t.agent_code}
                          </span>
                          <span>{t.agent_name}</span>
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', color: '#059669', fontWeight: 600 }}>
                          {t.duration_ms}ms
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
