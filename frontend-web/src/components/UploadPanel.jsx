import React, { useState } from "react";

export default function UploadPanel({ onUpload, loading }) {
  const [file, setFile] = useState(null);

  const handleChoose = (event) => {
    const selected = event.target.files?.[0];
    setFile(selected || null);
  };

  const handleUpload = () => {
    if (!file) return;
    onUpload(file);
  };

  return (
    <div className="card upload-card">
      <h2>Upload Dataset</h2>
      <p className="muted">
        CSV with Equipment Name, Type, Flowrate, Pressure, Temperature.
      </p>
      <div className="upload-row">
        <label className="file-chip">
          Choose File
          <input type="file" accept=".csv" onChange={handleChoose} />
        </label>
        <span className="file-name">{file ? file.name : "No file chosen"}</span>
        <button onClick={handleUpload} disabled={loading || !file}>
          {loading ? "Uploading..." : "Upload"}
        </button>
      </div>
    </div>
  );
}
