import React, { useEffect, useState, useCallback, useRef } from 'react';
import { reportsApi } from '../services/api';
import type { Report } from '../types';
import { formatReportId, formatWorkflowId } from '../utils/formatters';

const STATUS_CONFIG: Record<string, { color: string; badge: string }> = {
  generated:   { color: '#10b981', badge: 'badge-success' },
  pending:     { color: '#f59e0b', badge: 'badge-warning' },
  failed:      { color: '#ef4444', badge: 'badge-danger' },
  archived:    { color: '#64748b', badge: 'badge-muted' },
};

export const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [selected, setSelected] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const isMountedRef = useRef(true);

  const fetchReports = useCallback(async (isSilent = false) => {
    try {
      const res = await reportsApi.list({ limit: 50 });
      if (isMountedRef.current) {
        setReports(res.items);
        setTotal(res.total);
        setLastUpdated(new Date());
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
        setLastUpdated(new Date());
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
    <div className="page-content animate-fade-in">
      <div className="page-header">
        <h1><span className="gradient-text">Reports & Analytics</span></h1>
        <p>ADS-18 Reporting Agent generates executive reports after every workflow</p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => { setLoading(true); fetchReports(false); }}
            disabled={loading}
          >
            ↻ Refresh Reports
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: '#10b981' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 6px #10b981' }} />
            Live Auto-Sync (4s) • Updated {lastUpdated.toLocaleTimeString()}
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Report list */}
        <div className="card">
          <div className="section-header">
            <h3 className="section-title">📄 Report History</h3>
            <span className="badge badge-info">{total} total</span>
          </div>

          {loading ? (
            <div className="loading-overlay">
              <span className="loading-spinner" style={{ width: 28, height: 28 }} />
              <p>Loading reports…</p>
            </div>
          ) : reports.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">📄</span>
              <p>No reports generated yet</p>
              <p style={{ fontSize: '0.8rem', color: '#475569' }}>
                Complete a workflow to generate your first report
              </p>
            </div>
          ) : (
            <div className="report-list">
              {reports.map((r) => {
                const sc = STATUS_CONFIG[r.status] ?? STATUS_CONFIG.pending;
                const isSelected = selected?.report_id === r.report_id;
                return (
                  <div
                    key={r.report_id}
                    className={`report-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelected(isSelected ? null : r)}
                    style={{
                      borderLeft: isSelected ? `3px solid ${sc.color}` : '3px solid transparent',
                      background: isSelected ? `${sc.color}0a` : 'transparent',
                    }}
                  >
                    <div className="flex justify-between items-center">
                      <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>{r.title}</span>
                      <span className={`badge ${sc.badge}`}>{r.status}</span>
                    </div>
                    <div className="flex gap-3 mt-2" style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      <span>🔖 {r.report_type}</span>
                      {r.workflow_id && <span>⚡ {formatWorkflowId(r.workflow_id)}</span>}
                      {r.created_at && (
                        <span>🕐 {new Date(r.created_at).toLocaleString()}</span>
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
          <h3 className="section-title mb-4">📊 Report Detail</h3>
          {!selected ? (
            <div className="empty-state">
              <span className="empty-icon">👈</span>
              <p>Select a report to view details</p>
            </div>
          ) : (
            <div className="animate-fade-in">
              <div className="mb-4">
                <h4 style={{ marginBottom: '0.5rem' }}>{selected.title}</h4>
                <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
                  <span className="tag">{selected.report_type}</span>
                  {selected.generated_by_agent && (
                    <span className="tag" style={{ color: '#a78bfa' }}>
                      {selected.generated_by_agent}
                    </span>
                  )}
                  <span className={`badge ${STATUS_CONFIG[selected.status]?.badge ?? 'badge-muted'}`}>
                    {selected.status}
                  </span>
                </div>
              </div>

              <div className="divider" />

              <div className="form-group">
                <p className="form-label">Report Code</p>
                <code className="tag" style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }} title={selected.report_id}>
                  {formatReportId(selected.report_id)}
                </code>
              </div>

              {selected.workflow_id && (
                <div className="form-group mt-4">
                  <p className="form-label">Associated Workflow</p>
                  <code className="tag" style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#3b82f6' }} title={selected.workflow_id}>
                    {formatWorkflowId(selected.workflow_id)}
                  </code>
                </div>
              )}

              {selected.created_at && (
                <div className="form-group mt-4">
                  <p className="form-label">Generated At</p>
                  <p style={{ fontSize: '0.875rem' }}>
                    {new Date(selected.created_at).toLocaleString('en-US', {
                      dateStyle: 'full', timeStyle: 'short',
                    })}
                  </p>
                </div>
              )}

              {selected.payload_summary && (
                <div className="form-group mt-4">
                  <p className="form-label">Payload Summary</p>
                  <div className="code-block" style={{ maxHeight: '300px', overflow: 'auto' }}>
                    {JSON.stringify(selected.payload_summary, null, 2)}
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
