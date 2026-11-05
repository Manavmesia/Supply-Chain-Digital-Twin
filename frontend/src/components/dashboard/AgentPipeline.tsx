import React from 'react';
import type { AgentDefinition } from '../../types';
import { Cpu } from 'lucide-react';

const LAYER_CONFIG: Record<string, { label: string; tagColor: string }> = {
  operational:  { label: 'Operational Layer', tagColor: '#60a5fa' },
  business:     { label: 'Business Intelligence', tagColor: '#a78bfa' },
  coordination: { label: 'Coordination & Consensus', tagColor: '#34d399' },
};

interface AgentPipelineProps {
  agents: AgentDefinition[];
  activeAgents?: string[];
  loading?: boolean;
}

export const AgentPipeline: React.FC<AgentPipelineProps> = ({
  agents,
  activeAgents = [],
  loading,
}) => {
  if (loading) {
    return (
      <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: '8px', padding: '18px' }}>
        <div style={{ height: '24px', width: '200px', background: 'rgba(255,255,255,0.04)', borderRadius: '4px', marginBottom: '16px' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '8px' }}>
          {Array.from({ length: 18 }).map((_, i) => (
            <div key={i} style={{ height: '48px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }} />
          ))}
        </div>
      </div>
    );
  }

  const layers = ['operational', 'business', 'coordination'] as const;
  const byLayer = (l: string) => agents.filter((a) => a.layer === l);

  return (
    <div
      style={{
        background: '#0f172a',
        border: '1px solid rgba(255, 255, 255, 0.07)',
        borderRadius: '8px',
        padding: '20px',
        marginBottom: '24px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#94a3b8',
            }}
          >
            <Cpu size={15} />
          </div>
          <div>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Autonomous 18-Agent Consensus Engine
            </h3>
            <span style={{ fontSize: '11px', color: '#64748b' }}>
              LangGraph state-machine orchestrating decentralized supply chain nodes
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {Object.entries(LAYER_CONFIG).map(([k, cfg]) => (
            <span
              key={k}
              style={{
                fontSize: '11px',
                fontWeight: 500,
                color: cfg.tagColor,
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                padding: '3px 8px',
                borderRadius: '4px',
              }}
            >
              {cfg.label}
            </span>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {layers.map((layer) => {
          const cfg = LAYER_CONFIG[layer];
          const layerAgents = byLayer(layer);

          return (
            <div key={layer}>
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: '#64748b',
                  marginBottom: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>{cfg.label}</span>
                <span style={{ color: '#475569' }}>&bull;</span>
                <span style={{ color: '#94a3b8' }}>{layerAgents.length} agents</span>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                  gap: '8px',
                }}
              >
                {layerAgents.map((agent) => {
                  const isActive = activeAgents.includes(agent.code);

                  return (
                    <div
                      key={agent.code}
                      title={agent.description}
                      style={{
                        background: isActive ? 'rgba(59, 130, 246, 0.08)' : '#131e33',
                        border: isActive ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid rgba(255, 255, 255, 0.05)',
                        borderRadius: '6px',
                        padding: '8px 10px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '6px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
                        <span
                          style={{
                            fontFamily: 'monospace',
                            fontSize: '10px',
                            fontWeight: 700,
                            color: isActive ? '#60a5fa' : '#94a3b8',
                            background: 'rgba(255, 255, 255, 0.04)',
                            padding: '1px 4px',
                            borderRadius: '3px',
                            flexShrink: 0,
                          }}
                        >
                          {agent.code}
                        </span>
                        <span
                          style={{
                            fontSize: '12px',
                            fontWeight: 500,
                            color: '#f8fafc',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {agent.name}
                        </span>
                      </div>

                      <div
                        style={{
                          width: '6px',
                          height: '6px',
                          borderRadius: '50%',
                          background: isActive ? '#34d399' : '#334155',
                          flexShrink: 0,
                        }}
                      />
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
