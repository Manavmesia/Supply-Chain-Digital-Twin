import React, { useEffect, useState, useCallback, useRef } from 'react';
import { RotateCcw, Bot, X } from 'lucide-react';
import { Link } from 'react-router-dom';
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
  const isMountedRef = useRef(true);

  const fetchAgents = useCallback(async (isSilent = false) => {
    try {
      const res = await analyticsApi.getAgents();
      if (isMountedRef.current) {
        setAgents(res.agents);
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
    let ignore = false;
    isMountedRef.current = true;

    analyticsApi.getAgents().then((res) => {
      if (!ignore && isMountedRef.current) {
        setAgents(res.agents);
        setLoading(false);
      }
    }).catch((err) => {
      console.error('Agents load error:', err);
      if (!ignore && isMountedRef.current) setLoading(false);
    });

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
      ignore = true;
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
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Agent Directory
          </h1>
          <p className="page-subtitle">
            Operational, business intelligence, and coordination agents supervising enterprise workflows.
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={() => { setLoading(true); fetchAgents(false); }}
            disabled={loading}
            className="btn-secondary"
          >
            <RotateCcw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
        {layers.map((layer) => {
          const count = agents.filter((a) => a.layer === layer).length;
          const style = LAYER_STYLE[layer];
          return (
            <div
              key={layer}
              className="stat-card"
              style={{ borderTop: `3px solid ${style.color}` }}
            >
              <div className="stat-value" style={{ color: style.color, fontSize: '2rem' }}>
                {loading ? '—' : count}
              </div>
              <div className="stat-label" style={{ textTransform: 'capitalize', marginTop: '4px' }}>
                {layer} Agents
              </div>
              <p style={{ fontSize: '12px', color: '#64748b', marginTop: '8px', lineHeight: 1.5 }}>
                {LAYER_DESCRIPTIONS[layer]}
              </p>
            </div>
          );
        })}
      </div>

      {/* Pipeline visual */}
      <AgentPipeline agents={agents} loading={loading} />

      {/* Agent cards grid */}
      <div style={{ marginTop: '28px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Bot size={16} className="text-slate-400" />
          <span>Active Enterprise Agent Roster</span>
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
          {loading
            ? Array.from({ length: 18 }).map((_, i) => (
                <div key={i} className="skeleton" style={{ height: '120px', borderRadius: 'var(--radius-lg)' }} />
              ))
            : agents.map((agent) => {
                const style = LAYER_STYLE[agent.layer];
                const isSelected = selectedAgent?.code === agent.code;
                return (
                  <div
                    key={agent.code}
                    className="card animate-fade-in"
                    style={{
                      cursor: 'pointer',
                      borderLeft: `4px solid ${style.color}`,
                      transition: 'all 0.2s ease',
                      padding: '20px',
                      marginBottom: 0,
                    }}
                    onClick={() => setSelectedAgent(isSelected ? null : agent)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '9999px',
                          color: style.color,
                          border: `1px solid ${style.color}44`,
                          background: '#ffffff',
                        }}
                      >
                        {agent.code}
                      </span>
                      <span
                        style={{
                          background: style.bg,
                          color: style.color,
                          border: `1px solid ${style.color}44`,
                          fontSize: '11px',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '9999px',
                          textTransform: 'capitalize',
                        }}
                      >
                        {agent.layer}
                      </span>
                    </div>
                    <h4 style={{ margin: '0 0 6px 0', fontSize: '14px', fontWeight: 700, color: '#0f172a' }}>{agent.name}</h4>
                    <p style={{ fontSize: '12px', color: '#64748b', lineHeight: 1.5, margin: 0 }}>
                      {agent.description}
                    </p>
                  </div>
                );
              })}
        </div>
      </div>

      {/* Agent Detail Drawer */}
      {selectedAgent && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(2px)', display: 'flex', justifyContent: 'flex-end', zIndex: 110 }}>
          <div style={{ width: '480px', maxWidth: '100%', background: '#ffffff', height: '100%', padding: '28px', borderLeft: '1px solid #e2e8f0', boxShadow: '-4px 0 24px rgba(0,0,0,0.08)', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '9999px', color: LAYER_STYLE[selectedAgent.layer]?.color, border: '1px solid #e2e8f0', background: '#f8fafc' }}>
                  {selectedAgent.code}
                </span>
                <h2 style={{ fontSize: '20px', fontWeight: 700, margin: '8px 0 0', color: '#0f172a' }}>
                  {selectedAgent.name}
                </h2>
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '4px' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ background: '#f8fafc', borderRadius: 'var(--radius-md)', padding: '16px', marginBottom: '20px', border: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '6px' }}>
                Operational Layer
              </div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', textTransform: 'capitalize' }}>
                {selectedAgent.layer} Layer
              </div>
              <p style={{ fontSize: '13px', color: '#475569', margin: '8px 0 0', lineHeight: 1.5 }}>
                {LAYER_DESCRIPTIONS[selectedAgent.layer]}
              </p>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '6px' }}>
                Core Responsibilities
              </div>
              <p style={{ fontSize: '14px', color: '#334155', lineHeight: 1.6, margin: 0 }}>
                {selectedAgent.description}
              </p>
            </div>

            <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '20px', display: 'flex', gap: '10px' }}>
              <Link
                to="/workflows"
                className="btn-primary"
                style={{ flex: 1, justifyContent: 'center', textDecoration: 'none', padding: '10px 16px', fontSize: '13px' }}
              >
                Trigger Workflow in Agent Engine →
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
