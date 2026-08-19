import { useState, useEffect } from "react";
import { Code2, Sun, Moon, FolderOpen } from "lucide-react";
import { fetchFiles } from "../api.js";

export default function Header({ theme, toggleTheme, onFileLoad }) {
  const [files, setFiles] = useState([]);
  const [selected, setSelected] = useState("");

  useEffect(() => {
    fetchFiles()
      .then((d) => {
        setFiles(d.files || []);
        const def = (d.files || []).find((f) => f.filename === "location-page-gurgaon.html");
        if (def) {
          setSelected(def.filename);
          onFileLoad(def.filename);
        } else if (d.files && d.files.length > 0) {
          setSelected(d.files[0].filename);
          onFileLoad(d.files[0].filename);
        }
      })
      .catch(() => {});
  }, []);

  function handleLoad() {
    if (selected) onFileLoad(selected);
  }

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="brand">
          <Code2 className="brand-svg" />
          <span className="brand-title">Pipeline Studio</span>
        </div>
        <div className="env-badge">
          <span className="status-dot" />
          <span>Local :8000</span>
        </div>
        <div className="file-inspector">
          <select
            className="inspector-select"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {files.length === 0 && <option value="">No files found</option>}
            {files.map((f) => (
              <option key={f.filename} value={f.filename}>
                {f.filename} ({f.size_kb} KB)
              </option>
            ))}
          </select>
          <button className="icon-btn" onClick={handleLoad} title="Load and inspect file">
            <FolderOpen /> Load
          </button>
        </div>
      </div>

      <div className="header-right">
        <button className="icon-btn" onClick={toggleTheme} title="Toggle theme">
          {theme === "dark" ? <Sun /> : <Moon />}
        </button>
      </div>
    </header>
  );
}
