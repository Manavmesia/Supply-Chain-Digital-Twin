import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Cpu,
  RefreshCw,
  Check,
  X,
  FileCheck,
} from 'lucide-react';
import { workflowApi } from '../../services/api';
import type { WorkflowStatus, AgentTrace } from '../../types';
import { formatDateTime } from '../../utils/formatters';
import { BusinessDataView } from '../common/BusinessDataView';

interface OrderDecisionTrailProps {
  workflowId: string;
  orderId?: string;
  onRefresh?: () => void;
}

const AGENT_LAYER: Record<string, { color: string; label: string }> = {
  'ADS-01': { color: '#2563eb', label: 'Operational' },
  'ADS-02': { color: '#7c3aed', label: 'Business' },
  'ADS-03': { color: '#2563eb', label: 'Operational' },
  'ADS-04': { color: '#2563eb', label: 'Operational' },
  'ADS-05': { color: '#2563eb', label: 'Operational' },
  'ADS-06': { color: '#2563eb', label: 'Operational' },
  'ADS-07': { color: '#2563eb', label: 'Operational' },
  'ADS-08': { color: '#2563eb', label: 'Operational' },
  'ADS-09': { color: '#7c3aed', label: 'Business' },
  'ADS-10': { color: '#dc2626', label: 'Business Risk' },
  'ADS-11': { color: '#7c3aed', label: 'Business' },
  'ADS-12': { color: '#7c3aed', label: 'Business' },
  'ADS-13': { color: '#059669', label: 'Business ESG' },
  'ADS-14': { color: '#0891b2', label: 'Quality' },
  'ADS-15': { color: '#d97706', label: 'Coordination' },
  'ADS-16': { color: '#d97706', label: 'Coordination' },
  'ADS-17': { color: '#d97706', label: 'Governance' },
  'ADS-18': { color: '#475569', label: 'Reporting' },
};

