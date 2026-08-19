import { useEffect, useRef } from "react";
import { Trash2, Terminal } from "lucide-react";

function classifyLine(text) {
  if (!text || !text.trim()) return "normal";
  if (text.includes("STEP") || text.includes("====")) return "step";
  if (text.includes("[OK]") || text.includes("applied") || text.includes("written") || text.includes("success")) return "ok";
  if (text.includes("Error") || text.includes("ERROR") || text.includes("failed") || text.includes("FAILED")) return "err";
  if (text.includes("Warning") || text.includes("WARN")) return "warn";
  if (text.startsWith("[INFO]") || text.startsWith("[START]") || text.startsWith("[SYS]")) return "sys";
  return "normal";
}

export default function TerminalLogs({ logs, onClear, running }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  return (
    <>
      <div className="logs-toolbar">
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Terminal size={13} />
          <span>Pipeline Logs</span>
          {running && (
            <span style={{ color: "var(--accent-green)", fontStyle: "italic" }}>
              — streaming...
            </span>
          )}
        </div>
        <button className="icon-btn" onClick={onClear} title="Clear logs">
          <Trash2 size={12} /> Clear
        </button>
      </div>
      <div className="logs-console">
        {logs.length === 0 && (
          <div className="log-line sys">No logs yet. Run the pipeline to see output here.</div>
        )}
        {logs.map((line, i) => (
          <div key={i} className={`log-line ${classifyLine(line)}`}>{line}</div>
        ))}
        <div ref={bottomRef} />
      </div>
    </>
  );
}
