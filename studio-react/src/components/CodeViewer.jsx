import { useState } from "react";
import { Copy, Check } from "lucide-react";

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false);
  function doCopy() {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }
  return (
    <button className="icon-btn" onClick={doCopy} title="Copy to clipboard">
      {copied ? <Check size={12} style={{ color: "var(--accent-green)" }} /> : <Copy size={12} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

const TABS = [
  { id: "main",   label: "<main>",  tag: "HTML",    statKey: "main_lines",    contentKey: "main_html" },
  { id: "css",    label: "<style>", tag: "CSS",     statKey: "css_lines",     contentKey: "css" },
  { id: "js",     label: "<script>",tag: "JS",      statKey: "js_lines",      contentKey: "js" },
  { id: "schema", label: "ld+json", tag: "JSON-LD", statKey: "json_ld_lines", contentKey: "json_ld" },
  { id: "meta",   label: "<meta>",  tag: "META",    statKey: null,            contentKey: "meta" },
];

export default function CodeViewer({ components }) {
  const [activeTab, setActiveTab] = useState("main");

  const tab = TABS.find((t) => t.id === activeTab);
  const content = components ? (components[tab.contentKey] || "") : "";
  const lineCount = tab.statKey ? (components?.stats?.[tab.statKey] || 0) : content.split("\n").length;

  return (
    <>
      {/* Sub-tab bar */}
      <div className="nav-tabs" style={{ paddingLeft: 0 }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
            onClick={() => setActiveTab(t.id)}
          >
            <span className="tb-tag" style={{ fontSize: "0.6rem", padding: "0 4px" }}>{t.tag}</span>
            {t.label}
          </button>
        ))}
      </div>

      {/* Toolbar */}
      <div className="code-toolbar">
        <div className="tb-left">
          <span className="tb-tag">{tab.tag}</span>
          <span className="tb-desc">{lineCount} lines</span>
        </div>
        <div className="tb-right">
          <CopyBtn text={content} />
        </div>
      </div>

      {/* Code content */}
      <div className="code-container">
        {!components ? (
          <div style={{ padding: "24px 16px", color: "var(--text-muted)", fontSize: "0.78rem" }}>
            Load a file to inspect its code components.
          </div>
        ) : (
          <pre><code>{content || "(empty)"}</code></pre>
        )}
      </div>
    </>
  );
}