export const OrderDecisionTrail: React.FC<OrderDecisionTrailProps> = ({
  workflowId,
  orderId: _orderId,
  onRefresh,
}) => {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [traces, setTraces] = useState<AgentTrace[]>([]);
  const [openTraceIdx, setOpenTraceIdx] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'decision' | 'output' | 'input' | 'events'>('decision');
  const [actionLoading, setActionLoading] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const loadData = useCallback(async (isSilent = false) => {
    if (!workflowId) return;
    if (!isSilent) setLoading(true);
    try {
      const [statusRes, traceRes] = await Promise.all([
        workflowApi.getStatus(workflowId),
        workflowApi.getTrace(workflowId),
      ]);
      setStatus(statusRes);
      setTraces(traceRes?.traces || []);
    } catch {
      // Keep existing data on error
    } finally {
      if (!isSilent) setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    loadData(false);
    if (status?.workflow_status === 'completed' || status?.workflow_status === 'failed') return;
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadData(true);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [loadData, status?.workflow_status]);

  const handleApprove = async () => {
    if (!workflowId) return;
    setActionLoading(true);
    try {
      await workflowApi.approve(workflowId, approvalNotes || 'Approved by commercial operations');
      setActionFeedback('Transaction approved successfully.');
      await loadData();
      if (onRefresh) onRefresh();
    } catch {
      setActionFeedback('Failed to submit approval.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!workflowId) return;
    setActionLoading(true);
    try {
      await workflowApi.reject(workflowId, approvalNotes || 'Rejected by commercial operations');
      setActionFeedback('Transaction flagged and rejected.');
      await loadData();
      if (onRefresh) onRefresh();
    } catch {
      setActionFeedback('Failed to submit rejection.');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !status) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center', color: '#64748b' }}>
        <RefreshCw className="w-5 h-5 animate-spin" style={{ margin: '0 auto 8px', display: 'block' }} />
        <span style={{ fontSize: '13px' }}>Loading autonomous decision trail...</span>
      </div>
    );
  }

  const isCompleted = status?.workflow_status === 'completed';
  const isFailed = status?.workflow_status === 'failed';
  const requiresApproval = Boolean(status?.requires_human_approval);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header status bar */}
      <div
        style={{
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          padding: '14px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>
            Decision Pipeline State
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
            {isCompleted ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#059669', fontWeight: 600, fontSize: '13px' }}>
                <CheckCircle2 className="w-4 h-4" /> Autonomous Processing Complete
              </span>
            ) : isFailed ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#dc2626', fontWeight: 600, fontSize: '13px' }}>
                <AlertTriangle className="w-4 h-4" /> Processing Exception
              </span>
            ) : (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#2563eb', fontWeight: 600, fontSize: '13px' }}>
                <Clock className="w-4 h-4" /> Active Execution
              </span>
            )}
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>
            Audit Reference
          </div>
          <div style={{ fontSize: '12px', fontFamily: 'monospace', color: '#0f172a', fontWeight: 600, marginTop: '4px' }}>
            {workflowId.slice(0, 13)}...
          </div>
        </div>
      </div>

      {/* Human-in-the-loop intervention banner if required */}
      {requiresApproval && (
        <div
          style={{
            background: '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: '8px',
            padding: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#b45309', fontWeight: 600, fontSize: '14px', marginBottom: '6px' }}>
            <ShieldAlert className="w-4 h-4" />
            Governance Escalation — Operator Approval Required
          </div>
          <p style={{ fontSize: '12px', color: '#78350f', margin: '0 0 12px 0' }}>
            Automated threshold evaluation triggered governance review. Please evaluate executive decisions and approve or reject order dispatch.
          </p>

          <input
            type="text"
            placeholder="Optional review notes or exception justification..."
            value={approvalNotes}
            onChange={(e) => setApprovalNotes(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px',
              fontSize: '12px',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              marginBottom: '10px',
              boxSizing: 'border-box',
            }}
          />

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleApprove}
              disabled={actionLoading}
              style={{
                flex: 1,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '8px 12px',
                background: '#059669',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <Check className="w-3.5 h-3.5" />
              Approve Transaction
            </button>
            <button
              onClick={handleReject}
              disabled={actionLoading}
              style={{
                flex: 1,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '8px 12px',
                background: '#dc2626',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <X className="w-3.5 h-3.5" />
              Reject & Hold
            </button>
          </div>

          {actionFeedback && (
            <div style={{ fontSize: '12px', color: '#059669', fontWeight: 600, marginTop: '8px' }}>
              {actionFeedback}
            </div>
          )}
        </div>
      )}

      {/* Executive Decision Highlights */}
      {status?.executive_decision && Object.keys(status.executive_decision).length > 0 && (
        <div
          style={{
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '14px 16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: '#0f172a', marginBottom: '10px', textTransform: 'uppercase' }}>
            <FileCheck className="w-4 h-4 text-blue-600" />
            Executive Consensus & Allocations
          </div>
          <BusinessDataView data={status.executive_decision} layout="grid" />
        </div>
      )}

      {/* Agent Trace Timeline / Chain */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
        <div
          style={{
            padding: '12px 16px',
            background: '#f8fafc',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu className="w-4 h-4 text-blue-600" />
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
              Multi-Agent Decision Chain ({traces.length} Agents)
            </span>
          </div>
          <span style={{ fontSize: '11px', color: '#64748b' }}>
            Chronological Audit Log
          </span>
        </div>

        {traces.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
            No agent traces recorded yet for this transaction.
          </div>
        ) : (
          <div>
            {traces.map((trace, idx) => {
              const layer = AGENT_LAYER[trace.agent_code] || { color: '#64748b', label: 'Agent' };
              const isOpen = openTraceIdx === idx;
              const hasEvents = trace.events_published && trace.events_published.length > 0;

              return (
                <div
                  key={idx}
                  style={{
                    borderBottom: idx === traces.length - 1 ? 'none' : '1px solid #f1f5f9',
                  }}
                >
                  {/* Row summary item */}
                  <div
                    onClick={() => setOpenTraceIdx(isOpen ? null : idx)}
                    style={{
                      padding: '12px 16px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      background: isOpen ? '#f8fafc' : '#ffffff',
                      transition: 'background 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          fontFamily: 'monospace',
                          color: '#64748b',
                          minWidth: '20px',
                        }}
                      >
                        {String(idx + 1).padStart(2, '0')}
                      </span>

                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: trace.status === 'completed' ? '#059669' : '#dc2626',
                        }}
                      />

                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '13px', color: '#0f172a' }}>
                            {trace.agent_code}
                          </span>
                          <span style={{ fontSize: '13px', color: '#334155' }}>
                            {trace.agent_name}
                          </span>
                          <span
                            style={{
                              fontSize: '10px',
                              padding: '1px 6px',
                              borderRadius: '4px',
                              background: `${layer.color}15`,
                              color: layer.color,
                              border: `1px solid ${layer.color}30`,
                              fontWeight: 600,
                            }}
                          >
                            {layer.label}
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                          Duration: {trace.duration_ms}ms &bull; {trace.started_at ? formatDateTime(trace.started_at) : 'Executed'}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {trace.decision && (
                        <span style={{ fontSize: '11px', background: '#ecfdf5', color: '#059669', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                          Decision
                        </span>
                      )}
                      {isOpen ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {isOpen && (
                    <div
                      style={{
                        padding: '14px 16px',
                        background: '#f8fafc',
                        borderTop: '1px solid #e2e8f0',
                      }}
                    >
                      {/* Tabs */}
                      <div style={{ display: 'flex', gap: '4px', marginBottom: '12px', borderBottom: '1px solid #e2e8f0', paddingBottom: '4px' }}>
                        {(['decision', 'output', 'input', 'events'] as const).map((tab) => (
                          <button
                            key={tab}
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveTab(tab);
                            }}
                            style={{
                              padding: '4px 10px',
                              fontSize: '11px',
                              fontWeight: activeTab === tab ? 600 : 500,
                              color: activeTab === tab ? '#2563eb' : '#64748b',
                              background: activeTab === tab ? '#eff6ff' : 'transparent',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              textTransform: 'capitalize',
                            }}
                          >
                            {tab === 'decision' ? 'Agent Decision' : tab === 'output' ? 'State Output' : tab === 'input' ? 'Inputs' : 'Bus Events'}
                          </button>
                        ))}
                      </div>

                      {/* Tab content */}
                      {activeTab === 'decision' && (
                        trace.decision ? (
                          <BusinessDataView data={trace.decision} layout="grid" />
                        ) : (
                          <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic', padding: '8px 0' }}>
                            Pass-through coordination node (no local state override recorded).
                          </div>
                        )
                      )}

                      {activeTab === 'output' && (
                        <BusinessDataView data={trace.output} layout="grid" />
                      )}

                      {activeTab === 'input' && (
                        <BusinessDataView data={trace.input} layout="grid" />
                      )}

                      {activeTab === 'events' && (
                        hasEvents ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {trace.events_published.map((ev: any, ei: number) => (
                              <div
                                key={ei}
                                style={{
                                  background: '#ffffff',
                                  border: '1px solid #e2e8f0',
                                  borderRadius: '6px',
                                  padding: '8px 12px',
                                }}
                              >
                                <div style={{ fontSize: '11px', fontWeight: 600, color: '#7c3aed', marginBottom: '4px' }}>
                                  {ev.event_type || 'Event Published'}
                                </div>
                                <BusinessDataView data={ev.payload || ev} layout="grid" />
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic', padding: '8px 0' }}>
                            No event publications recorded for this node.
                          </div>
                        )
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
