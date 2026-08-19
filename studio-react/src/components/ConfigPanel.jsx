import { useState } from "react";
import { Play, RotateCcw } from "lucide-react";

const DEFAULTS = {
  role: "Machine Learning Engineer",
  city: "",
  state: "",
  geo_code: "",
  landmarks: "",
  dominentIindustries: "",
  model: "openrouter/deepseek/deepseek-v4-flash",
  output_filename: "",
  skip_generate: false,
  skip_widget: false,
};

export default function ConfigPanel({ running, onRun }) {
  const [form, setForm] = useState(DEFAULTS);

  function set(key) {
    return (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!form.city || !form.state) return;
    onRun(form);
  }

  function reset(e) {
    e.preventDefault();
    setForm(DEFAULTS);
  }

  return (
    <aside className="config-panel">
      <form onSubmit={handleSubmit}>
        {/* Location fields */}
        <div className="panel-section">
          <div className="panel-section-title">Location</div>
          <div className="field">
            <label htmlFor="inputRole">Role</label>
            <input
              id="inputRole"
              value={form.role}
              onChange={set("role")}
              placeholder="Machine Learning Engineer"
            />
          </div>
          <div className="field">
            <label htmlFor="inputCity">
              City <span style={{ color: "var(--accent-rose)" }}>*</span>
            </label>
            <input
              id="inputCity"
              value={form.city}
              onChange={set("city")}
              placeholder="e.g. Jaipur"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="inputState">
              State <span style={{ color: "var(--accent-rose)" }}>*</span>
            </label>
            <input
              id="inputState"
              value={form.state}
              onChange={set("state")}
              placeholder="e.g. Rajasthan"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="inputGeo">Geo Coordinates</label>
            <input
              id="inputGeo"
              value={form.geo_code}
              onChange={set("geo_code")}
              placeholder="lat,lng (e.g. 26.9124,75.7873)"
            />
          </div>
        </div>

        {/* Context fields */}
        <div className="panel-section">
          <div className="panel-section-title">Context</div>
          <div className="field">
            <label htmlFor="inputLandmarks">Landmarks</label>
            <textarea
              id="inputLandmarks"
              value={form.landmarks}
              onChange={set("landmarks")}
              placeholder="Key areas, tech parks, landmarks..."
            />
          </div>
          <div className="field">
            <label htmlFor="inputIndustries">Dominant Industries</label>
            <textarea
              id="inputIndustries"
              value={form.dominentIindustries}
              onChange={set("dominentIindustries")}
              placeholder="Key local industries..."
            />
          </div>
        </div>

        {/* Actions */}
        <div className="panel-section">
          <button
            type="submit"
            className="run-btn"
            disabled={running || !form.city || !form.state}
          >
            {running ? (
              <>
                <div className="spinner" /> Running Pipeline...
              </>
            ) : (
              <>
                <Play size={13} /> Run Pipeline
              </>
            )}
          </button>
          <button
            type="button"
            className="icon-btn"
            style={{ width: "100%", justifyContent: "center", marginTop: "6px" }}
            onClick={reset}
            disabled={running}
          >
            <RotateCcw size={12} /> Reset Form
          </button>
        </div>
      </form>
    </aside>
  );
}
