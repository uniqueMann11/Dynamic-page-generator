"""
inject_viewer.py
================
Generates a role-specific hero viewer widget using the LLM (via generate_viwer.py)
and injects it directly into the right side of the hero section inside the target
HTML file.

The target HTML must contain a <div class="vw-ml-widget"> in the hero section.
The script:
  1. Calls the LLM (same logic as generate_viwer.py) to produce a fresh widget snippet.
  2. Parses the target HTML file with BeautifulSoup.
  3. Replaces the *inner HTML* of <div class="vw-ml-widget"> with the generated snippet.
     - If the snippet contains <style>...</style>, those are moved to the page <head>
       (injected just before </style> of the page, tagged with a comment so they can
       be replaced on subsequent runs without growing the file).
     - If the snippet contains <script>...</script>, they are moved to just before
       </body> similarly.
     - The remaining markup (no <style>/<script> wrappers) is set as the div's inner HTML.
  4. Writes the modified HTML back to the same file (or a --output path).

Usage:
  python inject_viewer.py --target location-page-mumbai.html \\
      --role "Machine Learning Engineer" --city "Mumbai" --state "Maharashtra"

  python inject_viewer.py --target hire-machine-learning-engineer-ahmedabad.html \\
      --role "Machine Learning Engineer" --city "Ahmedabad" --state "Gujarat" \\
      --model "openrouter/anthropic/claude-3.5-sonnet"

  # Skip LLM call, use an already-generated widget file:
  python inject_viewer.py --target location-page-mumbai.html --widget generated_components/interactive_viewer.html

  # Write to a different output (non-destructive):
  python inject_viewer.py --target location-page-mumbai.html \\
      --role "Machine Learning Engineer" --city "Mumbai" --state "Maharashtra" \\
      --output out/mumbai_with_widget.html
"""

import os
import sys
import argparse
import re

# UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import subprocess

def _pip_install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("beautifulsoup4 not found. Installing...")
    _pip_install("beautifulsoup4")
    from bs4 import BeautifulSoup

try:
    from lxml import etree  # noqa: F401
    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"

# Re-use generate_viwer.py for the LLM call
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from generate_viwer import load_dotenv, generate_viewer  # noqa: E402

# Sentinel comments used to tag injected blocks so re-runs replace rather than append
CSS_START = "<!-- [VIEWER-WIDGET-CSS:START] -->"
CSS_END   = "<!-- [VIEWER-WIDGET-CSS:END] -->"
JS_START  = "<!-- [VIEWER-WIDGET-JS:START] -->"
JS_END    = "<!-- [VIEWER-WIDGET-JS:END] -->"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_fence(html: str) -> str:
    """Remove accidental markdown code fences."""
    html = html.strip()
    if html.startswith("```"):
        lines = html.splitlines()
        start = 1 if lines[0].startswith("```") else 0
        end   = -1 if lines[-1].strip() == "```" else len(lines)
        html  = "\n".join(lines[start:end])
    return html.strip()


def _extract_blocks(html: str):
    """
    Split generated snippet into (style_text, script_text, body_html).
    Strips all CSS comments (/* ... */) from the extracted style text.
    """
    style_blocks  = re.findall(r"<style[^>]*>(.*?)</style>",  html, re.DOTALL | re.IGNORECASE)
    script_blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)

    body = re.sub(r"<style[^>]*>.*?</style>",   "", html, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<script[^>]*>.*?</script>",  "", body, flags=re.DOTALL | re.IGNORECASE)
    body = body.strip()

    css_text = "\n".join(style_blocks).strip()
    css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL).strip()

    return (
        css_text,
        "\n".join(script_blocks).strip(),
        body,
    )


def _remove_sentinel_block(raw: str, start_s: str, end_s: str) -> str:
    pattern = re.escape(start_s) + r".*?" + re.escape(end_s)
    return re.sub(pattern, "", raw, flags=re.DOTALL)


def _inject_css_into_head(page_html: str, css_text: str) -> str:
    if not css_text.strip():
        return page_html

    # Remove any previous sentinel blocks from earlier runs
    page_html = _remove_sentinel_block(page_html, CSS_START, CSS_END)

    block = f"\n{css_text}\n"

    # Insert before the last </style> inside <head>
    head_end = page_html.lower().find("</head>")
    search_area = page_html[:head_end] if head_end != -1 else page_html
    last_style_close = search_area.rfind("</style>")

    if last_style_close != -1:
        page_html = page_html[:last_style_close] + block + page_html[last_style_close:]
    else:
        if head_end != -1:
            page_html = page_html[:head_end] + f"<style>{block}</style>\n" + page_html[head_end:]

    return page_html


def _inject_js_before_body_end(page_html: str, js_text: str) -> str:
    if not js_text.strip():
        return page_html

    # Remove any previous sentinel blocks from earlier runs
    page_html = _remove_sentinel_block(page_html, JS_START, JS_END)

    block = f"\n<script>\n{js_text}\n</script>\n"

    body_end = page_html.rfind("</body>")
    if body_end != -1:
        page_html = page_html[:body_end] + block + page_html[body_end:]
    else:
        page_html += block

    return page_html


