import { useRef, useState } from "react";
import { Monitor, Tablet, Smartphone, RefreshCw, ExternalLink } from "lucide-react";

const DEVICES = [
  { label: "Desktop", icon: Monitor, width: "100%" },
  { label: "Tablet", icon: Tablet, width: "768px" },
  { label: "Mobile", icon: Smartphone, width: "375px" },
];

export default function PreviewPane({ previewSrc }) {
  const iframeRef = useRef(null);
  const [device, setDevice] = useState("Desktop");

  const current = DEVICES.find((d) => d.label === device);

  function reload() {
    if (iframeRef.current && previewSrc) {
      const src = iframeRef.current.src;
      iframeRef.current.src = "";
      setTimeout(() => { if (iframeRef.current) iframeRef.current.src = src; }, 10);
    }
  }

  return (
    <>
      <div className="preview-toolbar">
        <div className="device-switch">
          {DEVICES.map((d) => (
            <button
              key={d.label}
              className={`dev-btn ${device === d.label ? "active" : ""}`}
              onClick={() => setDevice(d.label)}
              title={d.label}
            >
              <d.icon size={12} style={{ display: "inline", verticalAlign: "middle", marginRight: 3 }} />
              {d.label}
            </button>
          ))}
        </div>
        <div className="preview-info">
          {previewSrc && (
            <>
              <button className="icon-btn" onClick={reload} title="Reload preview">
                <RefreshCw size={12} />
              </button>
              <a
                className="icon-btn"
                href={previewSrc}
                target="_blank"
                rel="noreferrer"
                title="Open in new tab"
              >
                <ExternalLink size={12} /> New tab
              </a>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem" }}>
                Width: {current.width}
              </span>
            </>
          )}
        </div>
      </div>

      <div className="preview-frame-wrap" style={{ position: "relative" }}>
        {!previewSrc && (
          <div className="preview-placeholder">
            <Monitor size={32} strokeWidth={1.2} style={{ marginBottom: 12, color: "var(--border-subtle)" }} />
            <h3>No page loaded</h3>
            <p>Run the pipeline or load an existing file from the header to preview it here.</p>
          </div>
        )}
        <iframe
          ref={iframeRef}
          className="preview-iframe"
          src={previewSrc || "about:blank"}
          title="Site Preview"
          style={{ width: current.width, display: previewSrc ? "block" : "none" }}
        />
      </div>
    </>
  );
}
