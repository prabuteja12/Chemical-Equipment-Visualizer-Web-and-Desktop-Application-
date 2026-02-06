import React from "react";

export default function RecentUploads({ datasets, onSelect, onDownload }) {
  return (
    <div className="card recent-card">
      <h2>Recent Uploads</h2>
      <div className="recent-list">
        {datasets.length === 0 && <p className="muted">No uploads yet.</p>}
        {datasets.map((ds) => (
          <div
            key={ds.id}
            className="recent-item"
            role="button"
            tabIndex={0}
            onClick={() => onSelect(ds.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(ds.id);
              }
            }}
          >
            <div className="recent-left">
              <strong>{ds.name}</strong>
              <span>{new Date(ds.created_at).toLocaleString()}</span>
              <span className="recent-summary">
                Total: {ds.row_count} | Avg Flow: {Number(ds.avg_flowrate || 0).toFixed(2)} | Avg Pressure: {" "}
                {Number(ds.avg_pressure || 0).toFixed(2)} | Avg Temp: {Number(ds.avg_temperature || 0).toFixed(2)} | Types: {" "}
                {Object.keys(ds.type_distribution || {}).length || "--"}
              </span>
            </div>
            <div className="recent-meta">
              <button
                className="outline small"
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDownload(ds.id);
                }}
              >
                Download PDF
              </button>
              <span className="view-details">View details</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
