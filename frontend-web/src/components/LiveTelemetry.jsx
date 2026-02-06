import React from "react";
import { Line } from "react-chartjs-2";

export default function LiveTelemetry({ live, enabled }) {
  if (!enabled) return null;

  const labels = live?.labels || [];
  const signals = live?.signals || {};

  const data = {
    labels,
    datasets: [
      {
        label: "Flowrate",
        data: signals.flowrate || [],
        borderColor: "#ff7a00",
        backgroundColor: "rgba(255, 122, 0, 0.2)",
        tension: 0.3,
      },
      {
        label: "Pressure",
        data: signals.pressure || [],
        borderColor: "#2ec4b6",
        backgroundColor: "rgba(46, 196, 182, 0.2)",
        tension: 0.3,
      },
      {
        label: "Temperature",
        data: signals.temperature || [],
        borderColor: "#4c6fff",
        backgroundColor: "rgba(76, 111, 255, 0.2)",
        tension: 0.3,
      },
    ],
  };

  return (
    <div className="card">
      <h2>Live Telemetry</h2>
      <Line data={data} />
    </div>
  );
}
