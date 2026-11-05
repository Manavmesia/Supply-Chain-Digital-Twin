import React, { useEffect, useState, useCallback, useRef } from 'react';
import { shipmentsApi } from '../services/api';
import type { Shipment, ShipmentStats } from '../types';
import {
  Truck,
  Plane,
  Ship,
  Train,
  AlertTriangle,
  Clock,
  ArrowRight,
  Search,
  RefreshCw,
  Plus,
  Navigation,
  Zap,
} from 'lucide-react';

const MODE_ICONS: Record<string, React.ReactNode> = {
  road: <Truck className="w-4 h-4 text-emerald-400" />,
  air: <Plane className="w-4 h-4 text-sky-400" />,
  ocean: <Ship className="w-4 h-4 text-blue-400" />,
  rail: <Train className="w-4 h-4 text-purple-400" />,
};

const STATUS_BADGES: Record<string, { label: string; bg: string; text: string; border: string }> = {
  in_transit: { label: 'In Transit', bg: 'rgba(59, 130, 246, 0.1)', text: '#60a5fa', border: 'rgba(59, 130, 246, 0.3)' },
  delivered: { label: 'Delivered', bg: 'rgba(16, 185, 129, 0.1)', text: '#34d399', border: 'rgba(16, 185, 129, 0.3)' },
  delayed: { label: 'Delayed / Exception', bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: 'rgba(239, 68, 68, 0.4)' },
  pending: { label: 'Pending Dispatch', bg: 'rgba(245, 158, 11, 0.1)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' },
};

