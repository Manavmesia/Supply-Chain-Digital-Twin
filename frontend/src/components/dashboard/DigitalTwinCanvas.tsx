import React, { useState, useEffect, useRef } from 'react';
import {
  Globe,
  Maximize2,
  Minimize2,
  RotateCcw,
  X,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import type { TwinNetworkData, TwinNode } from '../../types';

interface DigitalTwinCanvasProps {
  data: TwinNetworkData | null;
  loading: boolean;
  onRefresh?: () => void;
}

export const DigitalTwinCanvas: React.FC<DigitalTwinCanvasProps> = ({
  data,
  loading,
  onRefresh,
}) => {
  const [selectedNode, setSelectedNode] = useState<TwinNode | null>(null);
  const [filterMode, setFilterMode] = useState<'all' | 'air' | 'sea' | 'road' | 'critical'>('all');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Default to selecting Newark Distribution Center if none selected
  useEffect(() => {
    if (data?.nodes && !selectedNode) {
      const defaultNode = data.nodes.find((n) => n.id.includes('10000000-0000-0000-0000-000000000001')) || data.nodes[0];
      setSelectedNode(defaultNode);
    }
  }, [data, selectedNode]);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  const NODE_COLORS: Record<string, { bg: string; border: string; glow: string; label: string }> = {
    supplier:   { bg: '#ffffff', border: '#2563eb', glow: 'rgba(37,99,235,0.2)', label: 'SUP' },
    plant:      { bg: '#ffffff', border: '#475569', glow: 'rgba(71,85,105,0.2)', label: 'MFG' },
    warehouse:  { bg: '#ffffff', border: '#1d4ed8', glow: 'rgba(29,78,216,0.2)', label: 'WMS' },
    market:     { bg: '#ffffff', border: '#059669', glow: 'rgba(5,150,105,0.2)', label: 'MKT' },
  };

  const LANE_STYLES: Record<string, { stroke: string; strokeDash?: string; width: number }> = {
    air:  { stroke: '#3b82f6', strokeDash: '6,4', width: 1.8 },
    sea:  { stroke: '#1d4ed8', strokeDash: '3,3', width: 2.0 },
    road: { stroke: '#64748b', width: 1.5 },
  };

  const filteredLanes = (data?.lanes || []).filter((l) => {
    if (filterMode === 'all') return true;
    if (filterMode === 'critical') return l.risk_score > 10;
    return l.mode === filterMode;
  });

  const nodeMap = new Map<string, TwinNode>();
  (data?.nodes || []).forEach((n) => nodeMap.set(n.id, n));

  return (
    <div
      ref={containerRef}
      className="card"
      style={{
        position: 'relative',
        padding: 0,
        overflow: 'hidden',
        background: '#ffffff',
        border: '1px solid var(--c-border)',
        boxShadow: 'var(--shadow-card)',
        borderRadius: '8px',
        minHeight: '540px',
      }}
    >
      {/* Canvas Header / Controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '1rem 1.5rem',
          borderBottom: '1px solid var(--c-border)',
          background: '#ffffff',
          zIndex: 20,
          position: 'relative',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '8px',
              background: '#eff6ff',
              border: '1px solid #bfdbfe',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Globe size={18} className="text-blue-600" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--c-text-primary)', letterSpacing: '-0.01em' }}>
                Spatial Digital Twin Topology
              </h3>
              <span
                style={{
                  fontSize: '0.65rem',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  background: 'rgba(16,185,129,0.1)',
                  color: '#059669',
                  border: '1px solid rgba(16,185,129,0.25)',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: loading ? '#f59e0b' : '#059669', display: 'inline-block' }} />
                {loading ? 'SYNCING...' : 'REAL-TIME TELEMETRY'}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--c-text-muted)' }}>
              Multi-echelon node network with live in-transit freight corridors & inventory buffers
            </p>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div
            style={{
              display: 'flex',
              background: '#f1f5f9',
              borderRadius: '8px',
              padding: '2px',
              border: '1px solid #e2e8f0',
            }}
          >
            {(['all', 'air', 'sea', 'road', 'critical'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setFilterMode(mode)}
                style={{
                  padding: '4px 10px',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  background: filterMode === mode ? '#ffffff' : 'transparent',
                  color: filterMode === mode ? '#0f172a' : '#64748b',
                  boxShadow: filterMode === mode ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                  transition: 'all 0.15s ease',
                  textTransform: 'capitalize',
                }}
              >
                {mode === 'all' ? 'All Lanes' : mode === 'critical' ? 'High Risk' : mode}
              </button>
            ))}
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              className="btn btn-ghost btn-sm"
              title="Refresh twin telemetry"
              style={{ padding: '6px 10px', height: '30px' }}
            >
              <RotateCcw size={13} />
            </button>
          )}

          <button
            onClick={toggleFullscreen}
            className="btn btn-ghost btn-sm"
            title="Toggle fullscreen view"
            style={{ padding: '6px 10px', height: '30px' }}
          >
            {isFullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div style={{ position: 'relative', width: '100%', height: '480px', userSelect: 'none', background: '#f8fafc' }}>
        {/* Abstract World Grid Background */}
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            opacity: 0.5,
          }}
        >
          <defs>
            <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" strokeWidth="0.8" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#gridPattern)" />
        </svg>

        {/* Global SVG Connecting Lanes & Animated Shipments */}
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
          }}
        >
          <defs>
            {/* Glow Filter for Active Lanes */}
            <filter id="laneGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Render Transit Corridors */}
          {filteredLanes.map((lane) => {
            const from = nodeMap.get(lane.from_node);
            const to = nodeMap.get(lane.to_node);
            if (!from || !to) return null;

            const x1 = `${from.coords.x}%`;
            const y1 = `${from.coords.y}%`;
            const x2 = `${to.coords.x}%`;
            const y2 = `${to.coords.y}%`;

            const style = LANE_STYLES[lane.mode] || LANE_STYLES.road;

            return (
              <g key={lane.id}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={style.stroke}
                  strokeWidth={style.width}
                  strokeDasharray={style.strokeDash}
                  opacity={lane.status === 'delayed' ? 0.9 : 0.6}
                  filter="url(#laneGlow)"
                />
              </g>
            );
          })}

          {/* Render Active Shipments along Lanes */}
          {(data?.active_shipments || []).map((shipment) => {
            const from = nodeMap.get(shipment.from_node);
            const to = nodeMap.get(shipment.to_node);
            if (!from || !to) return null;

            // Interpolate position along the vector
            const pct = (shipment.progress_pct || 50) / 100;
            const curX = from.coords.x + (to.coords.x - from.coords.x) * pct;
            const curY = from.coords.y + (to.coords.y - from.coords.y) * pct;

            const modeColor = shipment.mode === 'air' ? '#38bdf8' : shipment.mode === 'sea' ? '#3b82f6' : '#10b981';

            return (
              <g key={shipment.id} style={{ pointerEvents: 'auto', cursor: 'pointer' }}>
                <circle
                  cx={`${curX}%`}
                  cy={`${curY}%`}
                  r={8}
                  fill={modeColor}
                  opacity={0.3}
                  className="animate-ping"
                />
                <circle
                  cx={`${curX}%`}
                  cy={`${curY}%`}
                  r={5}
                  fill={modeColor}
                  stroke="#ffffff"
                  strokeWidth={1.5}
                  style={{ filter: 'drop-shadow(0 0 6px #ffffff)' }}
                />
                <title>{`${shipment.id} (${shipment.carrier}) • ${shipment.payload_desc}`}</title>
              </g>
            );
          })}
        </svg>

        {/* Nodes Layer */}
        {(data?.nodes || []).map((node) => {
          const cfg = NODE_COLORS[node.type] || NODE_COLORS.warehouse;
          const isSelected = selectedNode?.id === node.id;
          const isWarning = node.status === 'warning' || (node.low_stock_count ?? 0) > 0;

          return (
            <div
              key={node.id}
              onClick={() => setSelectedNode(node)}
              style={{
                position: 'absolute',
                left: `${node.coords.x}%`,
                top: `${node.coords.y}%`,
                transform: 'translate(-50%, -50%)',
                cursor: 'pointer',
                zIndex: isSelected ? 15 : 10,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                transition: 'transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translate(-50%, -50%) scale(1.15)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translate(-50%, -50%) scale(1)';
              }}
            >
              {/* Node Badge */}
              <div
                style={{
                  width: isSelected ? 34 : 28,
                  height: isSelected ? 34 : 28,
                  borderRadius: '6px',
                  background: '#ffffff',
                  border: `1.5px solid ${isSelected ? '#2563eb' : cfg.border}`,
                  boxShadow: isSelected ? '0 0 10px rgba(37, 99, 235, 0.3)' : '0 1px 3px rgba(0,0,0,0.06)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '9px',
                  fontWeight: 700,
                  fontFamily: 'monospace',
                  color: isSelected ? '#2563eb' : '#334155',
                  position: 'relative',
                }}
              >
                {cfg.label}

                {/* Status Dot */}
                {isWarning && (
                  <span
                    style={{
                      position: 'absolute',
                      top: -2,
                      right: -2,
                      width: 9,
                      height: 9,
                      borderRadius: '50%',
                      background: '#d97706',
                      border: '2px solid #ffffff',
                      boxShadow: '0 0 6px rgba(217,119,6,0.6)',
                    }}
                  />
                )}
              </div>

              {/* Node Title Label */}
              <div
                style={{
                  marginTop: 6,
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: isSelected ? '#eff6ff' : '#ffffff',
                  border: isSelected ? '1px solid #93c5fd' : '1px solid #e2e8f0',
                  color: isSelected ? '#1d4ed8' : '#0f172a',
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                }}
              >
                {node.name.replace(/ (Distribution Center|Logistics Centre|Fulfilment Hub|MegaHub|Plant|Market|Advanced Circuits|Systems GmbH|Inc\.|Ltd\.)/g, '')}
              </div>
            </div>
          );
        })}

        {/* Selected Node Telemetry Inspector Drawer */}
        {selectedNode && (
          <div
            style={{
              position: 'absolute',
              right: 16,
              bottom: 16,
              width: '320px',
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.08)',
              borderRadius: '10px',
              padding: '1.25rem',
              zIndex: 25,
              animation: 'fadeIn 0.2s ease-out',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '10px', fontWeight: 700, fontFamily: 'monospace', background: '#f1f5f9', border: '1px solid #e2e8f0', padding: '2px 5px', borderRadius: '3px', color: '#334155' }}>
                  {NODE_COLORS[selectedNode.type]?.label ?? 'NODE'}
                </span>
                <div>
                  <h4 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>
                    {selectedNode.name}
                  </h4>
                  <span style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    {selectedNode.type} • {selectedNode.location}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#64748b',
                  cursor: 'pointer',
                  padding: 2,
                }}
              >
                <X size={15} />
              </button>
            </div>

            {/* Warehouse Telemetry */}
            {selectedNode.type === 'warehouse' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                  <div style={{ background: '#f8fafc', padding: '0.5rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.65rem', color: '#64748b' }}>Available Stock</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#059669' }}>
                      {selectedNode.available_units?.toLocaleString() ?? '—'}
                    </div>
                  </div>
                  <div style={{ background: '#f8fafc', padding: '0.5rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.65rem', color: '#64748b' }}>Reserved Stock</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#2563eb' }}>
                      {selectedNode.reserved_units?.toLocaleString() ?? '0'}
                    </div>
                  </div>
                </div>

                <div style={{ background: '#f8fafc', padding: '0.5rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#64748b', marginBottom: '4px' }}>
                    <span>Capacity Utilization</span>
                    <span style={{ fontWeight: 600, color: '#0f172a' }}>
                      {Math.round(((selectedNode.available_units || 0) / (selectedNode.capacity || 50000)) * 100)}%
                    </span>
                  </div>
                  <div style={{ height: 4, width: '100%', background: '#e2e8f0', borderRadius: 2, overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(Math.round(((selectedNode.available_units || 0) / (selectedNode.capacity || 50000)) * 100), 100)}%`,
                        background: '#2563eb',
                      }}
                    />
                  </div>
                </div>

                {(selectedNode.low_stock_count ?? 0) > 0 ? (
                  <div style={{ fontSize: '0.72rem', color: '#f59e0b', background: 'rgba(245,158,11,0.1)', padding: '6px 8px', borderRadius: '6px', border: '1px solid rgba(245,158,11,0.3)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertTriangle size={13} />
                    <span>{selectedNode.low_stock_count} SKU locations below safety stock buffer</span>
                  </div>
                ) : (
                  <div style={{ fontSize: '0.72rem', color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '6px 8px', borderRadius: '6px', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CheckCircle2 size={13} />
                    <span>Safety stock buffers verified optimal</span>
                  </div>
                )}

                <a
                  href="/inventory"
                  className="btn btn-secondary btn-sm"
                  style={{ width: '100%', textAlign: 'center', marginTop: '4px', textDecoration: 'none', fontSize: '0.75rem' }}
                >
                  Inspect Warehouse Inventory →
                </a>
              </div>
            )}

            {/* Supplier Telemetry */}
            {selectedNode.type === 'supplier' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>Reliability Rating</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#10b981' }}>
                      {selectedNode.reliability}%
                    </div>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>Lead Time</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                      {selectedNode.lead_time_days} Days
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: '0.72rem', color: '#94a3b8', background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '6px' }}>
                  <span style={{ color: '#f8fafc', fontWeight: 600 }}>Catalog Lines:</span> {selectedNode.primary_products}
                </div>

                <div style={{ fontSize: '0.72rem', color: '#38bdf8', background: 'rgba(56,189,248,0.08)', padding: '6px 8px', borderRadius: '6px', border: '1px solid rgba(56,189,248,0.25)' }}>
                  Active Autonomous POs: {selectedNode.active_orders ?? 0} in transit
                </div>
              </div>
            )}

            {/* Plant & Market Telemetry */}
            {(selectedNode.type === 'plant' || selectedNode.type === 'market') && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.75rem', color: '#cbd5e1' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: '#94a3b8' }}>Operational Status</span>
                  <span style={{ color: '#10b981', fontWeight: 600 }}>Active / Optimal</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: '#94a3b8' }}>Tier Class</span>
                  <span>{selectedNode.tier}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <span style={{ color: '#94a3b8' }}>SLA Compliance</span>
                  <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                    {selectedNode.sla_performance ? `${selectedNode.sla_performance}%` : '99.1%'}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Summary Footer Bar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1rem',
          padding: '0.75rem 1.5rem',
          background: 'rgba(15, 23, 42, 0.95)',
          borderTop: '1px solid rgba(255,255,255,0.08)',
          fontSize: '0.75rem',
        }}
      >
        <div>
          <span style={{ color: '#94a3b8' }}>Network Health: </span>
          <span style={{ color: '#10b981', fontWeight: 700 }}>
            {data?.summary.network_health_score ?? 96.4}%
          </span>
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>Active Freight Lanes: </span>
          <span style={{ color: '#38bdf8', fontWeight: 700 }}>
            {data?.summary.total_lanes ?? 10} Corridors
          </span>
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>In-Transit Cargo: </span>
          <span style={{ color: '#f59e0b', fontWeight: 700 }}>
            {data?.summary.active_shipments_in_flight ?? 3} Active
          </span>
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>OTIF SLA Projection: </span>
          <span style={{ color: '#10b981', fontWeight: 700 }}>
            {data?.summary.otif_delivery_projection ?? 98.1}%
          </span>
        </div>
      </div>
    </div>
  );
};
