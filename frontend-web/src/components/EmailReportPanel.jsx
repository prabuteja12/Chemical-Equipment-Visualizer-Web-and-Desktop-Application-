import React, { useState } from "react";

export default function EmailReportPanel({ datasets, onSend, status }) {
  const [email, setEmail] = useState("");
  const [datasetId, setDatasetId] = useState("");

  const handleSend = () => {
    if (!email || !datasetId) return;
    onSend(datasetId, email);
  };

  return (
    <div className="card mail-card">
      <h2>Email Report</h2>
      <p className="muted">Send a PDF report to any recipient.</p>
      <select
        value={datasetId}
        onChange={(e) => setDatasetId(e.target.value)}
      >
        <option value="">Select dataset</option>
        {datasets.map((ds) => (
          <option key={ds.id} value={ds.id}>
            {ds.name}
          </option>
        ))}
      </select>
      <input
        type="email"
        placeholder="name@example.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <button onClick={handleSend}>Send PDF</button>
      {status && <p className="muted">{status}</p>}
    </div>
  );
}
