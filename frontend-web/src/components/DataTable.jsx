import React, { useMemo, useState } from "react";

export default function DataTable({ dataset }) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const rows = dataset?.rows || [];
  const columns = dataset?.columns || Object.keys(rows[0] || {});

  const filtered = useMemo(() => {
    let data = rows;
    if (typeFilter !== "All") {
      data = data.filter((row) => row.Type === typeFilter);
    }
    if (!filter) return data;
    const query = filter.toLowerCase();
    return data.filter((row) =>
      columns.some((col) =>
        String(row[col] ?? "")
          .toLowerCase()
          .includes(query),
      ),
    );
  }, [rows, columns, filter, typeFilter]);

  const typeOptions = useMemo(() => {
    const types = new Set(rows.map((row) => row.Type).filter(Boolean));
    return ["All", ...Array.from(types)];
  }, [rows]);

  const exportCsv = () => {
    const header = columns.join(",");
    const body = filtered
      .map((row) => columns.map((col) => row[col]).join(","))
      .join("\n");
    const blob = new Blob([header + "\n" + body], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "equipment_records.csv";
    link.click();
  };

  return (
    <div className={`card table-card ${open ? "open" : "closed"}`}>
      <div className="table-header">
        <h2>Equipment Records</h2>
        <div className="table-actions">
          <input
            type="text"
            placeholder="Search records"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            {typeOptions.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          <button className="outline small" onClick={exportCsv}>
            Export CSV
          </button>
          <button
            className="ghost small collapse-btn"
            onClick={() => setOpen(!open)}
          >
            {open ? "\u25B4" : "\u25BE"}
          </button>
        </div>
      </div>
      <div className="table-meta">
        {filtered.length} rows · Columns: {columns.slice(0, 3).join(", ")}
        {columns.length > 3 ? ` +${columns.length - 3}` : ""}
      </div>
      <div className="table-note">
        Highlighted rows indicate values outside the normal band.
      </div>
      {open && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, idx) => (
                <tr key={idx}>
                  {columns.map((col) => (
                    <td key={col}>{row[col]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
