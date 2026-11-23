import React, { useState, useEffect, useRef } from 'react';
import {
  Zap,
  ShieldAlert,
  Clock,
  Sliders,
} from 'lucide-react';
import { eventsApi, workflowApi } from '../../services/api';
import type { EventRecord, EventRemediationStep } from '../../types';

interface LiveEventGraphProps {
  initialEventId?: string;
  onEventSelect?: (eventId: string) => void;
}

const PRESET_EVENTS = [
  {
    type: 'InventoryLow',
    name: 'Stockout / Low Inventory',
    icon: '🏪',
    subscribers: ['ADS-03', 'ADS-05'],
    defaultPayload: { sku: 'ELEC-001', quantity: 120, warehouse_id: '10000000-0000-0000-0000-000000000001' },
    summary: 'Safety stock breached at distribution center. Triggers ADS-03 deficit detection and ADS-05 autonomous PO issuance.',
  },
  {
    type: 'DeliveryDelayed',
    name: 'Carrier Logistics Bottleneck',
    icon: '🚚',
    subscribers: ['ADS-06', 'ADS-15'],
    defaultPayload: { shipment_id: 'SHP-NJ-AIR-892', delay_days: 4, location: 'Newark Distribution Center' },
    summary: 'Transit delay of 4 days flagged. Triggers ADS-06 expedited freight rerouting and ADS-15 SLA preservation.',
  },
  {
    type: 'SupplierUnavailable',
    name: 'Supplier Capacity Outage',
    icon: '⚠️',
    subscribers: ['ADS-10', 'ADS-05'],
    defaultPayload: { supplier_name: 'Pacific Silicon Foundry', reason: 'Unplanned power outage' },
    summary: 'Primary tier-1 supplier unavailable. Triggers ADS-10 risk assessment and ADS-05 redundant supplier failover.',
  },
  {
    type: 'QualityAlertRaised',
    name: 'Quality Defect / Inspection Failed',
    icon: '🔬',
    subscribers: ['ADS-14', 'ADS-07'],
    defaultPayload: { batch_id: 'LOT-QC-9921', defect_type: 'Thermal tolerance breach', product_name: 'Server CPU 32-core' },
    summary: 'Defective batch identified. Triggers ADS-14 lot quarantine and ADS-07 emergency remanufacturing order.',
  },
  {
    type: 'DemandSpike',
    name: 'Market Demand Surge',
    icon: '📈',
    subscribers: ['ADS-02', 'ADS-15'],
    defaultPayload: { multiplier: 2.8, category: 'Enterprise Components' },
    summary: 'Surge of 2.8x baseline demand. Triggers ADS-02 predictive surge analytics and ADS-15 safety buffer increase.',
  },
];

const AGENT_NAMES: Record<string, { name: string; role: string; icon: string }> = {
  'ADS-01': { name: 'Order Management Agent', role: 'Order Lifecycle & Validation', icon: '📋' },
  'ADS-02': { name: 'Demand Forecast Agent', role: 'Predictive Demand Modeling', icon: '📈' },
  'ADS-03': { name: 'Inventory Management Agent', role: 'Safety Stock & Deficit Monitoring', icon: '🏪' },
  'ADS-04': { name: 'Warehouse Operations Agent', role: 'Fulfillment & Staging', icon: '🏬' },
  'ADS-05': { name: 'Supplier & Sourcing Agent', role: 'Vendor Selection & Autonomous PO', icon: '🤝' },
  'ADS-06': { name: 'Transportation Agent', role: 'Corridor Routing & Freight Expediting', icon: '🚚' },
  'ADS-07': { name: 'Manufacturing Agent', role: 'Assembly & Emergency Remanufacturing', icon: '🏭' },
  'ADS-08': { name: 'Customer Service Agent', role: 'Client SLA Notification', icon: '💬' },
  'ADS-09': { name: 'Finance Agent', role: 'Budget & Margin Audit', icon: '💰' },
  'ADS-10': { name: 'Supply Chain Risk Agent', role: 'Vulnerability & Geopolitical Risk', icon: '⚠️' },
  'ADS-14': { name: 'Quality Assurance Agent', role: 'Batch Inspection & Quarantine', icon: '🔬' },
  'ADS-15': { name: 'Dynamic Planner Agent', role: 'Production & Buffer Replanning', icon: '🧭' },
};

