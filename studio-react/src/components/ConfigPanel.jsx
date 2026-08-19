import { useState, useEffect } from "react";
import { Play, RotateCcw } from "lucide-react";
import { fetchPresets } from "../api.js";

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
  const [presets, setPresets] = useState([]);

  useEffect(() => {
    fetchPresets()
      .then((d) => setPresets(d.presets || []))
      .catch(() => {});
  }, []);

  function applyPreset(e) {
    const label = e.target.value;
    const p = presets.find((x) => x.label === label);
    if (!p) return;
    setForm((f) => ({
      ...f,
      city: p.city,
      state: p.state,
      geo_code: p.geo_code,
      landmarks: p.landmarks,
      dominentIindustries: p.dominentIindustries,
      output_filename: `location-page-${p.city.toLowerCase().replace(/ /g, "-")}.html`,
    }));
  }

  function set(key) {
    return (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  }
  function setCheck(key) {
    return (e) => setForm((f) => ({ ...f, [key]: e.target.checked }));
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
        {/* Presets */}
        <div className="panel-section">
          <div className="panel-section-title">City Preset</div>
          <div className="field">
            <label htmlFor="presetSelect">Quick fill</label>
            <select id="presetSelect" onChange={applyPreset} defaultValue="">
              <option value="" disabled>Select a city...</option>
              {presets.map((p) => (
                <option key={p.label} value={p.label}>{p.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Location fields */}
        <div className="panel-section">
          <div className="panel-section-title">Location</div>
          <div className="field">
            <label htmlFor="inputRole">Role</label>
            <input id="inputRole" value={form.role} onChange={set("role")} placeholder="Machine Learning Engineer" />
          </div>
          <div className="field">
            <label htmlFor="inputCity">City <span style={{color:"var(--accent-rose)"}}>*</span></label>
            <input id="inputCity" value={form.city} onChange={set("city")} placeholder="e.g. Gurgaon" required />
          </div>
          <div className="field">
            <label htmlFor="inputState">State <span style={{color:"var(--accent-rose)"}}>*</span></label>
            <input id="inputState" value={form.state} onChange={set("state")} placeholder="e.g. Haryana" required />
          </div>
          <div className="field">
            <label htmlFor="inputGeo">Geo Coordinates</label>
            <input id="inputGeo" value={form.geo_code} onChange={set("geo_code")} placeholder="lat,lng" />
          </div>
        </div>

        {/* Context fields */}
        <div className="panel-section">
          <div className="panel-section-title">Context</div>
          <div className="field">
            <label htmlFor="inputLandmarks">Landmarks</label>
            <textarea id="inputLandmarks" value={form.landmarks} onChange={set("landmarks")} placeholder="Key areas, landmarks..." />
          </div>
          <div className="field">
            <label htmlFor="inputIndustries">Dominant Industries</label>
            <textarea id="inputIndustries" value={form.dominentIindustries} onChange={set("dominentIindustries")} placeholder="Industries..." />
          </div>
        </div>

        {/* Model + output */}
        <div className="panel-section">
          <div className="panel-section-title">Generation</div>
          <div className="field">
            <label htmlFor="inputModel">AI Model</label>
            <select id="inputModel" value={form.model} onChange={set("model")}>
              <option value="openrouter/deepseek/deepseek-v4-flash">DeepSeek V4 Flash (fast)</option>
              <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
              <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
              <option value="gpt-4o">GPT-4o</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="inputOutput">Output Filename</label>
            <input id="inputOutput" value={form.output_filename} onChange={set("output_filename")} placeholder="Auto (location-page-{city}.html)" />
          </div>
        </div>

        {/* Toggles */}
        <div className="panel-section">
          <div className="panel-section-title">Options</div>
          <div className="toggle-row">
            <div className="toggle-left">
              <span className="toggle-label">Skip AI Generation</span>
              <span className="toggle-sub">Use existing JSON files</span>
            </div>
            <label className="toggle-switch">
              <input type="checkbox" checked={form.skip_generate} onChange={setCheck("skip_generate")} />
              <span className="toggle-slider" />
            </label>
          </div>
          <div className="toggle-row" style={{marginTop:"8px"}}>
            <div className="toggle-left">
              <span className="toggle-label">Skip Widget Injection</span>
              <span className="toggle-sub">Skip hero widget step</span>
            </div>
            <label className="toggle-switch">
              <input type="checkbox" checked={form.skip_widget} onChange={setCheck("skip_widget")} />
              <span className="toggle-slider" />
            </label>
          </div>
        </div>

        {/* Actions */}
        <div className="panel-section">
          <button type="submit" className="run-btn" disabled={running || !form.city || !form.state}>
            {running ? (
              <><div className="spinner" /> Running Pipeline...</>
            ) : (
              <><Play size={13} /> Run Pipeline</>
            )}
          </button>
          <button
            type="button"
            className="icon-btn"
            style={{width:"100%", justifyContent:"center", marginTop:"6px"}}
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
