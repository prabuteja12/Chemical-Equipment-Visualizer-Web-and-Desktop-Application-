import React from "react";

export default function InsightPanel({ dataset }) {
  const summary = dataset?.summary || dataset || {};
  const insights = summary.insights || {};

  return (
    <div className="card insights-card">
      <h3>Process Intelligence</h3>
      <div className="insight-grid">
        <div>
          <span>Health Score</span>
          <strong>{insights.health_score ?? "--"}</strong>
        </div>
        <div>
          <span>Stability Index</span>
          <strong>{insights.stability_index ?? "--"}</strong>
        </div>
        <div>
          <span>Efficiency Index</span>
          <strong>{insights.efficiency_index ?? "--"}</strong>
        </div>
        <div>
          <span>Utilization Band</span>
          <strong>{insights.utilization_band ?? "--"}</strong>
        </div>
        <div>
          <span>Anomaly Rate</span>
          <strong>{insights.anomaly_rate ?? "--"}%</strong>
        </div>
        <div>
          <span>Missing Ratio</span>
          <strong>{insights.missing_ratio ?? "--"}%</strong>
        </div>
      </div>
      <div className="alerts">
        <h4>Alerts</h4>
        {(insights.alerts || []).map((alert, idx) => (
          <div key={idx} className="alert-item">
            {alert}
          </div>
        ))}
      </div>
    </div>
  );
}