export const LiveEventGraph: React.FC<LiveEventGraphProps> = ({
  initialEventId,
  onEventSelect,
}) => {
  const [selectedPresetIndex, setSelectedPresetIndex] = useState(0);
  const [currentEvent, setCurrentEvent] = useState<EventRecord | null>(null);
  const [recentEvents, setRecentEvents] = useState<EventRecord[]>([]);
  const [delaySeconds, setDelaySeconds] = useState(0.8);
  const [isExecuting, setIsExecuting] = useState(false);
  const [selectedAgentCode, setSelectedAgentCode] = useState<string>('');

  const isMountedRef = useRef(true);

  // Load delay config and recent events
  useEffect(() => {
    workflowApi.getConfig().then((res) => {
      if (res?.delay_seconds !== undefined) {
        setDelaySeconds(res.delay_seconds);
      }
    }).catch(() => {});

    if (initialEventId) {
      eventsApi.getTrace(initialEventId).then((tr) => {
        if (isMountedRef.current && tr) {
          setCurrentEvent(tr as any);
        }
      }).catch(() => {});
    }

    loadRecentEvents();
  }, [initialEventId]);

  const loadRecentEvents = async () => {
    try {
      const res = await eventsApi.list({ limit: 12 });
      if (isMountedRef.current && res.items) {
        setRecentEvents(res.items);
        if (res.items.length > 0 && !currentEvent) {
          setCurrentEvent(res.items[0]);
          if (res.items[0].subscribers && res.items[0].subscribers.length > 0) {
            setSelectedAgentCode(res.items[0].subscribers[0]);
          }
        }
      }
    } catch (e) {
      console.warn('Failed to load recent events:', e);
    }
  };

  const handleDelayChange = async (val: number) => {
    setDelaySeconds(val);
    try {
      await workflowApi.setConfig(val);
    } catch {}
  };

  // Trigger an event with live animated agent workflow
  const handleTriggerEvent = async () => {
    const preset = PRESET_EVENTS[selectedPresetIndex];
    setIsExecuting(true);
    setSelectedAgentCode(preset.subscribers[0] || 'ADS-01');

    try {
      const res = await eventsApi.inject({
        event_type: preset.type,
        source_agent: 'ControlTower-Visualizer',
        payload: preset.defaultPayload,
        delay_seconds: delaySeconds,
      });

      // Fetch the updated event with its full remediation trace
      const detail = await eventsApi.getTrace(res.event_id);
      if (isMountedRef.current) {
        setCurrentEvent(detail as any);
        if (onEventSelect) onEventSelect(res.event_id);
        loadRecentEvents();
      }
    } catch (err: any) {
      alert(`Event dispatch failed: ${err.message}`);
    } finally {
      if (isMountedRef.current) {
        setIsExecuting(false);
      }
    }
  };

  const currentPreset = PRESET_EVENTS[selectedPresetIndex];
  const steps: EventRemediationStep[] = currentEvent?.remediation_trace || [];
  const autonomousActions = currentEvent?.autonomous_actions || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Pacing & Event Preset Launcher */}
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

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="range"
              min="0"
              max="2.5"
              step="0.1"
              value={delaySeconds}
              onChange={(e) => handleDelayChange(parseFloat(e.target.value))}
              style={{ width: '90px', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--c-brand-accent)', fontWeight: 600 }}>
              {delaySeconds.toFixed(1)}s
            </span>
          </div>
        </div>

        {/* Load Past Event Select */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {recentEvents.length > 0 && (
            <select
              value={currentEvent?.event_id || ''}
              onChange={async (e) => {
                const evId = e.target.value;
                try {
                  const tr = await eventsApi.getTrace(evId);
                  setCurrentEvent(tr as any);
                  if (tr.subscribers && tr.subscribers.length > 0) {
                    setSelectedAgentCode(tr.subscribers[0]);
                  }
                  if (onEventSelect) onEventSelect(evId);
                } catch {}
              }}
              style={{
                fontSize: '12px',
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid var(--c-border)',
                background: 'var(--c-bg-subtle)',
                color: 'var(--c-text-primary)',
              }}
            >
              <option value="">Inspect Past Event...</option>
              {recentEvents.map((e) => (
                <option key={e.event_id} value={e.event_id}>
                  {e.event_type} · {new Date(e.timestamp).toLocaleTimeString()}
                </option>
              ))}
            </select>
          )}

          <button
            onClick={handleTriggerEvent}
            disabled={isExecuting}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 16px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 600,
              background: isExecuting ? 'var(--c-bg-subtle)' : 'linear-gradient(135deg, #ef4444, #dc2626)',
              color: isExecuting ? 'var(--c-text-muted)' : '#ffffff',
              border: 'none',
              cursor: isExecuting ? 'not-allowed' : 'pointer',
              boxShadow: isExecuting ? 'none' : '0 2px 8px rgba(239,68,68,0.3)',
            }}
          >
            {isExecuting ? (
              <>
                <Clock size={15} className="animate-spin" />
                <span>Triggering Agents...</span>
              </>
            ) : (
              <>
                <Zap size={15} fill="currentColor" />
                <span>Inject Disruption Event</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Preset Selector Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
        {PRESET_EVENTS.map((preset, idx) => {
          const isSelected = selectedPresetIndex === idx;
          return (
            <div
              key={preset.type}
              onClick={() => setSelectedPresetIndex(idx)}
              style={{
                background: isSelected ? 'rgba(37,99,235,0.06)' : 'var(--c-bg-card)',
                border: isSelected ? '2px solid var(--c-brand-accent)' : '1px solid var(--c-border)',
                borderRadius: '8px',
                padding: '12px 14px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span style={{ fontSize: '18px' }}>{preset.icon}</span>
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--c-text-primary)' }}>
                  {preset.name}
                </span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--c-text-muted)', marginBottom: '8px' }}>
                Event: <code style={{ fontFamily: 'var(--font-mono)' }}>{preset.type}</code>
              </div>
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                {preset.subscribers.map((sub) => (
                  <span
                    key={sub}
                    style={{
                      fontSize: '10px',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      background: 'rgba(37,99,235,0.1)',
                      color: 'var(--c-brand-accent)',
                      border: '1px solid rgba(37,99,235,0.2)',
                    }}
                  >
                    {sub}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Live Event Workflow Flow Diagram */}
      <div
        style={{
          background: 'var(--c-bg-card)',
          border: '1px solid var(--c-border)',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: 'var(--c-text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={18} color="var(--c-brand-accent)" />
              Event-Driven Multi-Agent Remediation Workflow
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--c-text-muted)' }}>
              Canonical Bus: Event Ingestion ➔ Subscriber Cognitive Remediation ➔ Concrete Digital Twin Action
            </span>
          </div>

          {currentEvent && (
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '3px 10px',
                borderRadius: '12px',
                background: currentEvent.status === 'remediated' ? 'rgba(16,185,129,0.1)' : 'rgba(37,99,235,0.1)',
                color: currentEvent.status === 'remediated' ? '#059669' : '#2563eb',
                border: `1px solid ${currentEvent.status === 'remediated' ? 'rgba(16,185,129,0.3)' : 'rgba(37,99,235,0.3)'}`,
                textTransform: 'uppercase',
              }}
            >
              Status: {currentEvent.status || 'Remediated'}
            </span>
          )}
        </div>

        {/* Visual Remediation Flow Stages */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1.2fr auto 1.5fr auto 1.5fr auto 1.2fr',
            gap: '12px',
            alignItems: 'center',
            background: 'var(--c-bg-subtle)',
            borderRadius: '10px',
            padding: '20px',
            border: '1px solid var(--c-border)',
          }}
        >
          {/* Stage 1: Trigger Event */}
          <div
            style={{
              background: 'var(--c-bg-card)',
              border: '2px solid #ef4444',
              borderRadius: '8px',
              padding: '14px',
              boxShadow: '0 2px 6px rgba(239,68,68,0.1)',
            }}
          >
            <div style={{ fontSize: '10px', fontWeight: 700, color: '#ef4444', textTransform: 'uppercase', marginBottom: '4px' }}>
              1. Event Ingested
            </div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--c-text-primary)' }}>
              {currentEvent?.event_type || currentPreset.type}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--c-text-muted)', marginTop: '4px' }}>
              Source: {currentEvent?.source_agent || 'Operator-Cockpit'}
            </div>
          </div>

          <div style={{ fontSize: '18px', color: 'var(--c-text-muted)', textAlign: 'center' }}>➔</div>

          {/* Stage 2: Subscriber Agent 1 */}
          {(() => {
            const subCode = (currentEvent?.subscribers?.[0]) || currentPreset.subscribers[0] || 'ADS-03';
            const meta = AGENT_NAMES[subCode] || { name: subCode, role: '', icon: '🤖' };
            const step = steps.find((s) => s.agent_code === subCode);
            const isSelected = selectedAgentCode === subCode;

            return (
              <div
                onClick={() => setSelectedAgentCode(subCode)}
                style={{
                  background: isSelected ? 'rgba(37,99,235,0.06)' : 'var(--c-bg-card)',
                  border: isSelected ? '2px solid var(--c-brand-accent)' : '1px solid var(--c-border)',
                  borderRadius: '8px',
                  padding: '14px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--c-brand-accent)', textTransform: 'uppercase' }}>
                    2. Agent Invocated
                  </span>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#059669', fontWeight: 600 }}>
                    {step?.duration_ms ? `${step.duration_ms}ms` : '✓'}
                  </span>
                </div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--c-text-primary)' }}>
                  {meta.icon} {subCode}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--c-text-muted)', marginTop: '2px' }}>
                  {meta.name}
                </div>
              </div>
            );
          })()}

          <div style={{ fontSize: '18px', color: 'var(--c-text-muted)', textAlign: 'center' }}>➔</div>

          {/* Stage 3: Subscriber Agent 2 */}
          {(() => {
            const subCode = (currentEvent?.subscribers?.[1]) || currentPreset.subscribers[1] || 'ADS-05';
            const meta = AGENT_NAMES[subCode] || { name: subCode, role: '', icon: '🤖' };
            const step = steps.find((s) => s.agent_code === subCode);
            const isSelected = selectedAgentCode === subCode;

            return (
              <div
                onClick={() => setSelectedAgentCode(subCode)}
                style={{
                  background: isSelected ? 'rgba(37,99,235,0.06)' : 'var(--c-bg-card)',
                  border: isSelected ? '2px solid var(--c-brand-accent)' : '1px solid var(--c-border)',
                  borderRadius: '8px',
                  padding: '14px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--c-brand-accent)', textTransform: 'uppercase' }}>
                    3. Remediation Loop
                  </span>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#059669', fontWeight: 600 }}>
                    {step?.duration_ms ? `${step.duration_ms}ms` : '✓'}
                  </span>
                </div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--c-text-primary)' }}>
                  {meta.icon} {subCode}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--c-text-muted)', marginTop: '2px' }}>
                  {meta.name}
                </div>
              </div>
            );
          })()}

          <div style={{ fontSize: '18px', color: 'var(--c-text-muted)', textAlign: 'center' }}>➔</div>

          {/* Stage 4: Closed-Loop Remediation / Downstream Event */}
          <div
            style={{
              background: 'var(--c-bg-card)',
              border: '2px solid #10b981',
              borderRadius: '8px',
              padding: '14px',
              boxShadow: '0 2px 6px rgba(16,185,129,0.1)',
            }}
          >
            <div style={{ fontSize: '10px', fontWeight: 700, color: '#059669', textTransform: 'uppercase', marginBottom: '4px' }}>
              4. Twin Remediated
            </div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--c-text-primary)' }}>
              Autonomous Action
            </div>
            <div style={{ fontSize: '11px', color: 'var(--c-text-muted)', marginTop: '4px' }}>
              State Synchronized
            </div>
          </div>
        </div>

        {/* Executive Remediation Summary Banner */}
        {currentEvent?.remediation_summary && (
          <div
            style={{
              marginTop: '18px',
              background: 'rgba(16,185,129,0.06)',
              border: '1px solid rgba(16,185,129,0.3)',
              borderRadius: '8px',
              padding: '12px 16px',
              fontSize: '12px',
              color: 'var(--c-text-primary)',
              lineHeight: 1.5,
            }}
          >
            <strong style={{ color: '#059669' }}>Autonomous Remediation Summary: </strong>
            {currentEvent.remediation_summary}
          </div>
        )}
      </div>

      {/* Autonomous Action Steps Breakdown */}
      {autonomousActions.length > 0 && (
        <div
          style={{
            background: 'var(--c-bg-card)',
            border: '1px solid var(--c-border)',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: 'var(--shadow-card)',
          }}
        >
          <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--c-text-primary)', margin: '0 0 14px' }}>
            Multi-Agent Autonomous Actions ({autonomousActions.length})
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {autonomousActions.map((act, i) => (
              <div
                key={i}
                style={{
                  background: 'var(--c-bg-subtle)',
                  border: '1px solid var(--c-border)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  display: 'flex',
                  gap: '12px',
                  alignItems: 'flex-start',
                }}
              >
                <div
                  style={{
                    padding: '4px 8px',
                    borderRadius: '6px',
                    background: 'rgba(37,99,235,0.1)',
                    color: 'var(--c-brand-accent)',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                  }}
                >
                  {act.agent}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--c-text-primary)' }}>
                    {act.action}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--c-text-secondary)', marginTop: '2px' }}>
                    {act.details}
                  </div>
                </div>
                <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--c-text-muted)' }}>
                  {act.timestamp ? new Date(act.timestamp).toLocaleTimeString() : '—'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
