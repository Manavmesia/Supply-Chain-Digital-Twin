import React from 'react';
import type { AgentDefinition } from '../../types';

const LAYER_STYLE: Record<string, { color: string; bg: string; label: string }> = {
  operational:  { color: '#10b981', bg: 'rgba(16,185,129,0.1)',  label: 'Operational' },
  business:     { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)',  label: 'Business Intelligence' },
  coordination: { color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)', label: 'Coordination' },
};

interface AgentPipelineProps {
  agents: AgentDefinition[];
  activeAgents?: string[];    // agent codes that ran in the last workflow
  loading?: boolean;
}

export const AgentPipeline: React.FC<AgentPipelineProps> = ({
  agents, activeAgents = [], loading,
}) => {
  if (loading) {
    return (
      <div className="card">
        <div className="section-header">
          <h3 className="section-title">🤖 18-Agent Pipeline</h3>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', padding: '0.5rem' }}>
          {Array.from({ length: 18 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ width: '110px', height: '56px', borderRadius: '8px' }} />
          ))}
        </div>
      </div>
    );
  }

  const layers = ['operational', 'business', 'coordination'] as const;
  const byLayer = (l: string) => agents.filter((a) => a.layer === l);

  return (
    <div className="card animate-fade-in">
      <div className="section-header">
        <h3 className="section-title">
          <span className="icon-accent">🤖</span> 18-Agent Pipeline
        </h3>
        <div className="flex gap-2">
          {Object.entries(LAYER_STYLE).map(([k, s]) => (
            <span key={k} className="badge" style={{
              background: s.bg,
              color: s.color,
              border: `1px solid ${s.color}44`,
              fontSize: '0.7rem',
            }}>
              {s.label}
            </span>
          ))}
        </div>
      </div>

      <div className="agent-pipeline">
        {layers.map((layer) => {
          const style = LAYER_STYLE[layer];
          return (
            <div key={layer} className="agent-layer">
              <div className="agent-layer-header" style={{ color: style.color }}>
                <span
                  className="agent-layer-dot"
                  style={{ background: style.color }}
                />
                {style.label}
                <span className="agent-layer-count">
                  ({byLayer(layer).length})
                </span>
              </div>
              <div className="agent-layer-grid">
                {byLayer(layer).map((agent, i) => {
                  const isActive = activeAgents.includes(agent.code);
                  return (
                    <div
                      key={agent.code}
                      className={`agent-chip ${isActive ? 'active' : ''}`}
                      style={{
                        borderColor: isActive ? style.color : 'rgba(56,90,155,0.22)',
                        background: isActive ? style.bg : 'rgba(12,18,32,0.6)',
                        animationDelay: `${i * 40}ms`,
                      }}
                      title={agent.description}
                    >
                      <span
                        className="agent-chip-code"
                        style={{ color: isActive ? style.color : '#64748b' }}
                      >
                        {agent.code}
                      </span>
                      <span className="agent-chip-name">{agent.name}</span>
                      {isActive && (
                        <span
                          className="agent-chip-active-dot"
                          style={{ background: style.color }}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
