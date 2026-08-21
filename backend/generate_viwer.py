"""
Hero Viewer Widget Generator via LLM
=====================================
Generates a role-specific visual widget to replace the interactive viewer
in the hero section. The widget should be thematically related to the role.

Examples:
  - Machine Learning Engineer  -> animated ML pipeline / model training widget
  - Web Developer              -> browser mockup / code editor widget
  - Data Analyst               -> live chart / metrics dashboard widget
  - DevOps Engineer            -> deployment pipeline / infra status widget

The output is a self-contained HTML snippet (with embedded <style> and optionally
<script>) that fits inside the existing .viewer container from location-page-template.html.

Usage:
  python generate_viwer.py --role "Machine Learning Engineer" --city "Ahmedabad" --state "Gujarat"
  python generate_viwer.py --role "Web Developer" --city "Mumbai" --state "Maharashtra"
  python generate_viwer.py --role "Data Analyst" --output generated_components/custom_viewer.html
"""

import os
import sys
import glob
import random
import argparse
import subprocess

# Ensure UTF-8 output formatting on Windows CMD/PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load .env automatically
def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

# Bootstrap LiteLLM
try:
    from litellm import completion
except ImportError:
    print("litellm not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "litellm"])
    from litellm import completion

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Design tokens (mirrors global_design_rules.json) ───────────────────────
DESIGN_TOKENS = """
.svcp {
  /* Core colors */

  --ink: #0A1222;
  --ink-soft: #1B2740;
  --body: #48566E;
  --muted: #6B7A93;

  --line: #E6ECF4;
  --line-soft: #EFF3F9;

  --surface: #FFFFFF;

  /* :root --surface-alt → .svcp --soft */
  --soft: #F4F8FD;

  /* :root --surface-tint → .svcp --tint */
  --tint: #EAF0FF;


  /* Primary blue */

  /* :root --primary → .svcp --blue */
  --blue: #2456E6;

  /* :root --primary-strong → .svcp --blue-strong */
  --blue-strong: #1740C0;

  /* :root --primary-tint → .svcp --blue-tint */
  --blue-tint: #E6EEFF;

  /* :root --green → .svcp --mint */
  --mint: #0FA968;

  /* :root --green-tint → .svcp --mint-tint */
  --mint-tint: #E4F7EE;

  --mint-deep: #0B7D4E;

  --amber: #D97A18;
  --amber-tint: #FCEFDD;

  --rose: #E11D48;


  /* :root --indigo has no direct .svcp equivalent */
  --indigo: #4F46E5;


  /* Shadows */

  /* :root --shadow-sm → .svcp --sh-sm */
  --sh-sm:
    0 1px 2px rgba(10, 18, 34, .04),
    0 2px 6px rgba(10, 18, 34, .05);

  /* :root --shadow-md → .svcp --sh-md */
  --sh-md:
    0 14px 34px -16px rgba(10, 18, 34, .22);

  /* :root --shadow-lg → .svcp --sh-lg */
  --sh-lg:
    0 30px 70px -28px rgba(36, 86, 230, .32);


  /* Radius */

  /* :root --radius → .svcp --r */
  --r: 18px;

  /* :root --radius-sm → .svcp --r-sm */
  --r-sm: 12px;


  /* Layout */

  --maxw: 1200px;


  /* Fonts */

  /* :root --ff-display → .svcp --disp */
  --disp: "Plus Jakarta Sans", system-ui, sans-serif;

  /* :root --ff-body → .svcp --bodyf */
  --bodyf: "Inter", system-ui, sans-serif;

  /* :root --ff-mono → .svcp --mono */
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}
"""

# ─── Existing .viewer CSS from the template (so LLM can see container shape) ─
VIEWER_CSS_CONTEXT = """
/* === Existing .viewer container styles (DO NOT redefine these) === */
.route-card{background:#fff;border:1px solid var(--line);border-radius:22px;padding:26px;box-shadow:var(--sh-md);position:relative}
.route-card::before{content:"DIRECT ACCESS";position:absolute;top:-11px;left:26px;background:var(--ink);color:#fff;font-family:var(--mono);font-size:.6rem;letter-spacing:.18em;padding:5px 11px;border-radius:6px}
.route-title{font-family:var(--mono);font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:18px}
.route{display:flex;flex-direction:column;gap:0}
.route-node{display:flex;align-items:center;gap:14px;padding:12px 0;position:relative}
.route-node .ico{width:42px;height:42px;border-radius:11px;display:grid;place-items:center;flex:0 0 auto}
.route-node .ico svg{width:21px;height:21px}
.route-node.me .ico{background:var(--blue);color:#fff}
.route-node.you .ico{background:var(--ink);color:#fff}
.route-node.other .ico{background:var(--soft);color:var(--muted)}
.route-node .txt b{display:block;font-family:var(--disp);font-size:1rem;color:var(--ink);font-weight:700}
.route-node .txt span{font-size:.82rem;color:var(--muted)}
.route-node .tag{margin-left:auto;font-family:var(--mono);font-size:.64rem;letter-spacing:.08em;padding:5px 9px;border-radius:6px}
.route-node.me .tag{background:var(--blue-tint);color:var(--blue-strong)}
.route-node.other .tag{background:var(--soft);color:var(--muted)}
.route-connector{width:2px;height:16px;background:linear-gradient(var(--blue),rgba(36,86,230,.15));margin-left:20px}
.route-foot{margin-top:18px;padding-top:16px;border-top:1px dashed var(--line);display:flex;justify-content:space-between;font-size:.8rem}
.route-foot b{color:var(--ink);font-family:var(--disp)}
/* ================================================================= */
"""

SYSTEM_PROMPT = """
You are a senior Frontend Engineer and Creative UI Developer specializing in high-quality, role-specific hero-section widgets.

You will be given an EXAMPLE WIDGET — a complete, working HTML widget file.
Your job is to generate a NEW widget that:
  1. Is adapted to the TARGET ROLE, city, state, and local industries provided.
  2. Follows the SAME structural layout, component hierarchy, class-naming conventions (.vw-*), dimensions, typography scale, spacing scale, and responsive breakpoints as the example widget.
  3. Keeps all interactive mechanics (sliders, tabs, clickable steps, live metrics, log outputs, etc.) from the example widget, but rewrites all labels, values, descriptions, simulations, and logic to match the target role.

DIMENSION RULES — CRITICAL:
- The generated widget MUST match the example widget's `.vw-card` max-width (520px), card border-radius (var(--r) or var(--r-sm)), padding, and internal component heights exactly.
- Do NOT add new wrapper containers or alter the top-level card structure.
- Do NOT change the overall widget height or introduce scroll overflow.
- Preserve every @media breakpoint from the example exactly (e.g. @media (max-width: 480px)).

STYLE RULES:
- Use ONLY the CSS custom properties from the DESIGN TOKENS:
    Core colors: var(--ink), var(--ink-soft), var(--body), var(--muted)
    Borders/Lines: var(--line), var(--line-soft)
    Surfaces: var(--surface), var(--soft), var(--tint)
    Primary blue: var(--blue), var(--blue-strong), var(--blue-tint)
    Accents: var(--mint), var(--mint-tint), var(--mint-deep), var(--amber), var(--amber-tint), var(--violet), var(--violet-tint), var(--rose), var(--indigo)
    Shadows: var(--sh-sm), var(--sh-md), var(--sh-lg)
    Radius: var(--r) [18px], var(--r-sm) [12px]
    Fonts: var(--disp) ["Plus Jakarta Sans"], var(--bodyf) ["Inter"], var(--mono) ["IBM Plex Mono"]
- Fonts available on the parent page: "Plus Jakarta Sans" (display: var(--disp)), "Inter" (body: var(--bodyf)), "IBM Plex Mono" (mono: var(--mono)).
- Do NOT use old tokens like --primary, --green, --ff-display, --ff-body, --ff-mono, --radius, --shadow-md.
- Do NOT define or import any font that is not already listed.
- Do NOT redefine :root or .svcp custom properties — they are inherited from the parent page.
- Your CSS class names MUST start with `.vw-` to avoid collisions with the parent page.
- Do NOT write any CSS comments (/* ... */) or HTML comments in your output. Write clean code only.
- don't generate any of style for the body or any other parent class.

STRUCTURE RULES:
- The output must be a self-contained snippet starting directly with `<style>` and ending after the closing script or markup.
- Do NOT wrap in `<html>`, `<body>`, `<head>`, or any standalone page boilerplate.
- Do NOT include the :root block or font `<link>` tags — those are already on the parent page.
- The snippet will be injected inside `<div class="vw-ml-widget">` on the parent page.

INTERACTION RULES:
- The widget MUST contain at least ONE genuine user interaction.
- Interaction means the user must be able to click, hover, toggle, select, drag, or otherwise manipulate something and see a visible change.
- Do NOT consider automatic animation alone to be interaction.
- All interactions must use only vanilla JS, work entirely in the browser, and require no external libraries or APIs.
- Interactions must remain usable on mobile touch screens.

LOCAL CONTEXT RULES:
- City and state are contextual flavour only — never evidence of completed projects or clients.
- Allowed: "Serving {city} & {state}", "{city} • {state}", "Built for teams in {city}".
- NOT allowed: "42 {city} projects", "100+ {city} clients".
- Dominant industries may be woven into example data labels (e.g. a demand forecasting widget can reference the city's top industry).

FACTUAL CLAIMS:
- Never invent client counts, project counts, revenue, years of experience, certifications, awards, or testimonials.
- If a metric is needed visually, use a non-claiming technical value, process state, or symbolic label.

OUTPUT RULES:
- Output ONLY the raw HTML snippet. Start directly with `<style>`.
- No markdown fences, no explanations, no surrounding page boilerplate.
"""

def get_sample_widgets(widgets_dir: str) -> list:
    pattern = os.path.join(widgets_dir, "*.html")
    all_files = glob.glob(pattern)
    return [f for f in all_files if os.path.basename(f).lower() != "index.html"]


def select_sample_widget(widgets_dir: str, specific_widget: str = None) -> tuple:
    if specific_widget:
        path = os.path.join(widgets_dir, specific_widget)
        if not os.path.exists(path):
            path = specific_widget
        if not os.path.exists(path):
            raise FileNotFoundError(f"Specified sample widget not found: {specific_widget}")
    else:
        candidates = get_sample_widgets(widgets_dir)
        if not candidates:
            return None, None
        path = random.choice(candidates)
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    return os.path.basename(path), code


def generate_viewer(
    role: str,
    city: str,
    state: str,
    model: str,
    output_path: str,
    geo_code: str = None,
    landmarks: str = None,
    dominent_industries: str = None,
    sample_widget_path: str = None,
):
    print(f"\n{'='*60}")
    print(f"  Generating role-specific hero viewer widget")
    print(f"  Role  : {role}")
    print(f"  City  : {city}, {state}")
    print(f"  Model : {model}")
    print(f"{'='*60}\n")

    widgets_dir = os.path.join(BASE_DIR, "widgets")
    sample_name, sample_code = select_sample_widget(widgets_dir, sample_widget_path)

    if sample_name:
        print(f"  Sample widget selected: {sample_name}")
    else:
        print("  No sample widgets found — generating from scratch.")
        sample_code = ""
        sample_name = "(none)"

    context_lines = [
        f"ROLE      : {role}",
        f"CITY      : {city}",
        f"STATE     : {state}",
    ]
    if geo_code:
        context_lines.append(f"GEO CODE  : {geo_code}")
    if landmarks:
        context_lines.append(f"LANDMARKS : {landmarks}")
    if dominent_industries:
        context_lines.append(f"DOMINANT INDUSTRIES: {dominent_industries}")
    context_block = "\n".join(context_lines)

    if sample_code:
        example_block = f"""
EXAMPLE WIDGET (use this as your structural and dimensional blueprint — adapt all content to the target role):
<example>
{sample_code}
</example>

INSTRUCTIONS:
- Mirror the example widget's layout structure, component nesting, class hierarchy, `.vw-card` max-width (520px), paddings, font sizes, and @media breakpoints exactly.
- Replace every label, metric, step name, log message, description, and simulation with equivalents that make sense for "{role}".
- Keep all interactive mechanics intact (e.g. sliders, tabs, click events, live-updating intervals) but re-theme their labels, values, and calculations for the role.
- Do NOT include the :root block — CSS variables are inherited from the parent page.
- Do NOT include font <link> tags — fonts are already loaded on the parent page.
- Do NOT wrap output in <html>, <head>, or <body> tags.
- Output starts directly with <style>.
"""
    else:
        example_block = f"""
No example widget available. Generate a fresh, premium widget thematically tied to "{role}".

Design brief for Machine Learning Engineer:
  - Animated pipeline nodes, faux training terminal, live accuracy/loss metrics, or mini chart drawn with SVG.
  - Widget card max-width: 520px. Use .vw-card as the root class.
  - Do NOT include :root or font <link> tags.
  - Output starts directly with <style>.
"""

    user_prompt = f"""
Generate a premium, thematic hero-section widget for:

{context_block}

DESIGN TOKENS (CSS variables already declared on the parent page — reference only, do NOT redefine):
{DESIGN_TOKENS}

EXISTING VIEWER CSS CONTEXT (do NOT redefine these classes):
{VIEWER_CSS_CONTEXT}

{example_block}
Reference {city} lightly for local flavour (e.g. in a status caption or metric label) using the city and dominant industries as context.
Do not use any emoji. Make it professional and premium. Ensure spacing and font usage is consistent throughout.
"""

    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ]
    )

    html = response.choices[0].message.content.strip()

    # Strip accidental markdown fences
    if html.startswith("```"):
        lines = html.splitlines()
        start = 1 if lines[0].startswith("```") else 0
        end   = -1 if lines[-1].strip() == "```" else len(lines)
        html  = "\n".join(lines[start:end])

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  [OK] Widget saved to: {os.path.abspath(output_path)}\n")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate a role-specific hero viewer widget using an LLM."
    )
    parser.add_argument("--role",   type=str, default="Machine Learning Engineer",
                        help="Professional role to theme the widget around.")
    parser.add_argument("--city",   type=str, default="Ahmedabad",
                        help="City name for local flavour.")
    parser.add_argument("--state",  type=str, default="Gujarat",
                        help="State name for local flavour.")
    parser.add_argument("--geo-code", type=str, default=None,
                        help="ISO 3166-2 geo code (e.g. IN-GJ).")
    parser.add_argument("--landmarks", type=str, default=None,
                        help="Comma-separated local landmarks for context.")
    parser.add_argument("--dominent-industries", type=str, default=None,
                        help="Comma-separated dominant industries in the city/state.")
    parser.add_argument("--sample-widget", type=str, default=None,
                        help="Filename of a specific widget in widgets/ to use as blueprint (random if omitted).")
    parser.add_argument("--model",  type=str,
                        default="openrouter/meta-llama/llama-3.3-70b-instruct",
                        help="OpenRouter model to use.")
    parser.add_argument("--output", type=str,
                        default="generated_components/interactive_viewer.html",
                        help="Output file path for the generated widget HTML.")
    args = parser.parse_args()

    load_dotenv()

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY not set in environment or .env file.")
        sys.exit(1)

    generate_viewer(
        role                = args.role,
        city                = args.city,
        state               = args.state,
        geo_code            = args.geo_code,
        landmarks           = args.landmarks,
        dominent_industries = args.dominent_industries,
        sample_widget_path  = args.sample_widget,
        model               = args.model,
        output_path         = args.output,
    )


if __name__ == "__main__":
    main()
