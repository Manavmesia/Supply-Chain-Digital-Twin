import React, { useEffect, useState } from 'react';
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

  useEffect(() => {
    reportsApi.list({ limit: 50 }).then((res) => {
      setReports(res.items);
      setTotal(res.total);
      setLoading(false);
    });
  }, []);

  return (
    <div className="page-content animate-fade-in">
      <div className="page-header">
        <h1><span className="gradient-text">Reports & Analytics</span></h1>
        <p>ADS-18 Reporting Agent generates executive reports after every workflow</p>
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
