import { useState, useMemo } from "react";
import {
  CheckCircle2,
  Circle,
  Loader2,
  Sparkles,
  Layers,
  FileCode,
  Sliders,
  Terminal,
  ChevronDown,
  ChevronUp,
  Trash2,
  AlertCircle
} from "lucide-react";

const STEPS = [
  {
    id: 1,
    title: "Step 1/4: Hero & Value Proposition",
    desc: "Crafting hero headline, value badges, and introduction",
    icon: Sparkles,
    matchStart: ["STEP 1/4", "hero.json", "Hero Section"],
    matchEnd: ["Step 1/4 complete", "Hero section applied", "new_hero.json"]
  },
  {
    id: 2,
    title: "Step 2/4: Value Pillars & Quick Answer",
    desc: "Generating business pillars and direct-response answer",
    icon: Layers,
    matchStart: ["STEP 2/4", "second_hero.json", "Value & Quick Answer"],
    matchEnd: ["Step 2/4 complete", "Second hero section applied", "new_second_hero.json"]
  },
  {
    id: 3,
    title: "Step 3/4: Services & Local Ecosystem",
    desc: "Building localized service cards and ecosystem context",
    icon: Sliders,
    matchStart: ["STEP 3/4", "third_section.json", "Services & Local Context"],
    matchEnd: ["Step 3/4 complete", "Third section applied", "new_third_section.json"]
  },
  {
    id: 4,
    title: "Step 4/4: Process, Case Studies & FAQ",
    desc: "Writing timeline steps, metrics, testimonials, and FAQs",
    icon: FileCode,
    matchStart: ["STEP 4/4", "final_section.json", "Process, Case Studies"],
    matchEnd: ["Step 4/4 complete", "Final section applied", "new_final_section.json"]
  },
  {
    id: 5,
    title: "Step 5: HTML Compilation & Meta Tags",
    desc: "Assembling full responsive page and JSON-LD schemas",
    icon: FileCode,
    matchStart: ["STEP 2: Compiling", "COMPILING", "Compiling HTML"],
    matchEnd: ["Final website written", "Compilation complete", "Meta tags"]
  },
  {
    id: 6,
    title: "Step 6: Interactive Hero Viewer Widget",
    desc: "Generating and injecting interactive visual component",
    icon: Sparkles,
    matchStart: ["STEP 3: Hero Viewer", "WIDGET", "Hero Viewer Widget"],
    matchEnd: ["Hero viewer widget injected", "PIPELINE COMPLETE"]
  }
];

export default function TerminalLogs({ logs = [], running = false, onClear }) {
  const [showRawConsole, setShowRawConsole] = useState(false);

  // Compute status for each step based on log stream
  const { stepStatuses, progressPercent, currentStepLabel } = useMemo(() => {
    const raw = logs.join("\n");
    const statuses = {};
    let completedCount = 0;
    let activeStep = null;

    STEPS.forEach((step) => {
      const hasStarted = step.matchStart.some((m) => raw.includes(m));
      const hasEnded = step.matchEnd.some((m) => raw.includes(m));

      if (hasEnded) {
        statuses[step.id] = "completed";
        completedCount++;
      } else if (hasStarted) {
        statuses[step.id] = "running";
        activeStep = step;
      } else {
        statuses[step.id] = "pending";
      }
    });

    if (raw.includes("[ERROR]") || raw.includes("Error:") || raw.includes("FAILED")) {
      if (activeStep) statuses[activeStep.id] = "error";
    }

    const total = STEPS.length;
    let pct = Math.round((completedCount / total) * 100);
    if (running && pct < 95) {
      pct = Math.max(pct, activeStep ? Math.round(((activeStep.id - 0.5) / total) * 100) : 10);
    }
    if (!running && completedCount === total) pct = 100;

    const label = activeStep
      ? activeStep.title
      : completedCount === total
      ? "All steps completed"
      : running
      ? "Starting generation..."
      : "Ready to generate";

    return { stepStatuses: statuses, progressPercent: pct, currentStepLabel: label };
  }, [logs, running]);

  return (
    <div className="progress-panel">
      {/* Top Status Header */}
      <div className="progress-header">
        <div className="progress-title-row">
          <div className="progress-main-title">
            <Sparkles size={16} className={running ? "spin-slow" : ""} style={{ color: "var(--accent-blue)" }} />
            <span>Generation Progress</span>
            {running && <span className="live-pulse-badge">Live Step Execution</span>}
          </div>
          <div className="progress-percent-badge">{progressPercent}%</div>
        </div>

        {/* Dynamic Progress Bar */}
        <div className="progress-track">
          <div
            className={`progress-fill ${running ? "animated-stripes" : ""}`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="progress-caption">
          {running ? (
            <span className="caption-running">
              <Loader2 size={12} className="spinner" /> {currentStepLabel}
            </span>
          ) : progressPercent === 100 ? (
            <span className="caption-complete">
              <CheckCircle2 size={12} style={{ color: "var(--accent-green)" }} /> Page generation complete
            </span>
          ) : (
            <span className="caption-idle">Click "Run Pipeline" to generate page</span>
          )}
        </div>
      </div>

      {/* Step Cards Grid */}
      <div className="steps-container">
        {STEPS.map((step) => {
          const status = stepStatuses[step.id] || "pending";
          const StepIcon = step.icon;

          return (
            <div key={step.id} className={`step-card step-${status}`}>
              <div className="step-icon-col">
                {status === "completed" && (
                  <CheckCircle2 size={18} className="icon-completed" />
                )}
                {status === "running" && (
                  <Loader2 size={18} className="icon-running spinner" />
                )}
                {status === "error" && (
                  <AlertCircle size={18} className="icon-error" />
                )}
                {status === "pending" && (
                  <Circle size={18} className="icon-pending" />
                )}
              </div>

              <div className="step-content">
                <div className="step-header-line">
                  <span className="step-title">{step.title}</span>
                  <span className={`step-status-pill pill-${status}`}>
                    {status === "completed" && "Done"}
                    {status === "running" && "In Progress..."}
                    {status === "error" && "Failed"}
                    {status === "pending" && "Pending"}
                  </span>
                </div>
                <div className="step-desc">{step.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Optional Collapsible Raw Debug Console */}
      <div className="raw-console-toggle">
        <button
          type="button"
          className="console-toggle-btn"
          onClick={() => setShowRawConsole((v) => !v)}
        >
          <Terminal size={12} />
          <span>{showRawConsole ? "Hide Detailed Terminal Logs" : "View Detailed Terminal Logs"}</span>
          {showRawConsole ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {logs.length > 0 && (
          <button type="button" className="icon-btn-text" onClick={onClear} title="Clear raw logs">
            <Trash2 size={11} /> Clear
          </button>
        )}
      </div>

      {showRawConsole && (
        <div className="raw-console-box">
          {logs.length === 0 ? (
            <div className="raw-line sys">No terminal stream output yet.</div>
          ) : (
            logs.map((line, i) => (
              <div key={i} className="raw-line">
                {line}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
