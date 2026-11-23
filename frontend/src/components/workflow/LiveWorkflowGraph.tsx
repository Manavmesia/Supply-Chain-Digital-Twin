import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Play,
  CheckCircle2,
  Clock,
  Layers,
  Sliders,
} from 'lucide-react';
import { workflowApi, ordersApi } from '../../services/api';
import type { WorkflowStatus, AgentTrace } from '../../types';
import { CATALOG_PRODUCTS } from '../../utils/formatters';
import { BusinessDataView } from '../common/BusinessDataView';

interface LiveWorkflowGraphProps {
  initialWorkflowId?: string;
  onWorkflowSelect?: (workflowId: string) => void;
}

const AGENT_ORDER = [
  'ADS-01', // Order Management
  'ADS-02', // Demand Forecast
  'ADS-03', // Inventory
  'ADS-04', // Warehouse
  'ADS-05', // Supplier
  'ADS-06', // Transportation
  'ADS-13', // Sustainability
  'ADS-14', // Quality
  'ADS-09', // Finance
  'ADS-11', // Pricing
  'ADS-10', // Risk
  'ADS-12', // Procurement Strategy
  'ADS-15', // Planner
  'ADS-16', // Negotiation
  'ADS-08', // Customer Service
  'ADS-07', // Manufacturing
  'ADS-17', // CEO Governance
  'ADS-18', // Reporting
];

const AGENT_META: Record<string, { name: string; layer: 'operational' | 'business' | 'coordination'; icon: string; shortRole: string }> = {
  'ADS-01': { name: 'Order Management Agent', layer: 'operational', icon: '📋', shortRole: 'Order Validation & Intake' },
  'ADS-02': { name: 'Demand Forecast Agent', layer: 'business', icon: '📈', shortRole: 'Demand Predictive Analytics' },
  'ADS-03': { name: 'Inventory Management Agent', layer: 'operational', icon: '🏪', shortRole: 'Multi-Echelon Stock Check' },
  'ADS-04': { name: 'Warehouse Operations Agent', layer: 'operational', icon: '🏬', shortRole: 'Fulfillment & Staging' },
  'ADS-05': { name: 'Supplier & Sourcing Agent', layer: 'operational', icon: '🤝', shortRole: 'PO Sourcing & Vendor Selection' },
  'ADS-06': { name: 'Transportation & Logistics Agent', layer: 'operational', icon: '🚚', shortRole: 'Corridor Routing & Carrier TMS' },
  'ADS-13': { name: 'Sustainability & ESG Agent', layer: 'business', icon: '🌱', shortRole: 'Carbon Footprint & ESG Score' },
  'ADS-14': { name: 'Quality Assurance Agent', layer: 'business', icon: '🔬', shortRole: 'Quality Inspection & Lot QC' },
  'ADS-09': { name: 'Finance & Margins Agent', layer: 'business', icon: '💰', shortRole: 'Gross Margin & CapEx Approval' },
  'ADS-11': { name: 'Dynamic Pricing Agent', layer: 'business', icon: '🏷️', shortRole: 'Elasticity & Discount Matrix' },
  'ADS-10': { name: 'Supply Chain Risk Agent', layer: 'business', icon: '⚠️', shortRole: 'Disruption & Geopolitical Risk' },
  'ADS-12': { name: 'Procurement Strategy Agent', layer: 'business', icon: '📑', shortRole: 'Contract Terms & Volume Sourcing' },
  'ADS-15': { name: 'Dynamic Planner Agent', layer: 'coordination', icon: '🧭', shortRole: 'Master Production Schedule & SLA' },
  'ADS-16': { name: 'Agent Negotiation Protocol', layer: 'coordination', icon: '⚖️', shortRole: 'Decentralized Multi-Agent Consensus' },
  'ADS-08': { name: 'Customer Service Agent', layer: 'operational', icon: '💬', shortRole: 'Customer SLA & Notification' },
  'ADS-07': { name: 'Manufacturing Operations Agent', layer: 'operational', icon: '🏭', shortRole: 'Remanufacturing & Assembly' },
  'ADS-17': { name: 'CEO Executive Governance', layer: 'coordination', icon: '👔', shortRole: 'Executive Override & Alignment' },
  'ADS-18': { name: 'Audit & BI Reporting Agent', layer: 'coordination', icon: '📊', shortRole: 'Final State Ledger & Audit' },
};

const LAYER_COLORS = {
  operational: { bg: 'rgba(37,99,235,0.08)', border: '#2563eb', text: '#2563eb', label: 'Operational Layer' },
  business: { bg: 'rgba(124,58,237,0.08)', border: '#7c3aed', text: '#7c3aed', label: 'Business Intelligence' },
  coordination: { bg: 'rgba(16,185,129,0.08)', border: '#059669', text: '#059669', label: 'Consensus & Governance' },
};

const BASELINE_CUSTOMERS = [
  { id: '50000000-0000-0000-0000-000000000001', name: 'Siemens Global Automations' },
  { id: '50000000-0000-0000-0000-000000000002', name: 'Tesla Energy & Storage' },
  { id: '50000000-0000-0000-0000-000000000003', name: 'Schneider Electric Grid' },
  { id: '50000000-0000-0000-0000-000000000004', name: 'Honeywell Aerospace' },
];

