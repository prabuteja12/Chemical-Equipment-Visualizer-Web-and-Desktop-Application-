import React from "react";

export default function OperationalBrief({ dataset }) {
  const summary = dataset?.summary || dataset || {};
  const insights = summary.insights || {};
  const typeDist = summary.type_distribution || {};
  const topType = Object.entries(typeDist).sort((a, b) => b[1] - a[1])[0];
  return (
    <div className="brief-card">
      <h3>Operational Brief</h3>
      <p>
        The plant is running with a health score of{" "}
        <strong>{insights.health_score ?? "--"}</strong> and a{" "}
        <strong>{insights.utilization_band ?? "--"}</strong> utilization band.
        Average flowrate is{" "}
        <strong>{Number(summary.avg_flowrate || 0).toFixed(2)}</strong>, with
        pressure at{" "}
        <strong>{Number(summary.avg_pressure || 0).toFixed(2)}</strong> and
        temperature at{" "}
        <strong>{Number(summary.avg_temperature || 0).toFixed(2)}</strong>.
      </p>
      {topType && (
        <p>
          Most common equipment: <strong>{topType[0]}</strong> ({topType[1]}{" "}
          units).
        </p>
      )}
      <p>
        Stability index is <strong>{insights.stability_index ?? "--"}</strong>{" "}
        and efficiency index is{" "}
        <strong>{insights.efficiency_index ?? "--"}</strong>.
      </p>
      {(insights.alerts || []).length > 0 && (
        <p>Alerts: {insights.alerts.join(" • ")}</p>
      )}
    </div>
  );
}
