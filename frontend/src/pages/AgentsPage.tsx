import React, { useEffect, useState, useCallback, useRef } from 'react';
import { analyticsApi } from '../services/api';
import { AgentPipeline } from '../components/dashboard/AgentPipeline';
import type { AgentDefinition } from '../types';

const LAYER_DESCRIPTIONS = {
  operational: 'Execute day-to-day supply chain operations — order intake, inventory checks, shipping, and manufacturing.',
  business: 'Provide analytical intelligence — cost analysis, risk scoring, dynamic pricing, sustainability metrics.',
  coordination: 'Govern multi-agent coordination — execution planning, negotiation, executive decisions, and reporting.',
};

export const AgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<AgentDefinition | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const isMountedRef = useRef(true);

  const fetchAgents = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    try {
      const res = await analyticsApi.getAgents();
      if (isMountedRef.current) {
        setAgents(res.agents);
        setLastUpdated(new Date());
      }
    } catch (err) {
      console.error('Agents load error:', err);
    } finally {
      if (isMountedRef.current && !isSilent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    fetchAgents(false);

    // Auto-sync agents every 5 seconds
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchAgents(true);
      }
    }, 5000);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        fetchAgents(true);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [fetchAgents]);

  const LAYER_STYLE: Record<string, { color: string; bg: string }> = {
    operational:  { color: '#10b981', bg: 'rgba(16,185,129,0.1)' },
    business:     { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
    coordination: { color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)' },
  };

  const layers = ['operational', 'business', 'coordination'] as const;

  return (
    <div className="page-content animate-fade-in">
      <div className="page-header">
        <h1><span className="gradient-text">Agent Control Centre</span></h1>
        <p>All 18 autonomous AI agents — their roles, layers, and responsibilities</p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => fetchAgents(false)}
            disabled={loading}
          >
            ↻ Refresh Agents
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: '#10b981' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 6px #10b981' }} />
            Live Auto-Sync (5s) • Updated {lastUpdated.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid-3 mb-6">
        {layers.map((layer) => {
          const count = agents.filter((a) => a.layer === layer).length;
          const style = LAYER_STYLE[layer];
          return (
            <div
              key={layer}
              className="card"
              style={{ borderTop: `2px solid ${style.color}` }}
            >
              <div className="kpi-value" style={{ color: style.color, fontSize: '2rem' }}>
                {loading ? '—' : count}
              </div>
              <div className="kpi-label" style={{ textTransform: 'capitalize' }}>
                {layer} Agents
              </div>
              <p style={{ fontSize: '0.8rem', color: '#475569', marginTop: '0.5rem' }}>
                {LAYER_DESCRIPTIONS[layer]}
              </p>
            </div>
          );
        })}
      </div>

      {/* Pipeline visual */}
      <AgentPipeline agents={agents} loading={loading} />

      {/* Agent cards grid */}
      <div className="mt-6">
        <h3 className="section-title mb-4">📋 Agent Directory</h3>
        <div className="grid-3">
          {loading
            ? Array.from({ length: 18 }).map((_, i) => (
                <div key={i} className="skeleton" style={{ height: '120px', borderRadius: '12px' }} />
              ))
            : agents.map((agent) => {
                const style = LAYER_STYLE[agent.layer];
                const isSelected = selectedAgent?.code === agent.code;
                return (
                  <div
                    key={agent.code}
                    className={`card animate-fade-in ${isSelected ? 'glow-blue' : ''}`}
                    style={{
                      cursor: 'pointer',
                      borderLeft: `3px solid ${style.color}`,
                      transition: 'all 0.2s ease',
                    }}
                    onClick={() => setSelectedAgent(isSelected ? null : agent)}
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span
                        className="tag"
                        style={{ color: style.color, border: `1px solid ${style.color}44` }}
                      >
                        {agent.code}
                      </span>
                      <span
                        className="badge"
                        style={{
                          background: style.bg,
                          color: style.color,
                          border: `1px solid ${style.color}44`,
                          fontSize: '0.65rem',
                          textTransform: 'capitalize',
                        }}
                      >
                        {agent.layer}
                      </span>
                    </div>
                    <h4 style={{ marginBottom: '0.375rem' }}>{agent.name}</h4>
                    <p style={{ fontSize: '0.8rem', color: '#64748b', lineHeight: 1.5 }}>
                      {agent.description}
                    </p>
                  </div>
                );
              })}
        </div>
      </div>
    </div>
  );
};