export const LiveWorkflowGraph: React.FC<LiveWorkflowGraphProps> = ({
  initialWorkflowId,
  onWorkflowSelect,
}) => {
  const [workflowId, setWorkflowId] = useState<string>(initialWorkflowId || '');
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [traces, setTraces] = useState<AgentTrace[]>([]);
  const [selectedAgentCode, setSelectedAgentCode] = useState<string>('ADS-01');
  const [selectedPassIndex, setSelectedPassIndex] = useState<number | null>(null);
  const [agentFilter, setAgentFilter] = useState<'all' | 'renegotiated' | 'single'>('all');
  const [viewMode, setViewMode] = useState<'stream' | 'blueprint'>('stream');
  const [isExecuting, setIsExecuting] = useState(false);
  const [delaySeconds, setDelaySeconds] = useState<number>(0.8);
  const [recentWorkflows, setRecentWorkflows] = useState<any[]>([]);
  const [autoFollow, setAutoFollow] = useState<boolean>(true);

  // Order launcher inputs
  const [customerId, setCustomerId] = useState(BASELINE_CUSTOMERS[0].id);
  const [productId, setProductId] = useState(CATALOG_PRODUCTS[0].id);
  const [quantity, setQuantity] = useState(15);
  const [activeTab, setActiveTab] = useState<'decision' | 'input' | 'output' | 'events' | 'blackboard'>('decision');

  const pollIntervalRef = useRef<any>(null);
  const isMountedRef = useRef(true);
  const userSelectedRef = useRef<boolean>(false);

  // Load execution config (delay) on mount
  useEffect(() => {
    workflowApi.getConfig().then((res) => {
      if (res && typeof res.delay_seconds === 'number') {
        setDelaySeconds(res.delay_seconds);
      }
    }).catch(() => {});

    workflowApi.list(10).then((res) => {
      if (res?.items) {
        setRecentWorkflows(res.items);
      }
    }).catch(() => {});
  }, []);

  const handleDelayChange = async (newDelay: number) => {
    setDelaySeconds(newDelay);
    try {
      await workflowApi.setConfig(newDelay);
    } catch (e) {
      console.warn('Failed to save delay to backend:', e);
    }
  };

  const loadWorkflowData = useCallback(async (id: string, isSilent = false) => {
    if (!id) return;
    try {
      const [statusRes, traceRes] = await Promise.all([
        workflowApi.getStatus(id),
        workflowApi.getTrace(id),
      ]);
      if (isMountedRef.current) {
        setStatus(statusRes);
        const tr = traceRes?.traces || [];
        setTraces(tr);

        // Auto-select active or last completed agent only if user hasn't manually selected an agent
        if (!userSelectedRef.current) {
          if (statusRes.active_agents && statusRes.active_agents.length > 0) {
            setSelectedAgentCode(statusRes.active_agents[0]);
          } else if (tr.length > 0 && !isSilent) {
            setSelectedAgentCode(tr[tr.length - 1].agent_code);
          }
        }

        if (statusRes.workflow_status === 'completed' || statusRes.workflow_status === 'failed') {
          setIsExecuting(false);
        } else {
          setIsExecuting(true);
        }
      }
    } catch (err) {
      // Keep existing
    }
  }, []);

  // Sync polling when workflow is running
  useEffect(() => {
    if (!workflowId) return;
    loadWorkflowData(workflowId, false);

    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadWorkflowData(workflowId, true);
      }
    }, 450);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [workflowId, loadWorkflowData]);

  // Launch new visual workflow
  const handleStartWorkflow = async () => {
    setIsExecuting(true);
    setStatus(null);
    setTraces([]);
    userSelectedRef.current = false;
    setAutoFollow(true);
    setSelectedPassIndex(null);
    setSelectedAgentCode(AGENT_ORDER[0]);
    try {
      // Best-effort push delay to backend
      try {
        await workflowApi.setConfig(delaySeconds);
      } catch {
        // Silently continue if standalone config endpoint is skipped
      }

      let launchedWorkflowId = '';

      try {
        const res = await workflowApi.start({
          customer_id: customerId,
          items: [{ product_id: productId, quantity }],
          delay_seconds: delaySeconds,
        });
        launchedWorkflowId = res.workflow_id;
      } catch (err: any) {
        // Resilient fallback to commercial orders API which executes the exact same 18-agent LangGraph workflow
        const orderRes = await ordersApi.create({
          customer_id: customerId,
          priority: 'standard',
          items: [{ product_id: productId, quantity }],
        });
        launchedWorkflowId = orderRes.workflow_id;
      }

      setWorkflowId(launchedWorkflowId);
      if (onWorkflowSelect) onWorkflowSelect(launchedWorkflowId);
      loadWorkflowData(launchedWorkflowId, false);

      // Refresh recent list
      workflowApi.list(10).then((r) => setRecentWorkflows(r.items || [])).catch(() => {});
    } catch (err: any) {
      alert(`Failed to start workflow: ${err.message}`);
      setIsExecuting(false);
    }
  };

  // Group traces by agent code to support multi-cycle negotiation inspectability
  const tracesByAgent = new Map<string, AgentTrace[]>();
  traces.forEach((t) => {
    const list = tracesByAgent.get(t.agent_code) || [];
    list.push(t);
    tracesByAgent.set(t.agent_code, list);
  });

  // Latest trace for each agent
  const traceMap = new Map<string, AgentTrace>();
  traces.forEach((t) => traceMap.set(t.agent_code, t));

  const isWorkflowDone = status?.workflow_status === 'completed' || status?.workflow_status === 'failed';
  const activeAgents = isWorkflowDone ? [] : (status?.active_agents || []);
  const selectedAgentTraces = tracesByAgent.get(selectedAgentCode) || [];

  // Determine active pass index for inspector view
  const activePassIndex =
    selectedPassIndex !== null && selectedPassIndex >= 0 && selectedPassIndex < selectedAgentTraces.length
      ? selectedPassIndex
      : selectedAgentTraces.length > 0
      ? selectedAgentTraces.length - 1
      : 0;

  const selectedTrace = selectedAgentTraces[activePassIndex] || traceMap.get(selectedAgentCode);

  // Accurate distinct completed agents count (out of 18)
  const completedAgentsSet = new Set(
    traces
      .filter((t) => t.status === 'completed' || t.duration_ms !== undefined)
      .map((t) => t.agent_code)
  );
  const completedCount = AGENT_ORDER.filter((code) => completedAgentsSet.has(code)).length;
  const progressPct = Math.min(100, Math.round((completedCount / AGENT_ORDER.length) * 100));

  // Multi-pass vs single-pass breakdown for executive presentation
  const multiPassAgents = AGENT_ORDER.filter((code) => (tracesByAgent.get(code)?.length || 0) > 1);
  const singlePassAgents = AGENT_ORDER.filter((code) => (tracesByAgent.get(code)?.length || 0) === 1);

  // Dynamic Live Execution Chain: Agents that have executed or are actively executing
  const executedCodes = traces.map((t) => t.agent_code);
  const liveChain: string[] = [];
  executedCodes.forEach((c) => {
    if (!liveChain.includes(c)) liveChain.push(c);
  });
  activeAgents.forEach((c) => {
    if (!liveChain.includes(c)) liveChain.push(c);
  });

  // Base list: dynamic progressive stream (default) vs static blueprint
  const baseList = viewMode === 'stream' ? liveChain : AGENT_ORDER;

  // Filtered agent list based on client demonstration view
  const displayedAgents = baseList.filter((code) => {
    const count = tracesByAgent.get(code)?.length || 0;
    if (agentFilter === 'renegotiated') return count > 1;
    if (agentFilter === 'single') return count === 1;
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Pacing & Execution Control Bar */}
      <div
        style={{
          background: 'var(--c-bg-card)',
          border: '1px solid var(--c-border)',
          borderRadius: '12px',
          padding: '16px 20px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={18} color="var(--c-brand-accent)" />
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--c-text-primary)' }}>
              Execution Delay:
            </span>
          </div>

          {/* Quick preset buttons */}
          <div style={{ display: 'flex', gap: '6px' }}>
            {[
              { label: 'Instant (0s)', val: 0.0 },
              { label: 'Fast (0.4s)', val: 0.4 },
              { label: 'Balanced (0.8s)', val: 0.8 },
              { label: 'Cinematic (1.5s)', val: 1.5 },
            ].map((p) => {
              const isSelected = Math.abs(delaySeconds - p.val) < 0.05;
              return (
                <button
                  key={p.val}
                  type="button"
                  onClick={() => handleDelayChange(p.val)}
                  style={{
                    padding: '5px 11px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: isSelected ? 600 : 500,
                    background: isSelected ? 'var(--c-brand-accent)' : 'var(--c-bg-subtle)',
                    color: isSelected ? '#ffffff' : 'var(--c-text-secondary)',
                    border: isSelected ? '1px solid var(--c-brand-accent)' : '1px solid var(--c-border)',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>

          {/* Fine-tune slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '6px' }}>
            <input
              type="range"
              min="0"
              max="2.5"
              step="0.1"
              value={delaySeconds}
              onChange={(e) => handleDelayChange(parseFloat(e.target.value))}
              style={{ width: '100px', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--c-brand-accent)', fontWeight: 600 }}>
              {delaySeconds.toFixed(1)}s / step
            </span>
          </div>
        </div>

        {/* Workflow Launcher & Select */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <select
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            disabled={isExecuting}
            style={{
              fontSize: '12px',
              padding: '6px 10px',
              borderRadius: '6px',
              border: '1px solid var(--c-border)',
              background: 'var(--c-bg-subtle)',
              color: 'var(--c-text-primary)',
            }}
          >
            {BASELINE_CUSTOMERS.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <select
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            disabled={isExecuting}
            style={{
              fontSize: '12px',
              padding: '6px 10px',
              borderRadius: '6px',
              border: '1px solid var(--c-border)',
              background: 'var(--c-bg-subtle)',
              color: 'var(--c-text-primary)',
            }}
          >
            {CATALOG_PRODUCTS.slice(0, 5).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <input
            type="number"
            min="1"
            max="1000"
            value={quantity}
            onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
            disabled={isExecuting}
            style={{
              width: '56px',
              fontSize: '12px',
              padding: '6px 8px',
              borderRadius: '6px',
              border: '1px solid var(--c-border)',
              background: 'var(--c-bg-subtle)',
              color: 'var(--c-text-primary)',
            }}
          />

          {recentWorkflows.length > 0 && (
            <select
              value={workflowId}
              onChange={(e) => {
                setWorkflowId(e.target.value);
                if (onWorkflowSelect) onWorkflowSelect(e.target.value);
              }}
              style={{
                fontSize: '12px',
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid var(--c-border)',
                background: 'var(--c-bg-subtle)',
                color: 'var(--c-text-primary)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <option value="">Select Past...</option>
              {recentWorkflows.map((w) => (
                <option key={w.workflow_id} value={w.workflow_id}>
                  {w.workflow_id.slice(0, 10)}... ({w.workflow_status || w.status})
                </option>
              ))}
            </select>
          )}

          <button
            onClick={handleStartWorkflow}
            disabled={isExecuting}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 16px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 600,
              background: isExecuting ? 'var(--c-bg-subtle)' : 'linear-gradient(135deg, #2563eb, #1d4ed8)',
              color: isExecuting ? 'var(--c-text-muted)' : '#ffffff',
              border: 'none',
              cursor: isExecuting ? 'not-allowed' : 'pointer',
              boxShadow: isExecuting ? 'none' : '0 2px 8px rgba(37,99,235,0.3)',
              transition: 'all 0.18s',
            }}
          >
            {isExecuting ? (
              <>
                <Clock size={15} className="animate-spin" />
                <span>Executing Agents...</span>
              </>
            ) : (
              <>
                <Play size={15} fill="currentColor" />
                <span>Run Live Workflow</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Workflow Progress Status Bar */}
      <div
        style={{
          background: 'var(--c-bg-card)',
          border: '1px solid var(--c-border)',
          borderRadius: '12px',
          padding: '16px 20px',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--c-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Workflow Progress
            </span>
            {workflowId && (
              <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--c-text-muted)' }}>
                ID: {workflowId.slice(0, 16)}...
              </span>
            )}
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: '12px',
                textTransform: 'uppercase',
                background:
                  status?.workflow_status === 'completed'
                    ? 'rgba(16,185,129,0.1)'
                    : isExecuting
                    ? 'rgba(37,99,235,0.1)'
                    : 'var(--c-bg-subtle)',
                color:
                  status?.workflow_status === 'completed'
                    ? '#059669'
                    : isExecuting
                    ? '#2563eb'
                    : 'var(--c-text-muted)',
                border: `1px solid ${
                  status?.workflow_status === 'completed'
                    ? 'rgba(16,185,129,0.3)'
                    : isExecuting
                    ? 'rgba(37,99,235,0.3)'
                    : 'var(--c-border)'
                }`,
              }}
            >
              {status?.workflow_status || (workflowId ? 'Active' : 'Ready')}
            </span>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--c-text-muted)', display: 'flex', alignItems: 'center', gap: '14px' }}>
            <span>
              Agents Completed: <strong style={{ color: 'var(--c-text-primary)' }}>{completedCount}</strong> / {AGENT_ORDER.length}
              {traces.length > completedCount && (
                <span style={{ fontSize: '11px', color: 'var(--c-text-muted)', marginLeft: '6px' }}>
                  ({traces.length} steps in consensus cycles)
                </span>
              )}
            </span>
            {activeAgents.length > 0 && (
              <span style={{ color: 'var(--c-brand-accent)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: 'var(--c-brand-accent)',
                    display: 'inline-block',
                    animation: 'pulse 1.2s infinite',
                  }}
                />
                Active: {activeAgents[0]} ({AGENT_META[activeAgents[0]]?.name.split(' ')[0]})
              </span>
            )}
          </div>
        </div>

        {/* Progress Bar Track */}
        <div style={{ width: '100%', height: '8px', background: 'var(--c-bg-subtle)', borderRadius: '4px', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${progressPct}%`,
              background: 'linear-gradient(90deg, #2563eb, #10b981)',
              borderRadius: '4px',
              transition: 'width 0.3s ease-in-out',
            }}
          />
        </div>

        {/* Executive Multi-Agent Consensus Summary Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginTop: '14px' }}>
          <div style={{ background: 'var(--c-bg-subtle)', border: '1px solid var(--c-border)', borderRadius: '8px', padding: '10px 14px' }}>
            <div style={{ fontSize: '11px', color: 'var(--c-text-muted)', fontWeight: 600 }}>FIRST-PASS ALIGNMENT</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#059669', marginTop: '2px' }}>
              {singlePassAgents.length} Agents
            </div>
            <div style={{ fontSize: '11px', color: 'var(--c-text-secondary)', marginTop: '2px' }}>
              Executed once (agreed on first proposal)
            </div>
          </div>
          <div style={{ background: 'var(--c-bg-subtle)', border: '1px solid var(--c-border)', borderRadius: '8px', padding: '10px 14px' }}>
            <div style={{ fontSize: '11px', color: 'var(--c-text-muted)', fontWeight: 600 }}>RENEGOTIATED AGENTS</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: multiPassAgents.length > 0 ? '#7c3aed' : 'var(--c-text-primary)', marginTop: '2px' }}>
              {multiPassAgents.length} Agents {multiPassAgents.length > 0 ? '🔄' : ''}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--c-text-secondary)', marginTop: '2px' }}>
              {multiPassAgents.length > 0 ? 'Participated in multi-pass consensus cycles' : 'Zero contested constraints'}
            </div>
          </div>
          <div style={{ background: 'var(--c-bg-subtle)', border: '1px solid var(--c-border)', borderRadius: '8px', padding: '10px 14px' }}>
            <div style={{ fontSize: '11px', color: 'var(--c-text-muted)', fontWeight: 600 }}>TOTAL PIPELINE INVOCATIONS</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--c-brand-accent)', marginTop: '2px' }}>
              {traces.length} Steps
            </div>
            <div style={{ fontSize: '11px', color: 'var(--c-text-secondary)', marginTop: '2px' }}>
              Across 18 specialized autonomous roles
            </div>
          </div>
        </div>
      </div>

      {/* Main Split Layout: Workflow DAG Grid (Left) + Agent Inspector (Right) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(500px, 1.8fr) 1.2fr', gap: '20px', alignItems: 'start' }}>
        {/* Visual Workflow Graph */}
        <div
          style={{
            background: 'var(--c-bg-card)',
            border: '1px solid var(--c-border)',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: 'var(--shadow-card)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--c-text-primary)', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={16} color="var(--c-brand-accent)" />
                {viewMode === 'stream' ? 'Live Execution Stream' : '18-Agent LangGraph Architecture'}
              </h3>

              {/* View Mode Toggle: Progressive Execution Stream vs Full Architecture */}
              <div style={{ display: 'inline-flex', background: 'var(--c-bg-subtle)', borderRadius: '6px', padding: '2px', border: '1px solid var(--c-border)' }}>
                <button
                  type="button"
                  onClick={() => setViewMode('stream')}
                  style={{
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: viewMode === 'stream' ? 700 : 500,
                    background: viewMode === 'stream' ? 'var(--c-bg-card)' : 'transparent',
                    color: viewMode === 'stream' ? 'var(--c-brand-accent)' : 'var(--c-text-secondary)',
                    border: 'none',
                    cursor: 'pointer',
                    boxShadow: viewMode === 'stream' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                  }}
                  title="Progressively display agents only as they are called and executed"
                >
                  Live Stream ({liveChain.length})
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('blueprint')}
                  style={{
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: viewMode === 'blueprint' ? 700 : 500,
                    background: viewMode === 'blueprint' ? 'var(--c-bg-card)' : 'transparent',
                    color: viewMode === 'blueprint' ? 'var(--c-brand-accent)' : 'var(--c-text-secondary)',
                    border: 'none',
                    cursor: 'pointer',
                    boxShadow: viewMode === 'blueprint' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                  }}
                  title="Show all 18 agent roles in catalog"
                >
                  All 18 Roles
                </button>
              </div>
            </div>

            {/* Layer Legend */}
            <div style={{ display: 'flex', gap: '6px' }}>
              {Object.entries(LAYER_COLORS).map(([k, cfg]) => (
                <span
                  key={k}
                  style={{
                    fontSize: '11px',
                    color: cfg.text,
                    background: cfg.bg,
                    border: `1px solid ${cfg.border}`,
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontWeight: 500,
                  }}
                >
                  {cfg.label}
                </span>
              ))}
            </div>
          </div>

          {/* Demonstration Filter Bar: Highlight Multi-Pass vs Single-Pass */}
          {displayedAgents.length > 0 && (
            <div style={{ display: 'flex', gap: '6px', marginBottom: '14px', paddingBottom: '12px', borderBottom: '1px solid var(--c-border-subtle)' }}>
              <button
                type="button"
                onClick={() => setAgentFilter('all')}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: agentFilter === 'all' ? 700 : 500,
                  background: agentFilter === 'all' ? 'var(--c-brand-accent)' : 'var(--c-bg-subtle)',
                  color: agentFilter === 'all' ? '#ffffff' : 'var(--c-text-secondary)',
                  border: '1px solid var(--c-border)',
                  cursor: 'pointer',
                }}
              >
                All Displayed ({displayedAgents.length})
              </button>
              {multiPassAgents.length > 0 && (
                <button
                  type="button"
                  onClick={() => setAgentFilter('renegotiated')}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '11px',
                    fontWeight: agentFilter === 'renegotiated' ? 700 : 500,
                    background: agentFilter === 'renegotiated' ? '#7c3aed' : 'var(--c-bg-subtle)',
                    color: agentFilter === 'renegotiated' ? '#ffffff' : 'var(--c-text-secondary)',
                    border: '1px solid var(--c-border)',
                    cursor: 'pointer',
                  }}
                >
                  Renegotiated ({multiPassAgents.length}) 🔄
                </button>
              )}
              <button
                type="button"
                onClick={() => setAgentFilter('single')}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: agentFilter === 'single' ? 700 : 500,
                  background: agentFilter === 'single' ? '#059669' : 'var(--c-bg-subtle)',
                  color: agentFilter === 'single' ? '#ffffff' : 'var(--c-text-secondary)',
                  border: '1px solid var(--c-border)',
                  cursor: 'pointer',
                }}
              >
                Completed ({singlePassAgents.length}) ✓
              </button>
            </div>
          )}

          {/* Sequential Agent Nodes or Ready State */}
          {displayedAgents.length === 0 ? (
            <div
              style={{
                padding: '44px 24px',
                textAlign: 'center',
                background: 'var(--c-bg-subtle)',
                border: '2px dashed var(--c-border)',
                borderRadius: '12px',
              }}
            >
              <div
                style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '50%',
                  background: 'rgba(37,99,235,0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px',
                  color: 'var(--c-brand-accent)',
                }}
              >
                <Play size={24} fill="currentColor" />
              </div>
              <h4 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 8px', color: 'var(--c-text-primary)' }}>
                Multi-Agent Pipeline Ready for Execution
              </h4>
              <p style={{ fontSize: '13px', color: 'var(--c-text-secondary)', maxWidth: '440px', margin: '0 auto 20px', lineHeight: 1.5 }}>
                Agents have not been executed yet. Click <strong>"Run Live Workflow"</strong> above to observe agents appear dynamically step-by-step as each domain specialist is invoked.
              </p>
              <button
                type="button"
                onClick={handleStartWorkflow}
                disabled={isExecuting}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 22px',
                  borderRadius: '8px',
                  fontSize: '13px',
                  fontWeight: 600,
                  background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                  color: '#ffffff',
                  border: 'none',
                  cursor: 'pointer',
                  boxShadow: '0 2px 10px rgba(37,99,235,0.3)',
                }}
              >
                <Play size={15} fill="currentColor" />
                <span>Launch Live Demonstration</span>
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {displayedAgents.map((code, idx) => {
                const meta = AGENT_META[code] || { name: code, layer: 'operational', icon: '🤖', shortRole: '' };
                const layerStyle = LAYER_COLORS[meta.layer];
                const nodeTraces = tracesByAgent.get(code) || [];
                const executionCount = nodeTraces.length;
                const trace = nodeTraces[nodeTraces.length - 1] || traceMap.get(code);
                const isRunning = !isWorkflowDone && activeAgents.includes(code);
                const isCompleted = !isRunning && Boolean(trace && (trace.status === 'completed' || trace.duration_ms !== undefined));
                const isFailed = !isRunning && trace?.status === 'failed';
                const isSelected = selectedAgentCode === code;

                return (
                  <div key={code}>
                    <div
                      onClick={() => {
                        userSelectedRef.current = true;
                        setAutoFollow(false);
                        setSelectedAgentCode(code);
                        setSelectedPassIndex(null);
                      }}
                      style={{
                        background: isSelected
                          ? 'rgba(37,99,235,0.06)'
                          : isRunning
                          ? 'rgba(37,99,235,0.03)'
                          : 'var(--c-bg-card)',
                        border: isSelected
                          ? '2px solid var(--c-brand-accent)'
                          : isRunning
                          ? '2px solid #3b82f6'
                          : isFailed
                          ? '1px solid #ef4444'
                          : isCompleted
                          ? '1px solid rgba(16,185,129,0.4)'
                          : '1px solid var(--c-border)',
                        borderRadius: '8px',
                        padding: '10px 14px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        boxShadow: isRunning ? '0 0 12px rgba(37,99,235,0.2)' : 'none',
                        position: 'relative',
                      }}
                    >
                      {/* Index & Icon */}
                      <div
                        style={{
                          width: '28px',
                          height: '28px',
                          borderRadius: '6px',
                          background: isRunning ? 'rgba(37,99,235,0.1)' : isCompleted ? 'rgba(16,185,129,0.1)' : isFailed ? 'rgba(239,68,68,0.1)' : 'var(--c-bg-subtle)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '14px',
                        }}
                      >
                        {isRunning ? (
                          <Clock size={16} className="animate-spin" color="#2563eb" />
                        ) : isCompleted ? (
                          <CheckCircle2 size={16} color="#059669" />
                        ) : (
                          meta.icon
                        )}
                      </div>

                      {/* Agent Code, Name, Layer & Frequency Pill */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--c-text-muted)' }}>
                            {code}
                          </span>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--c-text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {meta.name}
                          </span>
                          <span
                            style={{
                              fontSize: '10px',
                              fontWeight: 500,
                              padding: '1px 6px',
                              borderRadius: '4px',
                              background: layerStyle.bg,
                              color: layerStyle.text,
                              border: `1px solid ${layerStyle.border}`,
                            }}
                          >
                            {meta.layer}
                          </span>

                          {/* Frequency Indicator Pill */}
                          {executionCount > 0 && (
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 700,
                                padding: '1px 7px',
                                borderRadius: '4px',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '3px',
                                background:
                                  executionCount > 1
                                    ? 'rgba(124,58,237,0.12)'
                                    : 'rgba(16,185,129,0.08)',
                                color: executionCount > 1 ? '#7c3aed' : '#059669',
                                border: `1px solid ${
                                  executionCount > 1
                                    ? 'rgba(124,58,237,0.3)'
                                    : 'rgba(16,185,129,0.25)'
                                }`,
                              }}
                              title={
                                executionCount > 1
                                  ? `Executed ${executionCount} times across consensus loops`
                                  : 'Executed 1 time: Optimal agreement on initial pass'
                              }
                            >
                              {executionCount === 1 ? '1× Pass' : `🔄 Executed ${executionCount}×`}
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--c-text-muted)', marginTop: '2px' }}>
                          {trace?.decision
                            ? (typeof trace.decision === 'object' && 'summary' in trace.decision
                                ? String((trace.decision as any).summary)
                                : typeof trace.decision === 'object' && 'action' in trace.decision
                                ? String((trace.decision as any).action)
                                : meta.shortRole)
                            : meta.shortRole}
                        </div>
                      </div>

                      {/* Status & Timing */}
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '3px' }}>
                        {isRunning ? (
                          <span style={{ fontSize: '10px', fontWeight: 700, color: '#2563eb', animation: 'pulse 1s infinite' }}>
                            PROCESSING...
                          </span>
                        ) : isFailed ? (
                          <span style={{ fontSize: '11px', fontWeight: 600, color: '#ef4444' }}>
                            Failed
                          </span>
                        ) : isCompleted ? (
                          <>
                            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#059669' }}>
                              {trace?.duration_ms ? `${trace.duration_ms}ms ✓` : 'Completed ✓'}
                            </span>
                            {executionCount > 1 && (
                              <span style={{ fontSize: '10px', fontWeight: 600, color: '#7c3aed' }}>
                                Pass {executionCount} of {executionCount}
                              </span>
                            )}
                          </>
                        ) : (
                          <span style={{ fontSize: '11px', color: 'var(--c-text-muted)' }}>
                            Pending
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Flow Arrow to next node */}
                    {idx < displayedAgents.length - 1 && (
                      <div style={{ display: 'flex', justifyContent: 'center', padding: '2px 0' }}>
                        <span style={{ color: isCompleted ? '#059669' : 'var(--c-border)', fontSize: '12px' }}>
                          ↓
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Live In-Progress indicator when executing downstream */}
              {isExecuting && (
                <div
                  style={{
                    padding: '12px',
                    background: 'rgba(37,99,235,0.04)',
                    border: '1px dashed #3b82f6',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    color: '#2563eb',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}
                >
                  <Clock size={15} className="animate-spin" />
                  <span>Evaluating and dispatching next downstream agent...</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Panel: Agent Call Inspector */}
        <div
          style={{
            background: 'var(--c-bg-card)',
            border: '1px solid var(--c-border)',
            borderRadius: '12px',
            padding: '20px',
            position: 'sticky',
            top: '20px',
            boxShadow: 'var(--shadow-card)',
            maxHeight: 'calc(100vh - 120px)',
            overflowY: 'auto',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', borderBottom: '1px solid var(--c-border)', paddingBottom: '12px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '16px' }}>{AGENT_META[selectedAgentCode]?.icon || '🤖'}</span>
                <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: 'var(--c-text-primary)' }}>
                  {selectedAgentCode} · {AGENT_META[selectedAgentCode]?.name}
                </h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px' }}>
                <span style={{ fontSize: '11px', color: 'var(--c-text-muted)' }}>
                  {AGENT_META[selectedAgentCode]?.shortRole}
                </span>
                {selectedAgentTraces.length > 1 && (
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      background: 'rgba(124,58,237,0.1)',
                      color: '#7c3aed',
                      border: '1px solid rgba(124,58,237,0.3)',
                    }}
                  >
                    Consensus Cycle {selectedAgentTraces.length} of {selectedAgentTraces.length}
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {!autoFollow && isExecuting && (
                <button
                  type="button"
                  onClick={() => {
                    userSelectedRef.current = false;
                    setAutoFollow(true);
                    if (activeAgents.length > 0) {
                      setSelectedAgentCode(activeAgents[0]);
                    } else if (traces.length > 0) {
                      setSelectedAgentCode(traces[traces.length - 1].agent_code);
                    }
                  }}
                  style={{
                    fontSize: '11px',
                    padding: '3px 8px',
                    borderRadius: '6px',
                    background: 'rgba(37,99,235,0.08)',
                    color: 'var(--c-brand-accent)',
                    border: '1px solid rgba(37,99,235,0.25)',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontWeight: 600,
                  }}
                >
                  ● Resume Follow
                </button>
              )}

              {autoFollow && isExecuting && (
                <span
                  style={{
                    fontSize: '11px',
                    padding: '3px 8px',
                    borderRadius: '6px',
                    background: 'rgba(16,185,129,0.1)',
                    color: '#059669',
                    border: '1px solid rgba(16,185,129,0.25)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontWeight: 600,
                  }}
                >
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', display: 'inline-block', animation: 'pulse 1.2s infinite' }} />
                  Live Following
                </span>
              )}

              {selectedTrace && (
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: '12px',
                    background: 'rgba(16,185,129,0.1)',
                    color: '#059669',
                    border: '1px solid rgba(16,185,129,0.3)',
                  }}
                >
                  {selectedTrace.duration_ms !== undefined ? `${selectedTrace.duration_ms} ms` : 'Completed'}
                </span>
              )}
            </div>
          </div>

          {/* Multi-Pass Consensus History or Single-Pass Confirmation */}
          {selectedAgentTraces.length > 1 && (
            <div
              style={{
                background: 'rgba(124,58,237,0.06)',
                border: '1px solid rgba(124,58,237,0.22)',
                borderRadius: '8px',
                padding: '12px 14px',
                marginBottom: '16px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '14px' }}>🔄</span>
                  <strong style={{ fontSize: '12px', color: '#7c3aed' }}>
                    Renegotiated Across {selectedAgentTraces.length} Consensus Cycles
                  </strong>
                </div>
                <span style={{ fontSize: '11px', color: 'var(--c-text-muted)', fontWeight: 600 }}>
                  Inspecting Pass {activePassIndex + 1} of {selectedAgentTraces.length}
                </span>
              </div>
              <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--c-text-secondary)', lineHeight: 1.4 }}>
                This agent executed <strong>{selectedAgentTraces.length} times</strong> to harmonize conflicting goals with other agents. Click a pass below to inspect the decision evolution:
              </p>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {selectedAgentTraces.map((_, pIdx) => {
                  const isCurrent = activePassIndex === pIdx;
                  return (
                    <button
                      key={pIdx}
                      type="button"
                      onClick={() => setSelectedPassIndex(pIdx)}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: isCurrent ? 700 : 500,
                        background: isCurrent ? '#7c3aed' : 'var(--c-bg-card)',
                        color: isCurrent ? '#ffffff' : 'var(--c-text-secondary)',
                        border: isCurrent ? '1px solid #7c3aed' : '1px solid var(--c-border)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        boxShadow: isCurrent ? '0 1px 4px rgba(124,58,237,0.3)' : 'none',
                      }}
                    >
                      {pIdx === 0
                        ? `Pass 1 (Initial Proposal)`
                        : pIdx === selectedAgentTraces.length - 1
                        ? `Pass ${pIdx + 1} (Final Agreement ✓)`
                        : `Pass ${pIdx + 1} (Counter-Offer)`}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {selectedAgentTraces.length === 1 && (
            <div
              style={{
                background: 'rgba(16,185,129,0.06)',
                border: '1px solid rgba(16,185,129,0.2)',
                borderRadius: '8px',
                padding: '10px 14px',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <CheckCircle2 size={16} color="#059669" />
              <span style={{ fontSize: '12px', color: '#059669', fontWeight: 600 }}>
                Executed 1 Time: Optimal agreement reached on initial proposal without requiring renegotiation loops.
              </span>
            </div>
          )}

          {/* Navigation Tabs */}
          <div style={{ display: 'flex', gap: '6px', marginBottom: '16px', borderBottom: '1px solid var(--c-border-subtle)', paddingBottom: '8px' }}>
            {(['decision', 'output', 'input', 'events', 'blackboard'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  background: activeTab === tab ? 'var(--c-bg-subtle)' : 'transparent',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '5px 10px',
                  fontSize: '12px',
                  fontWeight: activeTab === tab ? 600 : 500,
                  color: activeTab === tab ? 'var(--c-brand-accent)' : 'var(--c-text-secondary)',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Inspector Content */}
          {!selectedTrace ? (
            <div style={{ padding: '30px 10px', textAlign: 'center', color: 'var(--c-text-muted)' }}>
              <Clock size={28} style={{ margin: '0 auto 10px', opacity: 0.5 }} />
              <p style={{ fontSize: '13px', margin: 0 }}>
                {activeAgents.includes(selectedAgentCode)
                  ? 'Agent currently executing... Stream updates will appear momentarily.'
                  : 'This agent has not executed yet in the current workflow run.'}
              </p>
            </div>
          ) : (
            <div>
              {/* Tab: Decision */}
              {activeTab === 'decision' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ background: 'var(--c-bg-subtle)', border: '1px solid var(--c-border)', borderRadius: '8px', padding: '14px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--c-text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                      Agent Decision & Autonomous Policy
                    </div>
                    {selectedTrace.decision ? (
                      <BusinessDataView data={selectedTrace.decision} layout="grid" />
                    ) : (
                      <p style={{ margin: 0, fontSize: '12px', color: 'var(--c-text-secondary)', fontStyle: 'italic' }}>
                        Operational pass-through node. Standard state policy applied with no exceptions.
                      </p>
                    )}
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div style={{ background: 'var(--c-bg-subtle)', borderRadius: '6px', padding: '10px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--c-text-muted)' }}>Execution Started</span>
                      <div style={{ fontSize: '12px', fontWeight: 600, marginTop: '2px', color: 'var(--c-text-primary)' }}>
                        {selectedTrace.started_at ? new Date(selectedTrace.started_at).toLocaleTimeString() : '—'}
                      </div>
                    </div>
                    <div style={{ background: 'var(--c-bg-subtle)', borderRadius: '6px', padding: '10px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--c-text-muted)' }}>Execution Completed</span>
                      <div style={{ fontSize: '12px', fontWeight: 600, marginTop: '2px', color: 'var(--c-text-primary)' }}>
                        {selectedTrace.finished_at ? new Date(selectedTrace.finished_at).toLocaleTimeString() : '—'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab: Output State Delta */}
              {activeTab === 'output' && (
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--c-text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Output State Modifications
                  </div>
                  <BusinessDataView
                    data={selectedTrace.output || {}}
                    layout="grid"
                    emptyMessage="No output state modifications contributed by this node."
                  />
                </div>
              )}

              {/* Tab: Input State Snapshot */}
              {activeTab === 'input' && (
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--c-text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Input State Snapshot
                  </div>
                  <BusinessDataView
                    data={selectedTrace.input || {}}
                    layout="grid"
                    emptyMessage="No input state snapshot captured for this node."
                  />
                </div>
              )}

              {/* Tab: Events Emitted */}
              {activeTab === 'events' && (
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--c-text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Events Published to Bus ({selectedTrace.events_published?.length || 0})
                  </div>
                  {(!selectedTrace.events_published || selectedTrace.events_published.length === 0) ? (
                    <div style={{ padding: '16px', background: 'var(--c-bg-subtle)', borderRadius: '8px', color: 'var(--c-text-muted)', fontSize: '12px', fontStyle: 'italic' }}>
                      No domain events published to event bus by this agent node.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {selectedTrace.events_published.map((ev: any, i: number) => (
                        <div key={i} style={{ background: 'var(--c-bg-subtle)', border: '1px solid var(--c-border)', borderRadius: '8px', padding: '12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--c-brand-accent)' }}>
                              {ev.event_type || 'Domain Event'}
                            </span>
                            <span style={{ fontSize: '10px', fontWeight: 600, padding: '2px 6px', borderRadius: '4px', background: 'rgba(37,99,235,0.1)', color: 'var(--c-brand-accent)' }}>
                              Event Bus
                            </span>
                          </div>
                          <BusinessDataView data={ev.payload || ev} layout="grid" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab: Blackboard */}
              {activeTab === 'blackboard' && (
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--c-text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Multi-Agent Blackboard Consensus
                  </div>
                  {status?.blackboard && Object.keys(status.blackboard).length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {Object.entries(status.blackboard).map(([topic, entries]) => (
                        <div key={topic} style={{ background: 'var(--c-bg-subtle)', border: '1px solid var(--c-border)', borderRadius: '8px', padding: '12px' }}>
                          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--c-text-primary)', marginBottom: '8px', textTransform: 'capitalize' }}>
                            Topic: {topic.replace(/[_-]+/g, ' ')}
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {(entries as any[]).map((entry, idx) => (
                              <div key={idx} style={{ background: '#ffffff', border: '1px solid var(--c-border-subtle)', borderRadius: '6px', padding: '10px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                                  <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--c-brand-accent)' }}>
                                    {entry.agent_id}
                                  </span>
                                  <span
                                    style={{
                                      fontSize: '10px',
                                      fontWeight: 600,
                                      padding: '1px 6px',
                                      borderRadius: '4px',
                                      textTransform: 'uppercase',
                                      background:
                                        entry.status === 'accepted'
                                          ? 'rgba(16,185,129,0.1)'
                                          : entry.status === 'contested'
                                          ? 'rgba(239,68,68,0.1)'
                                          : 'rgba(245,158,11,0.1)',
                                      color:
                                        entry.status === 'accepted'
                                          ? '#059669'
                                          : entry.status === 'contested'
                                          ? '#ef4444'
                                          : '#d97706',
                                    }}
                                  >
                                    {entry.status}
                                  </span>
                                </div>
                                {entry.rationale && (
                                  <p style={{ margin: '0 0 8px', fontSize: '12px', color: 'var(--c-text-secondary)', lineHeight: 1.4 }}>
                                    {entry.rationale}
                                  </p>
                                )}
                                {entry.data && (
                                  <BusinessDataView data={entry.data} layout="grid" />
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ padding: '16px', background: 'var(--c-bg-subtle)', borderRadius: '8px', color: 'var(--c-text-muted)', fontSize: '12px', fontStyle: 'italic' }}>
                      Consensus reached across all agents with zero contested blackboard items.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
