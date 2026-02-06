import React from "react";

export default function SummaryCards({ dataset }) {
  const summary = dataset?.summary || dataset || {};
  const typeCount = Object.keys(summary.type_distribution || {}).length;

  return (
    <div className="summary-grid">
      <div className="summary-card">
        <span>Total Records</span>
        <strong>{summary.row_count ?? 0}</strong>
      </div>
      <div className="summary-card">
        <span>Avg Flowrate</span>
        <strong>{Number(summary.avg_flowrate || 0).toFixed(2)}</strong>
      </div>
      <div className="summary-card">
        <span>Avg Pressure</span>
        <strong>{Number(summary.avg_pressure || 0).toFixed(2)}</strong>
      </div>
      <div className="summary-card">
        <span>Avg Temperature</span>
        <strong>{Number(summary.avg_temperature || 0).toFixed(2)}</strong>
      </div>
      <div className="summary-card">
        <span>Equipment Types</span>
        <strong>{typeCount}</strong>
      </div>
    </div>
  );
}
