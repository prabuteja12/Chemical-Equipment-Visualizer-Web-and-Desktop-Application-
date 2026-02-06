import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import JSZip from "jszip";
import UploadPanel from "./components/UploadPanel.jsx";
import SummaryCards from "./components/SummaryCards.jsx";
import InsightPanel from "./components/InsightPanel.jsx";
import ChartsPanel from "./components/ChartsPanel.jsx";
import LiveTelemetry from "./components/LiveTelemetry.jsx";
import DataTable from "./components/DataTable.jsx";
import RecentUploads from "./components/RecentUploads.jsx";
import EmailReportPanel from "./components/EmailReportPanel.jsx";
import OperationalBrief from "./components/OperationalBrief.jsx";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

const SESSION_KEYS = {
  datasets: "chemviz.session.datasets",
  active: "chemviz.session.active",
};

const loadSession = (key, fallback) => {
  try {
    const stored = sessionStorage.getItem(key);
    return stored ? JSON.parse(stored) : fallback;
  } catch {
    return fallback;
  }
};

const saveSession = (key, value) => {
  sessionStorage.setItem(key, JSON.stringify(value));
};

export default function App() {
  const [datasets, setDatasets] = useState(() =>
    loadSession(SESSION_KEYS.datasets, [])
  );
  const [activeDataset, setActiveDataset] = useState(() =>
    loadSession(SESSION_KEYS.active, null)
  );
  const [liveData, setLiveData] = useState(null);
  const [liveEnabled, setLiveEnabled] = useState(true);
  const [theme, setTheme] = useState("light");
  const [view, setView] = useState("home");
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [loading, setLoading] = useState(false);
  const [emailStatus, setEmailStatus] = useState("");
  const [error, setError] = useState("");
  const chartDownloadersRef = useRef({});

  const apiRequest = async (method, url, config = {}) => {
    try {
      const response = await axios({
        method,
        url: `${API_BASE}${url}`,
        ...config,
      });
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || "Request failed.");
    }
  };

  const fetchDatasets = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await apiRequest("get", "/datasets/");
      setDatasets(data);
      saveSession(SESSION_KEYS.datasets, data);
    } catch (err) {
      const cached = loadSession(SESSION_KEYS.datasets, []);
      if (cached.length) setDatasets(cached);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectDataset = async (id) => {
    setLoading(true);
    setError("");
    try {
      const data = await apiRequest("get", `/datasets/${id}/?include_rows=1`);
      setActiveDataset(data);
      saveSession(SESSION_KEYS.active, data);
      setView("detail");
    } catch (err) {
      const cached = loadSession(SESSION_KEYS.active, null);
      if (cached) {
        setActiveDataset(cached);
        setView("detail");
      }
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (file) => {
    setLoading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const data = await apiRequest("post", "/upload/", {
        data: form,
        headers: { "Content-Type": "multipart/form-data" },
      });
      setActiveDataset(data);
      saveSession(SESSION_KEYS.active, data);
      setView("detail");
      await fetchDatasets();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = async (datasetId) => {
    try {
      const response = await axios({
        url: `${API_BASE}/datasets/${datasetId}/report/`,
        method: "get",
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `report_${datasetId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      setError("Unable to download report.");
    }
  };

  const handleSendEmail = async (datasetId, email) => {
    setEmailStatus("");
    try {
      await apiRequest("post", `/datasets/${datasetId}/email/`, {
        data: { email },
      });
      setEmailStatus(`Report sent to ${email}`);
    } catch (err) {
      setEmailStatus(err.message);
    }
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const registerDownloader = (key, fn) => {
    chartDownloadersRef.current[key] = fn;
  };

  const collectChartImages = () => {
    const downloaders = Object.values(chartDownloadersRef.current);
    if (!downloaders.length) {
      setError("Charts are not ready yet.");
      return [];
    }
    return downloaders.flatMap((fn) => fn() || []);
  };

  const handleDownloadChartsZip = async () => {
    const images = collectChartImages();
    if (!images.length) return;
    const zip = new JSZip();
    images.forEach((item) => {
      const base64 = item.dataUrl.split(",")[1];
      zip.file(`${item.name}.png`, base64, { base64: true });
    });
    const blob = await zip.generateAsync({ type: "blob" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.setAttribute("download", "charts_bundle.zip");
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    fetchDatasets();
  }, []);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    window.addEventListener("beforeunload", () => sessionStorage.clear());
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    if (!liveEnabled || !activeDataset) return undefined;
    const fetchLive = async () => {
      try {
        const data = await apiRequest(
          "get",
          `/datasets/${activeDataset.id}/live/?points=24`
        );
        setLiveData(data.live);
      } catch {
        setLiveData(null);
      }
    };
    fetchLive();
    const interval = setInterval(fetchLive, 8000);
    return () => clearInterval(interval);
  }, [liveEnabled, activeDataset?.id]);

  return (
    <div className="app-shell">
      <header className="hero-card">
        <div className="hero-left">
          <h1>Chemical Equipment Parameter Visualizer</h1>
          <p className="subhead">
            Upload datasets, inspect operational health, and export reports from
            a single console.
          </p>
        </div>
        <div className="hero-right">
          <span className="control-room">CONTROL ROOM</span>
          <span className={`status-pill ${isOnline ? "online" : "offline"}`}>
            {isOnline ? "Online" : "Offline"}
          </span>
          <button className="outline" onClick={toggleTheme}>
            SWITCH TO {theme === "light" ? "DARK" : "LIGHT"} MODE
          </button>
          <label className="toggle">
            <input
              type="checkbox"
              checked={liveEnabled}
              onChange={(e) => setLiveEnabled(e.target.checked)}
            />
            <span>Live Updates</span>
          </label>
        </div>
      </header>

      {view === "home" && (
        <main className="layout-home">
          <section className="panel left">
            <UploadPanel onUpload={handleUpload} loading={loading} />
            <EmailReportPanel
              datasets={datasets}
              onSend={handleSendEmail}
              status={emailStatus}
            />
          </section>
          <section className="panel right">
            <RecentUploads
              datasets={datasets}
              onSelect={selectDataset}
              onDownload={handleDownloadReport}
            />
          </section>
        </main>
      )}

      {view === "detail" && activeDataset && (
        <main className="layout-detail">
          <section className="detail-header card">
            <div className="detail-meta">
              <button className="outline back-btn" onClick={() => setView("home")}>
                <span className="back-icon" aria-hidden="true">&larr;</span>
                Back to uploads
              </button>
              <h2>{activeDataset.name}</h2>
              <p>
                Uploaded{" "}
                {new Date(activeDataset.created_at).toLocaleString()}
              </p>
            </div>
            <div className="detail-actions">
              <button className="outline" onClick={handleDownloadChartsZip}>
                Download Charts ZIP
              </button>
              <button className="outline" onClick={() => handleDownloadReport(activeDataset.id)}>
                Download Charts
              </button>
              <button className="outline" onClick={() => handleDownloadReport(activeDataset.id)}>Download PDF</button>
            </div>
          </section>

          <section className="detail-grid">
            <div className="card brief-panel">
              <OperationalBrief dataset={activeDataset} />
            </div>
            <InsightPanel dataset={activeDataset} />
          </section>

          <SummaryCards dataset={activeDataset} />

          <DataTable dataset={activeDataset} />

          <LiveTelemetry live={liveData} enabled={liveEnabled} />

          <ChartsPanel
            dataset={activeDataset}
            registerDownloader={registerDownloader}
          />
          {error && <div className="error-banner">{error}</div>}
        </main>
      )}
    </div>
  );
}






