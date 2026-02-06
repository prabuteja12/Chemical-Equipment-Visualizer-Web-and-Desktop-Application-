import React, { useEffect, useRef } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Line, Scatter } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

export default function ChartsPanel({ dataset, registerDownloader }) {
  if (!dataset) return null;

  const barRef = useRef(null);
  const scatterRef = useRef(null);
  const lineRef = useRef(null);
  const histRef = useRef(null);

  const summary = dataset.summary || dataset;
  const typeDistribution = summary.type_distribution || {};
  const rows = dataset.rows || [];

  const barData = {
    labels: Object.keys(typeDistribution),
    datasets: [
      {
        label: "Count",
        data: Object.values(typeDistribution),
        backgroundColor: "#FF7A00",
        borderRadius: 8,
      },
    ],
  };

  const scatterPoints = rows
    .map((row) => ({
      x: Number(row.Pressure),
      y: Number(row.Flowrate),
    }))
    .filter((point) => !Number.isNaN(point.x) && !Number.isNaN(point.y));

  const scatterData = {
    datasets: [
      {
        label: "Pressure vs Flowrate",
        data: scatterPoints,
        backgroundColor: "rgba(46, 196, 182, 0.7)",
      },
    ],
  };

  const tempRows = rows.slice(0, 20);
  const lineData = {
    labels: tempRows.map((row) => row["Equipment Name"] || "Unit"),
    datasets: [
      {
        label: "Temperature",
        data: tempRows.map((row) => Number(row.Temperature)),
        borderColor: "#4C6FFF",
        backgroundColor: "rgba(76, 111, 255, 0.2)",
        tension: 0.3,
      },
    ],
  };

  const buildHistogram = (values, binCount = 6) => {
    if (!values.length) {
      return { labels: [], data: [], min: null, max: null, binSize: null };
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const binSize = span / binCount;
    const bins = Array(binCount).fill(0);
    values.forEach((val) => {
      const idx = Math.min(binCount - 1, Math.floor((val - min) / binSize));
      bins[idx] += 1;
    });
    const labels = bins.map((_, idx) => {
      const start = min + idx * binSize;
      const end = start + binSize;
      return `${start.toFixed(1)}-${end.toFixed(1)}`;
    });
    return { labels, data: bins, min, max, binSize };
  };

  const flowValues = rows
    .map((row) => Number(row.Flowrate))
    .filter((val) => !Number.isNaN(val));

  const flowHistogram = buildHistogram(flowValues, 6);
  const flowHistData = {
    labels: flowHistogram.labels,
    datasets: [
      {
        label: "Flowrate bins",
        data: flowHistogram.data,
        backgroundColor: "rgba(76, 111, 255, 0.45)",
        borderRadius: 6,
      },
    ],
  };

  const totalTypes = Object.keys(typeDistribution).length;
  const topType = Object.entries(typeDistribution).sort((a, b) => b[1] - a[1])[0];
  const topTypeShare = topType && summary.row_count
    ? (topType[1] / summary.row_count) * 100
    : null;

  const pressureValues = rows
    .map((row) => Number(row.Pressure))
    .filter((val) => !Number.isNaN(val));

  const computeCorrelation = (x, y) => {
    if (x.length === 0 || y.length === 0 || x.length !== y.length) return null;
    const meanX = x.reduce((acc, val) => acc + val, 0) / x.length;
    const meanY = y.reduce((acc, val) => acc + val, 0) / y.length;
    let num = 0;
    let denX = 0;
    let denY = 0;
    for (let i = 0; i < x.length; i += 1) {
      const dx = x[i] - meanX;
      const dy = y[i] - meanY;
      num += dx * dy;
      denX += dx * dx;
      denY += dy * dy;
    }
    const den = Math.sqrt(denX * denY);
    if (!den) return null;
    return num / den;
  };

  const correlation = computeCorrelation(pressureValues, flowValues);
  let trendLabel = "No clear trend";
  if (correlation !== null) {
    if (correlation > 0.6) trendLabel = "Strong positive trend";
    else if (correlation > 0.3) trendLabel = "Moderate positive trend";
    else if (correlation > 0.1) trendLabel = "Slight positive trend";
    else if (correlation < -0.6) trendLabel = "Strong negative trend";
    else if (correlation < -0.3) trendLabel = "Moderate negative trend";
    else if (correlation < -0.1) trendLabel = "Slight negative trend";
  }

  const tempValues = rows
    .map((row) => Number(row.Temperature))
    .filter((val) => !Number.isNaN(val));
  const tempStats = {
    min: tempValues.length ? Math.min(...tempValues) : null,
    max: tempValues.length ? Math.max(...tempValues) : null,
    avg: tempValues.length
      ? tempValues.reduce((acc, val) => acc + val, 0) / tempValues.length
      : null,
  };
  const tempAbove320 = tempValues.filter((val) => val > 320).length;

  const mostCommonBin = flowHistogram.data.length
    ? flowHistogram.data.indexOf(Math.max(...flowHistogram.data))
    : null;
  const commonBinLabel =
    mostCommonBin === null ? "--" : flowHistogram.labels[mostCommonBin];

  const binSize = flowHistogram.binSize || null;

  useEffect(() => {
    if (!registerDownloader) return;
    const getImage = (ref, name) => {
      const chart = ref.current;
      if (!chart || typeof chart.toBase64Image !== "function") return null;
      return { name, dataUrl: chart.toBase64Image("image/png", 1) };
    };

    registerDownloader("charts", () => {
      return [
        getImage(barRef, "equipment_mix"),
        getImage(scatterRef, "pressure_vs_flowrate"),
        getImage(lineRef, "temperature_profile"),
        getImage(histRef, "flowrate_distribution"),
      ].filter(Boolean);
    });
  }, [registerDownloader]);

  return (
    <div className="charts-grid">
      <div className="card chart-row">
        <div className="chart-main">
          <h2>Equipment Mix</h2>
          <Bar ref={barRef} data={barData} />
        </div>
        <div className="chart-info">
          <h3>What This Means</h3>
          <p className="chart-note">
            Each bar shows how many units belong to each equipment type.
          </p>
          <div className="chart-info-item">
            <span>Total Types</span>
            <strong>{totalTypes}</strong>
          </div>
          <div className="chart-info-item">
            <span>Top Type</span>
            <strong>{topType ? `${topType[0]} (${topType[1]})` : "--"}</strong>
          </div>
          <div className="chart-info-item">
            <span>Top Type Share</span>
            <strong>
              {topTypeShare === null ? "--" : `${topTypeShare.toFixed(1)}%`}
            </strong>
          </div>
          <div className="chart-info-item">
            <span>Total Records</span>
            <strong>{summary.row_count}</strong>
          </div>
        </div>
      </div>
      <div className="card chart-row">
        <div className="chart-main">
          <h2>Pressure vs Flowrate</h2>
          <Scatter ref={scatterRef} data={scatterData} />
        </div>
        <div className="chart-info">
          <h3>How to Read</h3>
          <p className="chart-note">
            Each dot is an equipment unit. Dots up and right indicate higher
            pressure and flowrate together.
          </p>
          <div className="chart-info-item">
            <span>Correlation</span>
            <strong>{correlation === null ? "--" : correlation.toFixed(2)}</strong>
          </div>
          <div className="chart-info-item">
            <span>Trend</span>
            <strong>{trendLabel}</strong>
          </div>
          <div className="chart-info-item">
            <span>Samples</span>
            <strong>{scatterPoints.length}</strong>
          </div>
          <div className="chart-info-item">
            <span>Flowrate Avg</span>
            <strong>{Number(summary.avg_flowrate || 0).toFixed(2)}</strong>
          </div>
        </div>
      </div>
      <div className="card chart-row">
        <div className="chart-main">
          <h2>Temperature Profile</h2>
          <Line ref={lineRef} data={lineData} />
        </div>
        <div className="chart-info">
          <h3>What to Watch</h3>
          <p className="chart-note">
            This line shows temperatures for the first {tempRows.length} units.
          </p>
          <div className="chart-info-item">
            <span>Average</span>
            <strong>{tempStats.avg === null ? "--" : tempStats.avg.toFixed(2)}</strong>
          </div>
          <div className="chart-info-item">
            <span>Min</span>
            <strong>{tempStats.min === null ? "--" : tempStats.min.toFixed(2)}</strong>
          </div>
          <div className="chart-info-item">
            <span>Max</span>
            <strong>{tempStats.max === null ? "--" : tempStats.max.toFixed(2)}</strong>
          </div>
          <div className="chart-info-item">
            <span>Above 320°C</span>
            <strong>{tempAbove320}</strong>
          </div>
        </div>
      </div>
      <div className="card chart-row">
        <div className="chart-main">
          <h2>Flowrate Distribution</h2>
          <Bar ref={histRef} data={flowHistData} />
        </div>
        <div className="chart-info">
          <h3>How to Read</h3>
          <p className="chart-note">
            Taller bars show the most common operating bands.
          </p>
          <div className="chart-info-item">
            <span>Range</span>
            <strong>
              {flowHistogram.min === null
                ? "--"
                : `${flowHistogram.min.toFixed(2)}–${flowHistogram.max.toFixed(2)}`}
            </strong>
          </div>
          <div className="chart-info-item">
            <span>Most Common Band</span>
            <strong>{commonBinLabel}</strong>
          </div>
          <div className="chart-info-item">
            <span>Samples</span>
            <strong>{flowValues.length}</strong>
          </div>
          <div className="chart-info-item">
            <span>Bin Size</span>
            <strong>{binSize === null ? "--" : binSize.toFixed(2)}</strong>
          </div>
        </div>
      </div>
    </div>
  );
}
