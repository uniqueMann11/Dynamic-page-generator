import { useState, useEffect, useRef } from "react";
import Header from "./components/Header.jsx";
import ConfigPanel from "./components/ConfigPanel.jsx";
import PreviewPane from "./components/PreviewPane.jsx";
import CodeViewer from "./components/CodeViewer.jsx";
import TerminalLogs from "./components/TerminalLogs.jsx";
import { previewUrl, openPipelineStream } from "./api.js";
import { FileText, Code, ScrollText, Eye } from "lucide-react";

import { Activity } from "lucide-react";

const TABS = [
  { id: "preview", label: "Preview", Icon: Eye },
  { id: "code",    label: "Code Inspector", Icon: Code },
  { id: "logs",    label: "Generation Progress", Icon: Activity },
];

function Toast({ message }) {
  return (
    <div className={`toast ${message ? "show" : ""}`}>
      {message}
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState("dark");
  const [activeTab, setActiveTab] = useState("preview");
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [components, setComponents] = useState(null);
  const [previewSrc, setPreviewSrc] = useState(null);
  const [statusBadge, setStatusBadge] = useState({ label: "Ready", cls: "" });
  const [pageTitle, setPageTitle] = useState("Configure and run pipeline");
  const [pageFile, setPageFile] = useState(null);
  const [toast, setToast] = useState("");
  const toastTimer = useRef(null);
  const stopStream = useRef(null);

  // Apply theme to <html>
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }

  function showToast(msg) {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 2400);
  }

  // Run pipeline with SSE streaming
  function handleRun(formData) {
    if (stopStream.current) stopStream.current();
    setRunning(true);
    setLogs([]);
    setStatusBadge({ label: "Running", cls: "running" });
    setPageTitle(`Generating page for ${formData.city}...`);
    setActiveTab("logs");

    const newLogs = [];
    function addLog(text) {
      newLogs.push(text);
      setLogs([...newLogs]);
    }

    addLog(`[START] Pipeline started ? ${formData.role} in ${formData.city}, ${formData.state}`);
    if (formData.skip_generate) addLog("[INFO] Skip AI generation ? using existing JSONs.");
    if (formData.skip_widget) addLog("[INFO] Skip hero widget injection.");

    const stop = openPipelineStream(
      formData,
      (line) => addLog(line.trimEnd()),
      (data) => {
        setComponents(data);
        setPreviewSrc(previewUrl(data.filename));
        setPageTitle(data.title || data.filename);
        setPageFile(data.filename);
        setStatusBadge({ label: "Ready", cls: "ready" });
        setRunning(false);
        addLog(`\n[SUCCESS] Pipeline complete -> ${data.filename}`);
        showToast(`Generated ${data.filename}`);
        setTimeout(() => setActiveTab("preview"), 700);
      },
      (errText) => {
        addLog(`\n[ERROR] ${errText}`);
        setStatusBadge({ label: "Error", cls: "error" });
        setPageTitle("Pipeline execution error");
        setRunning(false);
        showToast(`Error: ${errText}`);
      }
    );

    stopStream.current = stop;
  }

  return (
    <div className="studio-root">
      <Header
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <div className="studio-body">
        <ConfigPanel running={running} onRun={handleRun} />

        <main className="workspace-panel">
          {/* Workspace header */}
          <div className="workspace-header">
            <div className="page-meta">
              <span className={`badge ${statusBadge.cls}`}>{statusBadge.label}</span>
              <span className="page-title">{pageTitle}</span>
              {pageFile && <span className="page-file-pill">{pageFile}</span>}
            </div>
            <div className="workspace-actions">
              {components && (
                <>
                  <button
                    className="icon-btn"
                    onClick={() => {
                      if (components.full_html) {
                        navigator.clipboard.writeText(components.full_html);
                        showToast("Full HTML copied");
                      }
                    }}
                    title="Copy full HTML"
                  >
                    <FileText size={12} /> Copy HTML
                  </button>
                  {previewSrc && (
                    <a className="icon-btn" href={previewSrc} target="_blank" rel="noreferrer">
                      Open
                    </a>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Navigation tabs */}
          <nav className="nav-tabs">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
                onClick={() => setActiveTab(t.id)}
              >
                <t.Icon size={12} />
                {t.label}
                {t.id === "logs" && running && (
                  <span className="tab-indicator live" />
                )}
                {t.id === "logs" && logs.length > 0 && (
                  <span className="tab-count">{logs.length}</span>
                )}
              </button>
            ))}
          </nav>

          {/* Tab content */}
          <div className="tab-content">
            {/* Preview */}
            <div className={`tab-pane ${activeTab === "preview" ? "active" : ""}`}>
              <PreviewPane previewSrc={previewSrc} />
            </div>

            {/* Code inspector */}
            <div className={`tab-pane ${activeTab === "code" ? "active" : ""}`}>
              <CodeViewer components={components} />
            </div>

            {/* Logs */}
            <div className={`tab-pane ${activeTab === "logs" ? "active" : ""}`}>
              <TerminalLogs
                logs={logs}
                running={running}
                onClear={() => setLogs([])}
              />
            </div>
          </div>
        </main>
      </div>

      <Toast message={toast} />
    </div>
  );
}
