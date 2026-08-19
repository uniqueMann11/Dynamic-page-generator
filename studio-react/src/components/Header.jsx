import { Code2, Sun, Moon } from "lucide-react";

export default function Header({ theme, toggleTheme }) {
  return (
    <header className="app-header">
      <div className="header-left">
        <div className="brand">
          <Code2 className="brand-svg" />
          <span className="brand-title">Pipeline Studio</span>
        </div>
        <div className="env-badge">
          <span className="status-dot" />
          <span>Studio Active</span>
        </div>
      </div>

      <div className="header-right">
        <button className="icon-btn" onClick={toggleTheme} title="Toggle theme">
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  );
}