export const ShipmentsPage: React.FC = () => {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [stats, setStats] = useState<ShipmentStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modeFilter, setModeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [reroutingId, setReroutingId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showStatusModal, setShowStatusModal] = useState<Shipment | null>(null);

  // Form states
  const [newOrigin, setNewOrigin] = useState('Newark Distribution Center');
  const [newDestination, setNewDestination] = useState('Frankfurt Logistics Centre');
  const [newCarrier, setNewCarrier] = useState('Global Intermodal Logistics');
  const [newMode, setNewMode] = useState<'road' | 'air' | 'ocean' | 'rail'>('road');

  // Status modal form
  const [updateStatusVal, setUpdateStatusVal] = useState<'pending' | 'in_transit' | 'delivered' | 'delayed'>('in_transit');
  const [updateLocationVal, setUpdateLocationVal] = useState('');
  const [updateReasonVal, setUpdateReasonVal] = useState('');

  const isMountedRef = useRef(true);

  const loadData = useCallback(async (isSilent = false) => {
    try {
      const [listRes, statsRes] = await Promise.all([
        shipmentsApi.list({ limit: 100 }),
        shipmentsApi.getStats(),
      ]);
      if (isMountedRef.current) {
        setShipments(listRes.items || []);
        setStats(statsRes);
      }
    } catch (err) {
      console.error('Failed to load shipments:', err);
    } finally {
      if (isMountedRef.current && !isSilent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    loadData();
    const interval = setInterval(() => loadData(true), 12000);
    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
    };
  }, [loadData]);

  const handleRerouteAir = async (shipment: Shipment) => {
    setReroutingId(shipment.shipment_id);
    setActionMessage(null);
    try {
      await shipmentsApi.reroute(shipment.shipment_id, {
        new_freight_mode: 'air',
        new_carrier: 'FedEx Priority Air Cargo',
        reason: 'Autonomous ADS-06 bottleneck resolution — shifted from bottlenecked corridor to express air bridge.',
      });
      setActionMessage(`Shipment ${shipment.carrier_tracking_id} successfully rerouted to Express Air Cargo!`);
      await loadData(true);
    } catch (err: any) {
      setActionMessage(`Reroute failed: ${err.message || 'Unknown error'}`);
    } finally {
      setReroutingId(null);
    }
  };

  const handleCreateShipment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await shipmentsApi.create({
        origin: newOrigin,
        destination: newDestination,
        carrier: newCarrier,
        freight_mode: newMode,
      });
      setShowCreateModal(false);
      setActionMessage('New freight dispatch created successfully!');
      await loadData(true);
    } catch (err: any) {
      alert(`Creation failed: ${err.message}`);
    }
  };

  const handleUpdateStatusSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showStatusModal) return;
    try {
      await shipmentsApi.updateStatus(showStatusModal.shipment_id, {
        status: updateStatusVal,
        current_location: updateLocationVal || undefined,
        delay_reason: updateReasonVal || undefined,
      });
      setShowStatusModal(null);
      setActionMessage(`Shipment ${showStatusModal.carrier_tracking_id} waypoint updated.`);
      await loadData(true);
    } catch (err: any) {
      alert(`Update failed: ${err.message}`);
    }
  };

  const filtered = shipments.filter((s) => {
    if (modeFilter !== 'all' && s.freight_mode !== modeFilter) return false;
    if (statusFilter !== 'all' && s.status !== statusFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchTrack = s.carrier_tracking_id?.toLowerCase().includes(q);
      const matchCarrier = s.carrier?.toLowerCase().includes(q);
      const matchOrigin = s.origin?.toLowerCase().includes(q);
      const matchDest = s.destination?.toLowerCase().includes(q);
      const matchId = s.shipment_id?.toLowerCase().includes(q);
      return matchTrack || matchCarrier || matchOrigin || matchDest || matchId;
    }
    return true;
  });

  return (
    <div style={{ padding: '28px', maxWidth: '1440px', margin: '0 auto', color: '#f1f5f9' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>
              Logistics & Transportation (TMS)
            </h1>
            <span style={{ fontSize: '11px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', padding: '3px 8px', borderRadius: '4px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              Live Carrier Telemetry
            </span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0 0' }}>
            Multi-modal freight tracking, IoT waypoint monitoring, and autonomous disruption bypass (ADS-06).
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => loadData()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#cbd5e1',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              background: '#2563eb',
              border: 'none',
              borderRadius: '6px',
              color: '#ffffff',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <Plus className="w-4 h-4" />
            Dispatch Shipment
          </button>
        </div>
      </div>

      {actionMessage && (
        <div style={{ marginBottom: '20px', padding: '12px 16px', borderRadius: '8px', background: 'rgba(37, 99, 235, 0.15)', border: '1px solid rgba(37, 99, 235, 0.3)', color: '#93c5fd', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap className="w-4 h-4 text-sky-400" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>TOTAL SHIPMENTS</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>{stats?.total_shipments ?? shipments.length}</div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Across road, air, ocean & rail</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>IN TRANSIT</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#60a5fa' }}>{stats?.in_transit ?? 0}</div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Live active freight consignments</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>LOGISTICAL EXCEPTIONS</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: stats?.delayed ? '#f87171' : '#34d399' }}>
            {stats?.delayed ?? 0}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Corridor disruptions detected</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>ON-TIME PROJECTION (OTIF)</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#34d399' }}>
            {stats?.on_time_rate_pct ?? 96.5}%
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>SLA adherence across routes</div>
        </div>
      </div>

      {/* Filters and Search Bar */}
      <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 500 }}>Mode:</span>
          {['all', 'road', 'air', 'ocean'].map((m) => (
            <button
              key={m}
              onClick={() => setModeFilter(m)}
              style={{
                padding: '5px 10px',
                borderRadius: '5px',
                fontSize: '12px',
                border: '1px solid',
                borderColor: modeFilter === m ? '#3b82f6' : '#334155',
                background: modeFilter === m ? 'rgba(59, 130, 246, 0.2)' : '#1e293b',
                color: modeFilter === m ? '#93c5fd' : '#cbd5e1',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {m}
            </button>
          ))}
          <span style={{ margin: '0 8px', color: '#334155' }}>|</span>
          <span style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 500 }}>Status:</span>
          {['all', 'in_transit', 'delayed', 'delivered'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              style={{
                padding: '5px 10px',
                borderRadius: '5px',
                fontSize: '12px',
                border: '1px solid',
                borderColor: statusFilter === st ? '#3b82f6' : '#334155',
                background: statusFilter === st ? 'rgba(59, 130, 246, 0.2)' : '#1e293b',
                color: statusFilter === st ? '#93c5fd' : '#cbd5e1',
                cursor: 'pointer',
              }}
            >
              {st === 'all' ? 'All' : st.replace('_', ' ')}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#1e293b', borderRadius: '6px', padding: '6px 12px', border: '1px solid #334155' }}>
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search tracking, carrier, origin..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#f8fafc',
              fontSize: '12px',
              width: '240px',
            }}
          />
        </div>
      </div>

      {/* Shipments Table / Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {filtered.map((shipment) => {
          const badge = STATUS_BADGES[shipment.status] || STATUS_BADGES.in_transit;
          const isDelayed = shipment.status === 'delayed';

          return (
            <div
              key={shipment.shipment_id}
              style={{
                background: '#0f172a',
                border: isDelayed ? '1px solid rgba(239, 68, 68, 0.5)' : '1px solid #1e293b',
                borderRadius: '8px',
                padding: '16px 20px',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ padding: '8px', background: '#1e293b', borderRadius: '6px', border: '1px solid #334155' }}>
                    {MODE_ICONS[shipment.freight_mode] || <Truck className="w-4 h-4 text-emerald-400" />}
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '14px', color: '#f8fafc' }}>
                        {shipment.carrier_tracking_id}
                      </span>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: badge.bg,
                          color: badge.text,
                          border: `1px solid ${badge.border}`,
                        }}
                      >
                        {badge.label}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                      Carrier: <strong style={{ color: '#cbd5e1' }}>{shipment.carrier}</strong> &bull; Freight:{' '}
                      <span style={{ textTransform: 'uppercase', color: '#60a5fa' }}>{shipment.freight_mode}</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {isDelayed && (
                    <button
                      onClick={() => handleRerouteAir(shipment)}
                      disabled={reroutingId === shipment.shipment_id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                        border: 'none',
                        borderRadius: '5px',
                        padding: '6px 12px',
                        color: '#ffffff',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        boxShadow: '0 0 10px rgba(2, 132, 199, 0.4)',
                      }}
                    >
                      <Zap className="w-3.5 h-3.5 text-yellow-300" />
                      {reroutingId === shipment.shipment_id ? 'Rerouting...' : 'Autonomous Air Reroute'}
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setShowStatusModal(shipment);
                      setUpdateStatusVal(shipment.status as any);
                      setUpdateLocationVal(shipment.current_location || '');
                      setUpdateReasonVal(shipment.delay_reason || '');
                    }}
                    style={{
                      padding: '6px 12px',
                      background: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '5px',
                      color: '#cbd5e1',
                      fontSize: '12px',
                      cursor: 'pointer',
                    }}
                  >
                    Update Waypoint
                  </button>
                </div>
              </div>

              {/* Corridor Route Visualizer */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  background: '#131e33',
                  padding: '10px 14px',
                  borderRadius: '6px',
                  border: '1px solid #1e293b',
                  fontSize: '12px',
                  gap: '12px',
                }}
              >
                <div style={{ color: '#cbd5e1', fontWeight: 600 }}>{shipment.origin}</div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                <div style={{ color: '#cbd5e1', fontWeight: 600 }}>{shipment.destination}</div>
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8' }}>
                  <Navigation className="w-3.5 h-3.5 text-sky-400" />
                  <span>
                    Current Location: <strong style={{ color: '#f1f5f9' }}>{shipment.current_location || 'En Route'}</strong>
                  </span>
                  <span style={{ color: '#475569' }}>|</span>
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>ETA: {shipment.eta ? new Date(shipment.eta).toLocaleDateString() : 'Pending'}</span>
                </div>
              </div>

              {/* Disruption Alert Notice */}
              {isDelayed && shipment.delay_reason && (
                <div
                  style={{
                    marginTop: '10px',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    color: '#fca5a5',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                  <span>
                    <strong>Bottleneck Exception:</strong> {shipment.delay_reason}
                  </span>
                </div>
              )}
            </div>
          );
        })}

        {filtered.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: '48px', color: '#64748b', background: '#0f172a', borderRadius: '8px', border: '1px solid #1e293b' }}>
            No shipments match the current filters.
          </div>
        )}
      </div>

      {/* Dispatch Modal */}
      {showCreateModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', padding: '24px', width: '480px', maxWidth: '90%' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 16px 0', color: '#f8fafc' }}>Dispatch New Freight Consignment</h2>
            <form onSubmit={handleCreateShipment} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Origin Hub</label>
                <input
                  type="text"
                  value={newOrigin}
                  onChange={(e) => setNewOrigin(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Destination Facility</label>
                <input
                  type="text"
                  value={newDestination}
                  onChange={(e) => setNewDestination(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                  required
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Carrier</label>
                  <select
                    value={newCarrier}
                    onChange={(e) => setNewCarrier(e.target.value)}
                    style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                  >
                    <option value="Global Intermodal Logistics">Global Intermodal Logistics</option>
                    <option value="DHL Air Express">DHL Air Express</option>
                    <option value="Maersk Line Ocean Logistics">Maersk Line Ocean Logistics</option>
                    <option value="FedEx Freight Intermodal">FedEx Freight Intermodal</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Freight Mode</label>
                  <select
                    value={newMode}
                    onChange={(e) => setNewMode(e.target.value as any)}
                    style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                  >
                    <option value="road">Road</option>
                    <option value="air">Air</option>
                    <option value="ocean">Ocean</option>
                    <option value="rail">Rail</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{ padding: '8px 14px', background: 'transparent', border: '1px solid #334155', borderRadius: '5px', color: '#cbd5e1', cursor: 'pointer', fontSize: '13px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: '8px 18px', background: '#2563eb', border: 'none', borderRadius: '5px', color: '#ffffff', fontWeight: 600, cursor: 'pointer', fontSize: '13px' }}
                >
                  Dispatch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Update Waypoint Modal */}
      {showStatusModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', padding: '24px', width: '460px', maxWidth: '90%' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 8px 0', color: '#f8fafc' }}>
              Update Waypoint: {showStatusModal.carrier_tracking_id}
            </h2>
            <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 16px 0' }}>
              Record GPS checkpoint telemetry or report bottleneck exception.
            </p>
            <form onSubmit={handleUpdateStatusSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Status</label>
                <select
                  value={updateStatusVal}
                  onChange={(e) => setUpdateStatusVal(e.target.value as any)}
                  style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                >
                  <option value="in_transit">In Transit</option>
                  <option value="delivered">Delivered</option>
                  <option value="delayed">Delayed (Exception)</option>
                  <option value="pending">Pending</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Current Location / Checkpoint</label>
                <input
                  type="text"
                  value={updateLocationVal}
                  onChange={(e) => setUpdateLocationVal(e.target.value)}
                  placeholder="e.g. Chicago Intermodal Yard, Gate 4"
                  style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                />
              </div>
              {updateStatusVal === 'delayed' && (
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f87171', marginBottom: '4px' }}>Delay / Bottleneck Reason</label>
                  <input
                    type="text"
                    value={updateReasonVal}
                    onChange={(e) => setUpdateReasonVal(e.target.value)}
                    placeholder="e.g. Severe storm causing maritime port suspension"
                    style={{ width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid rgba(239,68,68,0.5)', borderRadius: '5px', color: '#f8fafc', fontSize: '13px' }}
                    required
                  />
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setShowStatusModal(null)}
                  style={{ padding: '8px 14px', background: 'transparent', border: '1px solid #334155', borderRadius: '5px', color: '#cbd5e1', cursor: 'pointer', fontSize: '13px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: '8px 18px', background: '#2563eb', border: 'none', borderRadius: '5px', color: '#ffffff', fontWeight: 600, cursor: 'pointer', fontSize: '13px' }}
                >
                  Save Waypoint
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