def _replace_widget_div(page_html: str, new_outer_html: str) -> str:
    """
    Find <div class="vw-ml-widget">...</div> using depth-tracking and replace
    the entire element with new_outer_html.
    """
    open_pattern = re.compile(
        r'<div\s[^>]*class="[^"]*\bvw-ml-widget\b[^"]*"[^>]*>',
        re.IGNORECASE
    )
    m = open_pattern.search(page_html)
    if not m:
        raise ValueError(
            'Could not locate <div class="vw-ml-widget"> in the HTML for replacement.'
        )

    start = m.start()
    pos   = m.end()
    depth = 1

    div_open  = re.compile(r"<div\b",    re.IGNORECASE)
    div_close = re.compile(r"</div\s*>", re.IGNORECASE)

    while pos < len(page_html) and depth > 0:
        next_open  = div_open.search(page_html,  pos)
        next_close = div_close.search(page_html, pos)

        if next_close is None:
            raise ValueError("Unbalanced <div> tags while scanning vw-ml-widget block.")

        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            pos = next_close.end()

    end = pos
    return page_html[:start] + new_outer_html + page_html[end:]


def inject_widget_into_html(page_html: str, widget_html: str) -> str:
    """
    Main injection function.
    1. Extract <style>/<script> from widget and inject into page head/body.
    2. Replace <div class="vw-ml-widget"> inner content with the widget body markup.
    Returns the updated HTML string.
    """
    widget_html = _strip_fence(widget_html)
    style_text, script_text, body_html = _extract_blocks(widget_html)

    # Guard: if the LLM wrapped its output in a vw-ml-widget div, unwrap it to
    # prevent double-nesting when we wrap it again below.
    _inner_check = BeautifulSoup(body_html, HTML_PARSER)
    _top = _inner_check.find("div", class_="vw-ml-widget")
    if _top is not None:
        body_html = _top.decode_contents()

    # Guard: if the body contains a vw-card whose parent is the root, also strip
    # any redundant outer vw-card-wrap containers that the LLM may have added.
    _inner_check2 = BeautifulSoup(body_html, HTML_PARSER)
    _top_card = _inner_check2.find("div", class_="vw-card")
    if _top_card and _top_card.parent and _top_card.parent.name == "[document]":
        # body_html is already clean \u2014 a bare vw-card is the root, nothing to strip
        pass

    # Step 1 & 2: inject CSS and JS via raw string manipulation
    page_html = _inject_css_into_head(page_html, style_text)
    page_html = _inject_js_before_body_end(page_html, script_text)

    # Step 3: use BeautifulSoup to build the new widget div HTML, then raw-replace
    soup = BeautifulSoup(f'<div class="vw-ml-widget">{body_html}</div>', HTML_PARSER)
    widget_div = soup.find("div", class_="vw-ml-widget")
    if widget_div is None:
        raise ValueError("Failed to parse the widget body HTML.")

    new_outer_html = str(widget_div)
    page_html = _replace_widget_div(page_html, new_outer_html)

    return page_html


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a role-specific hero viewer widget via LLM and inject it "
            "into <div class='vw-ml-widget'> inside the target HTML page."
        )
    )
    parser.add_argument("--target", type=str, required=True,
                        help="Path to the HTML file to update.")
    parser.add_argument("--role",   type=str, default="Machine Learning Engineer",
                        help="Professional role to theme the widget around.")
    parser.add_argument("--city",   type=str, default="Ahmedabad",
                        help="City name for local flavour.")
    parser.add_argument("--state",  type=str, default="Gujarat",
                        help="State name for local flavour.")
    parser.add_argument("--model",  type=str,
                        default="openrouter/meta-llama/llama-3.3-70b-instruct",
                        help="OpenRouter model to use for generation.")
    parser.add_argument("--widget", type=str, default=None,
                        help="Path to an already-generated widget HTML file (skips LLM).")
    parser.add_argument("--output", type=str, default=None,
                        help="Output path. Defaults to overwriting --target in-place.")
    args = parser.parse_args()

    target_path = os.path.abspath(args.target)
    if not os.path.exists(target_path):
        print(f"Error: Target file not found: {target_path}")
        sys.exit(1)

    output_path = os.path.abspath(args.output) if args.output else target_path

    load_dotenv()

    # --- Get widget HTML ---
    if args.widget:
        widget_file = os.path.abspath(args.widget)
        if not os.path.exists(widget_file):
            print(f"Error: Widget file not found: {widget_file}")
            sys.exit(1)
        with open(widget_file, "r", encoding="utf-8") as f:
            widget_html = f.read()
        print(f"\n  [OK] Using pre-generated widget: {widget_file}")
    else:
        if not os.environ.get("OPENROUTER_API_KEY"):
            print("Error: OPENROUTER_API_KEY not set in environment or .env file.")
            sys.exit(1)

        tmp_widget_path = os.path.join(
            BASE_DIR, "generated_components", "interactive_viewer.html"
        )
        generate_viewer(
            role        = args.role,
            city        = args.city,
            state       = args.state,
            model       = args.model,
            output_path = tmp_widget_path,
        )
        with open(tmp_widget_path, "r", encoding="utf-8") as f:
            widget_html = f.read()

    # --- Read target page ---
    with open(target_path, "r", encoding="utf-8") as f:
        page_html = f.read()

    print(f"\n{'='*60}")
    print(f"  Injecting widget into : {target_path}")
    print(f"  Output                : {output_path}")
    print(f"{'='*60}\n")

    try:
        updated_html = inject_widget_into_html(page_html, widget_html)
    except ValueError as e:
        print(f"\nError during injection:\n  {e}")
        sys.exit(1)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(updated_html)

    print(f"  [OK] Updated HTML written to: {output_path}\n")
    print(f"{'='*60}")
    print(f"  DONE  –  hero widget injected successfully.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
