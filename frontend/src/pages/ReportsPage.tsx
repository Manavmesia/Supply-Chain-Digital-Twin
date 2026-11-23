import React, { useEffect, useState, useCallback, useRef } from 'react';
import { FileText, Tag, Zap, Clock, RotateCcw, FileSearch } from 'lucide-react';
import { reportsApi } from '../services/api';
import type { Report } from '../types';
import { formatReportId, formatWorkflowId } from '../utils/formatters';
import { BusinessDataView } from '../components/common/BusinessDataView';

const STATUS_CONFIG: Record<string, { color: string; badge: string }> = {
  ready:       { color: '#10b981', badge: 'badge-success' },
  generated:   { color: '#10b981', badge: 'badge-success' },
  generating:  { color: '#3b82f6', badge: 'badge-info' },
  pending:     { color: '#f59e0b', badge: 'badge-warning' },
  failed:      { color: '#ef4444', badge: 'badge-danger' },
  archived:    { color: '#64748b', badge: 'badge-muted' },
};

export const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [selected, setSelected] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const isMountedRef = useRef(true);

  const fetchReports = useCallback(async (isSilent = false) => {
    try {
      const res = await reportsApi.list({ limit: 50 });
      if (isMountedRef.current) {
        setReports(res.items);
        setTotal(res.total);
        setSelected((prev) => {
          if (!prev) return null;
          const match = res.items.find((item) => item.report_id === prev.report_id);
          return match || prev;
        });
      }
    } catch (err) {
      console.error('Reports load error:', err);
    } finally {
      if (isMountedRef.current && !isSilent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    isMountedRef.current = true;

    reportsApi.list({ limit: 50 }).then((res) => {
      if (!ignore && isMountedRef.current) {
        setReports(res.items);
        setTotal(res.total);
        setSelected((prev) => {
          if (!prev) return null;
          const match = res.items.find((item) => item.report_id === prev.report_id);
          return match || prev;
        });
        setLoading(false);
      }
    }).catch((err) => {
      console.error('Reports load error:', err);
      if (!ignore && isMountedRef.current) setLoading(false);
    });

    // Auto-sync reports every 4 seconds
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchReports(true);
      }
    }, 4000);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        fetchReports(true);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      ignore = true;
      isMountedRef.current = false;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [fetchReports]);

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Reports & Analytics
          </h1>
          <p className="page-subtitle">
            Executive operational reviews, sustainability audits, and supplier resilience scorecards.
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={() => { setLoading(true); fetchReports(false); }}
            disabled={loading}
            className="btn-secondary"
          >
            <RotateCcw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid-2">
        {/* Report list */}
        <div className="card">
          <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
              <FileText size={16} className="text-slate-400" />
              <span>Report History</span>
            </h3>
            <span style={{ fontSize: '12px', color: '#1d4ed8', background: '#eff6ff', padding: '3px 10px', borderRadius: '9999px', fontWeight: 600, border: '1px solid #bfdbfe' }}>
              {total} total
            </span>
          </div>

          {loading ? (
            <div className="loading-overlay">
              <span className="loading-spinner" style={{ width: 28, height: 28 }} />
              <p>Loading reports…</p>
            </div>
          ) : reports.length === 0 ? (
            <div className="empty-state">
              <FileText size={32} className="text-slate-600 mb-2" />
              <p>No reports generated yet</p>
              <p style={{ fontSize: '0.8rem', color: '#475569' }}>
                Process transactions to generate operational reports
              </p>
            </div>
          ) : (
            <div className="report-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {reports.map((r) => {
                const sc = STATUS_CONFIG[r.status] ?? STATUS_CONFIG.pending;
                const isSelected = selected?.report_id === r.report_id;
                return (
                  <div
                    key={r.report_id}
                    className={`report-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelected(isSelected ? null : r)}
                    style={{
                      borderLeft: isSelected ? `4px solid ${sc.color}` : '4px solid var(--c-border)',
                      background: isSelected ? 'var(--c-brand-subtle)' : 'var(--c-bg-subtle)',
                      borderRadius: 'var(--radius-md)',
                      padding: 'var(--space-3) var(--space-4)',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      borderTop: '1px solid var(--c-border)',
                      borderRight: '1px solid var(--c-border)',
                      borderBottom: '1px solid var(--c-border)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: 'var(--text-base)', color: 'var(--c-text-primary)' }}>{r.title}</span>
                      <span
                        style={{
                          fontSize: 'var(--text-xs)',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: 'var(--radius-full)',
                          background: `${sc.color}18`,
                          color: sc.color,
                          border: `1px solid ${sc.color}44`,
                          textTransform: 'capitalize',
                        }}
                      >
                        {r.status}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '12px', marginTop: '6px', fontSize: 'var(--text-xs)', color: 'var(--c-text-muted)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Tag size={12} /> {r.report_type}</span>
                      {r.workflow_id && <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontFamily: 'var(--font-mono)' }}><Zap size={12} /> {formatWorkflowId(r.workflow_id)}</span>}
                      {r.created_at && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Clock size={12} /> {new Date(r.created_at).toLocaleString()}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Report detail */}
        <div className="card">
          <h3 style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--c-text-primary)', letterSpacing: 'var(--track-snug)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <FileSearch size={16} className="text-slate-400" />
            <span>Report Details</span>
          </h3>
          {!selected ? (
            <div className="empty-state">
              <FileSearch size={32} className="text-slate-600 mb-2" />
              <p>Select a report to view details</p>
            </div>
          ) : (
            <div className="animate-fade-in">
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: 700, color: '#0f172a' }}>{selected.title}</h4>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '9999px', background: '#f1f5f9', color: '#475569', fontWeight: 500 }}>{selected.report_type}</span>
                  {selected.generated_by_agent && (
                    <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '9999px', background: '#eff6ff', color: '#2563eb', fontWeight: 600 }}>
                      {selected.generated_by_agent}
                    </span>
                  )}
                  <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '9999px', background: '#ecfdf5', color: '#059669', fontWeight: 600 }}>
                    {selected.status}
                  </span>
                </div>
              </div>

              <div style={{ height: '1px', background: '#e2e8f0', margin: '16px 0' }} />

              <div style={{ marginBottom: '12px' }}>
                <p style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginBottom: '4px' }}>Report Code</p>
                <code style={{ fontSize: '12px', fontFamily: 'monospace', padding: '2px 6px', background: '#f8fafc', borderRadius: '4px', border: '1px solid #e2e8f0', color: '#0f172a' }}>
                  {formatReportId(selected.report_id)}
                </code>
              </div>

              {selected.workflow_id && (
                <div style={{ marginBottom: '12px' }}>
                  <p style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginBottom: '4px' }}>Audit Ref</p>
                  <code style={{ fontSize: '12px', fontFamily: 'monospace', color: '#2563eb', padding: '2px 6px', background: '#eff6ff', borderRadius: '4px', border: '1px solid #bfdbfe' }}>
                    {formatWorkflowId(selected.workflow_id)}
                  </code>
                </div>
              )}

              {selected.created_at && (
                <div style={{ marginBottom: '12px' }}>
                  <p style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginBottom: '4px' }}>Generated At</p>
                  <p style={{ fontSize: '13px', color: '#334155', margin: 0 }}>
                    {new Date(selected.created_at).toLocaleString('en-US', {
                      dateStyle: 'full', timeStyle: 'short',
                    })}
                  </p>
                </div>
              )}

              {selected.payload_summary && (
                <div style={{ marginTop: '16px' }}>
                  <p style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginBottom: '8px' }}>Key Metrics</p>
                  <div style={{ marginTop: '6px' }}>
                    <BusinessDataView data={selected.payload_summary} layout="grid" />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
