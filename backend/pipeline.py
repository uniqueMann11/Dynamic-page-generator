"""
Full Website Generation Pipeline
=================================
Reads actual_data + rules for each section, sends them to an LLM via OpenRouter,
stores generated JSON in generated/, then compiles the final HTML page with
city/state/geo_code placeholder replacement.

Usage:
  python pipeline.py --role "Machine Learning Engineer" --city "Ahmedabad" --state "Gujarat" --geo-code "IN-GJ" --landmarks "Sabarmati Riverfront, GIFT City" --dominentIindustries "IT, Textiles, Pharmaceuticals"
"""

import os
import re
import sys
import json
import argparse
import subprocess

# Ensure UTF-8 output formatting on Windows CMD/PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── dependency bootstrap ──────────────────────────────────────────────────────
from litellm import completion

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("beautifulsoup4 not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# Viewer widget generation & injection modules
from generate_viwer import generate_viewer
from inject_viewer import inject_widget_into_html

# ── paths ─────────────────────────────────────────────────────────────────────
IS_VERCEL = "VERCEL" in os.environ or "AWS_LAMBDA_FUNCTION_NAME" in os.environ

if IS_VERCEL:
    import tempfile
    WORK_TMP = tempfile.gettempdir()
    GENERATED_DIR = os.path.join(WORK_TMP, "generated")
    HTML_PAGES_DIR = os.path.join(WORK_TMP, "HTML pages")
else:
    GENERATED_DIR = os.path.join(BASE_DIR, "generated")
    HTML_PAGES_DIR = os.path.join(BASE_DIR, "HTML pages")

ACTUAL_DATA_DIR = os.path.join(BASE_DIR, "actual_data")
RULES_DIR = os.path.join(BASE_DIR, "rules")
os.makedirs(HTML_PAGES_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

# Prefer new template: hire-machine-learning-engineer-ahmedabad copy.html
TEMPLATE_PATH = os.path.join(BASE_DIR, "hire-machine-learning-engineer-ahmedabad copy.html")
if not os.path.exists(TEMPLATE_PATH):
    TEMPLATE_PATH = os.path.join(ROOT_DIR, "hire-machine-learning-engineer-ahmedabad copy.html")
if not os.path.exists(TEMPLATE_PATH):
    TEMPLATE_PATH = os.path.join(BASE_DIR, "hire-machine-learning-engineer-ahmedabad.html")
if not os.path.exists(TEMPLATE_PATH):
    TEMPLATE_PATH = os.path.join(ROOT_DIR, "hire-machine-learning-engineer-ahmedabad.html")
if not os.path.exists(TEMPLATE_PATH):
    TEMPLATE_PATH = os.path.join(HTML_PAGES_DIR, "location-page-template.html")

# The four sections in order — each entry maps:
#   data file name  ->  rules file name  ->  generated output name
SECTIONS = [
    {"name": "Hero Section", "data": "hero.json", "rules": "hero_rules.json", "output": "new_hero.json"},
    {"name": "Value & Quick Answer", "data": "second_hero.json", "rules": "second_hero_rules.json", "output": "new_second_hero.json"},
    {"name": "Services & Local Context", "data": "third_section.json", "rules": "third_section_rules.json", "output": "new_third_section.json"},
    {"name": "Process, Case Studies & FAQ", "data": "final_section.json", "rules": "final_section_rules.json", "output": "new_final_section.json"},
]

# ── .env loader ───────────────────────────────────────────────────────────────
def load_dotenv():
    env_path = os.path.join(ROOT_DIR, ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

# ── LLM content generation ───────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are an expert website content strategist, SEO copywriter, and conversion copywriter specializing in premium personal brand service websites.

Your responsibility is NOT to simply rewrite text.

Your responsibility is to regenerate the website content so it becomes a completely new website for a different professional role while preserving the original website structure.

You have to generate the data according the city, state and Geo Code (ISO 3166-2:IN) given also be given the search keywords to use for SEO optimization purpose.

You also be given the Dominent Industries in that city/state. You have to make content that tries to target those industries.

The JSON structure represents the architecture of the website, not the content itself.

Treat every section as an independent business section with its own purpose.

Giving the local industries in that area you have to make content that tries to target those industries.

Examples:
- Hero introduces the professional and value proposition.
- Services describe the actual services offered.
- Consulting explains advisory offerings.
- Comparison explains competitive positioning.
- Process explains the workflow.
- Case studies demonstrate relevant work.
- FAQ answers objections for that profession.
- CTA motivates visitors to contact the professional.

When the target profession changes, ALL profession-dependent content must also change.

Do NOT perform simple keyword substitution.
Do NOT change any link or hyperlink keep them as it is.

Instead, regenerate every value so it naturally fits the target profession.

Keep only:
- JSON structure
- Website architecture
- Section purpose
- Writing quality
- Tone
- Overall conversion strategy

Never invent new JSON keys.
Never remove existing JSON keys.
Never rename keys.
Never change nesting.
Only modify values.
Follow every constraint described in the provided Rules JSON.
Add data in placeholders as given.

Output must be ONLY valid JSON.
No markdown.
No explanations.
No comments.
No extra text.
"""


def generate_section(role, city, state, geo_code, landmarks, dominentIindustries, model, data_path, rules_path, output_path, step_num=1, total_steps=4, section_title="Section"):
    """Send one section through the LLM and save the result."""
    section_name = os.path.basename(data_path)
    print(f"[STEP {step_num}/{total_steps}] Generating {section_title} for {city}...")

    with open(data_path, "r", encoding="utf-8") as f:
        original_content = json.load(f)
    with open(rules_path, "r", encoding="utf-8") as f:
        rules_content = json.load(f)

    prompt = f"""
Target Role
{role}

City
{city}

State
{state}

Geo Code
{geo_code}

Landmarks
{landmarks}

Dominent Industries
{dominentIindustries}

Original Website JSON
{json.dumps(original_content, indent=2)}

Description JSON
{json.dumps(rules_content, indent=2)}

Return ONLY valid JSON.
"""

    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()

        # Clean markdown fences if model ignored response_format
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                content = "\n".join(lines[1:-1])

        new_data = json.loads(content)

        # --- Fix double-encoded JSON responses from LLM ---
        if isinstance(new_data, dict) and len(new_data) == 1:
            only_key = list(new_data.keys())[0]
            only_val = new_data[only_key]
            if isinstance(only_val, str):
                try:
                    unwrapped = json.loads(only_val)
                    if isinstance(unwrapped, dict) and len(unwrapped) > 0:
                        print(f"  [FIX] Unwrapped double-encoded JSON (key was: {repr(only_key)})")
                        new_data = unwrapped
                except (json.JSONDecodeError, ValueError):
                    pass

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2)

        print(f"[OK] Step {step_num}/{total_steps} complete: {section_title}")
        return new_data

    except Exception as e:
        print(f"  [ERROR] Error generating {section_name}: {e}")
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                fb_data = json.load(f)
            raw = json.dumps(fb_data)
            KNOWN_CITIES = ["Ahmedabad", "Bangalore", "Chennai", "Delhi", "Gurgaon", "Hyderabad", "Kolkata", "Mumbai", "Noida", "Pune", "Kochi"]
            for c in KNOWN_CITIES:
                if c.lower() != city.lower():
                    raw = raw.replace(c, city)
            raw = raw.replace("{{CITY}}", city).replace("{{STATE}}", state)
            new_data = json.loads(raw)
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2)
            print(f"  [FALLBACK] Created city-customized section data for {city} -> {output_path}")
            return new_data
        except Exception as fb_err:
            print(f"  [ERROR] Fallback failed for {section_name}: {fb_err}")
            return None


# ── Helper text updater for BeautifulSoup elements ─────────────────────────────
def _set_text(el, text):
    if el and text is not None:
        el.string = str(text)

def _set_href(el, url):
    if el and url:
        el["href"] = str(url)

def _update_prose_paragraphs(prose_el, p_data, soup):
    """
    Updates the <p> elements within a container (.prose, .tldr, etc.).
    Handles matching count, adding new <p> tags if data has more items,
    and deleting/decomposing any excess <p> tags if data has fewer items.
    """
    if not prose_el or p_data is None:
        return
    if isinstance(p_data, str):
        p_list = [p_data]
    elif isinstance(p_data, list):
        p_list = p_data
    elif isinstance(p_data, dict):
        p_list = p_data.get("p", [])
        if isinstance(p_list, str):
            p_list = [p_list]
    else:
        p_list = []

    p_els = prose_el.find_all("p", recursive=False)
    if not p_els:
        p_els = prose_el.find_all("p")

    for i, p_text in enumerate(p_list):
        if i < len(p_els):
            p_els[i].string = str(p_text)
        else:
            new_p = soup.new_tag("p")
            new_p.string = str(p_text)
            checklist = prose_el.find(class_="checklist")
            if checklist:
                checklist.insert_before(new_p)
            else:
                prose_el.append(new_p)

    for i in range(len(p_list), len(p_els)):
        p_els[i].decompose()


# ── Template constants (the hardcoded values in the template file) ────────────
TEMPLATE_CITY  = "Ahmedabad"
TEMPLATE_STATE = "Gujarat"
TEMPLATE_ROLE  = "Machine Learning Engineer"


# ── Meta & JSON-LD updater ────────────────────────────────────────────────────
def _update_meta_and_jsonld(soup, role, city, state):
    """
    Update all <meta> tags (SEO, OG, Twitter), <title>, <link rel=canonical>,
    and <script type=application/ld+json> structured data to reflect the
    new role, city and state.
    """
    old_city  = TEMPLATE_CITY
    old_state = TEMPLATE_STATE
    old_role  = TEMPLATE_ROLE

    old_slug  = old_city.lower().replace(" ", "-")
    new_slug  = city.lower().replace(" ", "-")

    old_role_slug = old_role.lower().replace(" ", "-")
    new_role_slug = role.lower().replace(" ", "-")

    def _swap(text):
        if not text:
            return text
        text = text.replace(old_city, city)
        text = text.replace(old_state, state)
        text = text.replace(old_role, role)
        text = text.replace(old_slug, new_slug)
        text = text.replace(old_role_slug, new_role_slug)
        return text

    head = soup.find("head")
    if not head:
        print("  ⚠ No <head> found — skipping meta/JSON-LD update.")
        return

    # 1. <title>
    title_el = head.find("title")
    if title_el and title_el.string:
        title_el.string = _swap(title_el.string)

    # 2. <meta> tags
    for meta in head.find_all("meta"):
        for attr in ("content",):
            val = meta.get(attr)
            if val:
                meta[attr] = _swap(val)

    # 3. <link rel="canonical">
    canon = head.find("link", rel="canonical")
    if canon and canon.get("href"):
        canon["href"] = _swap(canon["href"])

    # 4. <script type="application/ld+json">
    for script in head.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            ld = json.loads(script.string)
        except json.JSONDecodeError:
            print("  ⚠ Could not parse JSON-LD — skipping.")
            continue

        def _walk(obj):
            if isinstance(obj, dict):
                return {k: _walk(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_walk(item) for item in obj]
            elif isinstance(obj, str):
                return _swap(obj)
            return obj

        ld = _walk(ld)

        graph = ld.get("@graph", [])
        for node in graph:
            ntype = node.get("@type", "")
            if ntype == "ProfessionalService":
                for area in node.get("areaServed", []):
                    if area.get("@type") == "City":
                        area["name"] = city
                    elif area.get("@type") == "State":
                        area["name"] = state
                addr = node.get("address", {})
                if addr:
                    addr["addressLocality"] = city
                    addr["addressRegion"] = state
                founder = node.get("founder", {})
                if founder:
                    founder["jobTitle"] = role

        script.string = json.dumps(ld, indent=2, ensure_ascii=False)

    print("  ✓ Meta tags & JSON-LD updated.")


# ── HTML compilation ─────────────────────────────────────────────────────────
def compile_html(role, city, state, geo_code, landmarks, dominent_industries, output_path):
    """Load all generated JSONs and compile into the final HTML page using exact CSS classes."""
    print(f"\n{'='*60}")
    print(f"  Compiling HTML -> {output_path}")
    print(f"  Role: {role}  |  City: {city}  |  State: {state}")
    print(f"{'='*60}")

    hero_path = os.path.join(GENERATED_DIR, "new_hero.json")
    second_path = os.path.join(GENERATED_DIR, "new_second_hero.json")
    third_path = os.path.join(GENERATED_DIR, "new_third_section.json")
    final_path = os.path.join(GENERATED_DIR, "new_final_section.json")

    KNOWN_CITIES = ["Ahmedabad", "Bangalore", "Chennai", "Delhi", "Gurgaon", "Hyderabad", "Kolkata", "Mumbai", "Noida", "Pune", "Kochi"]

    def load_json(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Fix double-encoded JSON (LLM sometimes wraps output in a string)
                if isinstance(data, dict) and len(data) == 1:
                    only_key = list(data.keys())[0]
                    only_val = data[only_key]
                    if isinstance(only_val, str):
                        try:
                            unwrapped = json.loads(only_val)
                            if isinstance(unwrapped, dict) and len(unwrapped) > 0:
                                print(f"  [FIX] Unwrapped double-encoded JSON in {os.path.basename(path)}")
                                data = unwrapped
                        except (json.JSONDecodeError, ValueError):
                            pass

                raw = json.dumps(data)
                for c in KNOWN_CITIES:
                    if c.lower() != city.lower():
                        raw = raw.replace(c, city)
                raw = raw.replace("{{CITY}}", city).replace("{{STATE}}", state)
                return json.loads(raw)
        except FileNotFoundError:
            print(f"  Warning: {path} not found. Skipping.")
            return None

    hero_data = load_json(hero_path)
    second_data = load_json(second_path)
    third_data = load_json(third_path)
    final_data = load_json(final_path)

    if not hero_data:
        print("  Error: Hero JSON is required. Cannot compile.")
        return

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # ─────────────────────────────────────────────────────────────
    # 1. HERO SECTION (from new_hero.json)
    # ─────────────────────────────────────────────────────────────
    hero_sec = soup.find("section", id="demo") or soup.find("section", class_="hero")
    if hero_sec and "hero" in hero_data:
        hd = hero_data["hero"]

        # eyebrow
        _set_text(hero_sec.find("p", class_="eyebrow"), hd.get("eyebrow"))

        # h1 (supports h1-text + span/em)
        h1_el = hero_sec.find("h1")
        if h1_el and "h1" in hd:
            h1_data = hd["h1"]
            if isinstance(h1_data, dict):
                h1_el.clear()
                if "h1-text" in h1_data:
                    h1_el.append(str(h1_data["h1-text"]) + " ")
                if "span" in h1_data:
                    span_tag = soup.new_tag("span")
                    span_tag.string = str(h1_data["span"])
                    h1_el.append(span_tag)
                elif "em" in h1_data:
                    span_tag = soup.new_tag("span")
                    span_tag.string = str(h1_data["em"])
                    h1_el.append(span_tag)
                if "h1-suffix" in h1_data:
                    h1_el.append(str(h1_data["h1-suffix"]))
            else:
                h1_el.string = str(h1_data)

        # hero-sub
        _set_text(hero_sec.find(class_="hero-sub"), hd.get("hero-sub"))

        # creds (new template)
        creds_container = hero_sec.find(class_="creds")
        if creds_container and "creds" in hd:
            cred_els = creds_container.find_all(class_="cred")
            for i, cred_entry in enumerate(hd["creds"]):
                if i < len(cred_els):
                    c_info = cred_entry.get("cred", cred_entry)
                    t_box = cred_els[i].find(class_="t")
                    if t_box:
                        if "i" in c_info:
                            _set_text(t_box.find("i"), c_info["i"])
                        if "b" in c_info:
                            _set_text(t_box.find("b"), c_info["b"])

        # hero-stats (legacy fallback)
        stats_container = hero_sec.find(class_="hero-stats")
        if stats_container and "hero-stats" in hd:
            chips = stats_container.find_all(class_="stat-chip")
            for i, chip_data in enumerate(hd["hero-stats"]):
                if i < len(chips):
                    c_dict = chip_data.get("stat-chip", chip_data)
                    b_el = chips[i].find("b")
                    span_el = chips[i].find("span")
                    if b_el and "b" in c_dict:
                        b_el.string = str(c_dict["b"])
                    if span_el and "span" in c_dict:
                        span_el.string = str(c_dict["span"])

        # hero-cta / hero-actions
        cta_container = hero_sec.find(class_="hero-cta") or hero_sec.find(class_="hero-actions")
        hero_acts = hd.get("hero-cta") or hd.get("hero-actions") or []
        if cta_container and hero_acts:
            btns = cta_container.find_all("a", class_="btn")
            for i, btn_entry in enumerate(hero_acts):
                if i < len(btns):
                    btn_el = btns[i]
                    b_info = btn_entry.get("btn-primary") or btn_entry.get("btn--primary") or btn_entry.get("btn-ghost") or btn_entry.get("btn--ghost") or btn_entry
                    if isinstance(b_info, dict):
                        svg = btn_el.find("svg")
                        btn_el.clear()
                        btn_el.append(str(b_info.get("text", "")))
                        if svg:
                            btn_el.append(" ")
                            btn_el.append(svg)
                        if "url" in b_info:
                            btn_el["href"] = str(b_info["url"])

        # live / hero-note
        live_el = hero_sec.find(class_="live") or hero_sec.find(class_="hero-note")
        live_text = hd.get("live") or hd.get("hero-note")
        if live_el and live_text:
            pulse = live_el.find(class_="pulse") or live_el.find("svg")
            live_el.clear()
            if pulse:
                live_el.append(pulse)
                live_el.append(" ")
            live_el.append(str(live_text))

    print("  ✓ Hero section applied.")

    # ─────────────────────────────────────────────────────────────
    # 2. SECOND HERO (from new_second_hero.json)
    # ─────────────────────────────────────────────────────────────
    if second_data:
        # why-direct (value-strip)
        why_sec = soup.find("section", id="why-direct") or soup.find("section", class_=lambda c: c and "value-strip" in c) or (soup.find(class_="value-grid").find_parent("section") if soup.find(class_="value-grid") else None)
        v_data = second_data.get("why-direct") or second_data.get("value-strip") or second_data.get("value_strip_section")
        if why_sec and v_data:
            sec_head = why_sec.find(class_="sec-head") or why_sec.find(class_="center")
            sh_data = v_data.get("sec-head") or v_data.get("center") or v_data
            if sec_head:
                _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
                _set_text(sec_head.find("h2"), sh_data.get("h2"))

            cards = why_sec.find_all(class_="value-card")
            v_grid = v_data.get("grid g4") or v_data.get("value-grid") or []
            for i, card_entry in enumerate(v_grid):
                if i < len(cards):
                    c_info = card_entry.get("value-card", card_entry)
                    _set_text(cards[i].find("h3"), c_info.get("h3"))
                    _set_text(cards[i].find("p"), c_info.get("p"))

        # what-is (quick-answer)
        what_sec = soup.find("section", id="what-is") or soup.find("section", class_=lambda c: c and "quick-answer" in c) or (soup.find(class_="tldr").find_parent("section") if soup.find(class_="tldr") else None)
        q_data = second_data.get("what-is") or second_data.get("quick-answer") or second_data.get("plain_answer_section")
        if what_sec and q_data:
            sec_head = what_sec.find(class_="sec-head")
            sh_data = q_data.get("sec-head") or q_data.get("prose-grid") or q_data
            if sec_head:
                _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
                _set_text(sec_head.find("h2"), sh_data.get("h2"))

            tldr_el = what_sec.find(class_="tldr") or what_sec.find(class_="answer-card")
            if tldr_el:
                t_data = q_data.get("tldr") or q_data.get("answer-card") or {}
                if "b" in t_data:
                    _set_text(tldr_el.find("b"), t_data["b"])
                if "tag" in t_data:
                    _set_text(tldr_el.find(class_="tag"), t_data["tag"])

                p_list = t_data.get("p", []) if isinstance(t_data, dict) else []
                if not p_list and "prose" in q_data:
                    p_list = q_data["prose"].get("p", [])
                if p_list:
                    _update_prose_paragraphs(tldr_el, p_list, soup)

        print("  ✓ Second hero section applied.")

    # ─────────────────────────────────────────────────────────────
    # 3. THIRD SECTION (from new_third_section.json)
    # ─────────────────────────────────────────────────────────────
    if third_data:
        # services (what-I-build)
        svc_sec = soup.find("section", id="services") or soup.find("section", class_=lambda c: c and ("what-I-build" in c or "what_i_build" in c)) or (soup.find(class_="svc-grid").find_parent("section") if soup.find(class_="svc-grid") else None)
        svc_data = third_data.get("services") or third_data.get("what-I-build") or third_data.get("what_i_build_section")
        if svc_sec and svc_data:
            sec_head = svc_sec.find(class_="sec-head") or svc_sec
            sh_data = svc_data.get("sec-head") or svc_data
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))
            _set_text(sec_head.find(class_="lede"), sh_data.get("lede"))

            cards = svc_sec.find_all(class_="svc-card")
            s_grid = svc_data.get("svc-grid", [])
            for i, card_entry in enumerate(s_grid):
                if i < len(cards):
                    c_info = card_entry.get("svc-card", card_entry)
                    _set_text(cards[i].find(class_="svc-num"), c_info.get("svc-num"))
                    _set_text(cards[i].find("h3"), c_info.get("h3"))
                    _set_text(cards[i].find("p"), c_info.get("p"))

            explore_el = svc_sec.find(class_="svc-explore")
            if explore_el and "svc-explore" in svc_data:
                _set_text(explore_el.find("span"), svc_data["svc-explore"].get("span"))
                chips = explore_el.find_all(class_="chip")
                for i, chip_data in enumerate(svc_data["svc-explore"].get("chip", [])):
                    if i < len(chips):
                        svg = chips[i].find("svg")
                        chips[i].clear()
                        chips[i].append(str(chip_data.get("text", "")))
                        if svg:
                            chips[i].append(" ")
                            chips[i].append(svg)
                        _set_href(chips[i], chip_data.get("url"))

        # stack (Tooling)
        stack_sec = soup.find("section", id="stack")
        stack_data = third_data.get("stack")
        if stack_sec and stack_data:
            sec_head = stack_sec.find(class_="sec-head") or stack_sec
            sh_data = stack_data.get("sec-head") or stack_data
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))
            _set_text(sec_head.find(class_="lede"), sh_data.get("lede"))

        # comparison
        cmp_sec = soup.find("section", id="comparison") or soup.find("section", class_=lambda c: c and "comparison" in c) or (soup.find(class_="cmp").find_parent("section") if soup.find(class_="cmp") else None)
        cmp_data = third_data.get("comparison") or third_data.get("honest_comparison_section")
        if cmp_sec and cmp_data:
            sec_head = cmp_sec.find(class_="sec-head") or cmp_sec
            sh_data = cmp_data.get("sec-head") or cmp_data
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))
            _set_text(sec_head.find(class_="lede"), sh_data.get("lede"))

            tbl = cmp_sec.find("table")
            c_table_data = cmp_data.get("cmp", {})
            if tbl and c_table_data:
                th_list = c_table_data.get("thead", [])
                th_els = tbl.select("thead th")
                for i, text in enumerate(th_list):
                    if i < len(th_els):
                        th_els[i].string = str(text)

                tr_els = tbl.select("tbody tr")
                for i, row in enumerate(c_table_data.get("tbody", [])):
                    if i < len(tr_els):
                        th = tr_els[i].find("th")
                        if th and "th" in row:
                            th.string = str(row["th"])
                        tds = tr_els[i].find_all("td")
                        for j, val in enumerate(row.get("td", [])):
                            if j < len(tds):
                                tick = tds[j].find(class_="cmp-tick")
                                tds[j].clear()
                                if tick:
                                    tds[j].append(tick)
                                    tds[j].append(" ")
                                tds[j].append(str(val))

            btn_p = cmp_sec.find("a", class_="btn-primary") or cmp_sec.find(class_="btn--primary")
            btn_data = cmp_data.get("btn-primary") or cmp_data.get("btn--primary")
            if btn_p and btn_data:
                svg = btn_p.find("svg")
                btn_p.clear()
                btn_p.append(str(btn_data.get("text", "")))
                if svg:
                    btn_p.append(" ")
                    btn_p.append(svg)
                _set_href(btn_p, btn_data.get("url"))

        # local-context
        lc_sec = soup.find("section", id="local-context") or soup.find("section", class_=lambda c: c and ("local-context" in c or "local_context" in c)) or (soup.find(class_="ctx-grid").find_parent("section") if soup.find(class_="ctx-grid") else None)
        lc_data = third_data.get("local-context") or third_data.get("local_context_section")
        if lc_sec and lc_data:
            cgrid = lc_data.get("ctx-grid", lc_data)
            sec_head = lc_sec.find(class_="sec-head") or lc_sec
            sh_data = cgrid.get("sec-head") or cgrid
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))

            prose_el = lc_sec.find(class_="prose")
            if prose_el and "prose" in cgrid:
                _update_prose_paragraphs(prose_el, cgrid["prose"].get("p", []), soup)

            cta = lc_sec.find("a", class_="link-cta") or lc_sec.find(class_="link-cta")
            cta_data = cgrid.get("link-cta")
            if cta and cta_data:
                svg = cta.find("svg")
                cta.clear()
                cta.append(str(cta_data.get("text", "")))
                if svg:
                    cta.append(" ")
                    cta.append(svg)
                _set_href(cta, cta_data.get("url"))

            card_el = lc_sec.find("div", class_="card")
            card_data = cgrid.get("card")
            if card_el and card_data:
                _set_text(card_el.find(class_="why-tag"), card_data.get("why-tag"))
                _set_text(card_el.find("h3"), card_data.get("h3"))
                _set_text(card_el.find("p"), card_data.get("p"))
                chk_items = card_data.get("checklist", [])
                li_els = card_el.select("ul.checklist li")
                for i, li_text in enumerate(chk_items):
                    if i < len(li_els):
                        svg = li_els[i].find("svg")
                        li_els[i].clear()
                        if svg:
                            li_els[i].append(svg)
                            li_els[i].append(" ")
                        li_els[i].append(str(li_text))
                for i in range(len(chk_items), len(li_els)):
                    li_els[i].decompose()

        print("  ✓ Third section applied.")

    # ─────────────────────────────────────────────────────────────
    # 4. FINAL SECTION (from new_final_section.json)
    # ─────────────────────────────────────────────────────────────
    if final_data:
        # process (how-i-work)
        proc_sec = soup.find("section", id="process") or soup.find("section", class_=lambda c: c and ("how-i-work" in c or "how_i_work" in c or "process" in c)) or (soup.find(class_="steps").find_parent("section") if soup.find(class_="steps") else None)
        proc_data = final_data.get("process") or final_data.get("how-i-work") or final_data.get("how_i_work_section")
        if proc_sec and proc_data:
            sec_head = proc_sec.find(class_="sec-head") or proc_sec
            sh_data = proc_data.get("sec-head") or proc_data
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))
            _set_text(sec_head.find(class_="lede"), sh_data.get("lede"))

            steps_els = proc_sec.find_all(class_="step") or proc_sec.find_all(class_="tl-item")
            s_list = proc_data.get("steps") or proc_data.get("timeline") or []
            for i, step_entry in enumerate(s_list):
                if i < len(steps_els):
                    s_info = step_entry.get("step") or step_entry.get("tl-item") or step_entry
                    when = s_info.get("tl-when", {})
                    body = s_info.get("tl-body", {})
                    num_val = s_info.get("num") or when.get("pill")
                    days_val = s_info.get("days") or when.get("sub")
                    h3_val = s_info.get("h3") or body.get("h3")
                    body_val = s_info.get("body") or body.get("p")

                    num_el = steps_els[i].find(class_="num")
                    if num_el:
                        days_el = num_el.find(class_="days")
                        if days_el and days_val:
                            days_el.string = str(days_val)
                        if num_val:
                            num_el.clear()
                            num_el.append(str(num_val))
                            if days_el:
                                num_el.append(days_el)

                    _set_text(steps_els[i].find("h3"), h3_val)
                    _set_text(steps_els[i].find(class_="body"), body_val)

        # proof
        proof_sec = soup.find("section", id="proof") or soup.find("section", class_=lambda c: c and ("proof-section" in c or "proof" in c)) or (soup.find(class_="proof-grid").find_parent("section") if soup.find(class_="proof-grid") else None)
        p_data = final_data.get("proof") or final_data.get("proof-section") or final_data.get("proof_section")
        if proof_sec and p_data:
            sec_head = proof_sec.find(class_="sec-head") or proof_sec
            sh_data = p_data.get("sec-head") or p_data
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))
            _set_text(sec_head.find(class_="lede"), sh_data.get("lede"))

            cards = proof_sec.find_all("article", class_="proof-card") or proof_sec.find_all(class_="proof-card")
            p_grid = p_data.get("grid g3") or p_data.get("proof-grid") or []
            for i, card_entry in enumerate(p_grid):
                if i < len(cards):
                    c_info = card_entry.get("proof-card", card_entry)
                    _set_text(cards[i].find(class_="proof-cat"), c_info.get("proof-cat"))
                    inner = c_info.get("proof-inner", c_info)
                    _set_text(cards[i].find("h3"), inner.get("h3"))
                    _set_text(cards[i].find("p"), inner.get("p"))

                    pm = cards[i].find(class_="proof-metric")
                    if pm and "proof-metric" in inner:
                        _set_text(pm.find("b"), inner["proof-metric"].get("b"))
                        _set_text(pm.find("span"), inner["proof-metric"].get("span"))

                    cta = cards[i].find("a", class_="link-cta") or cards[i].find(class_="link-cta")
                    if cta and "link-cta" in inner:
                        svg = cta.find("svg")
                        cta.clear()
                        cta.append(str(inner["link-cta"].get("text", "")))
                        if svg:
                            cta.append(" ")
                            cta.append(svg)
                        _set_href(cta, inner["link-cta"].get("url"))

            btn_g = (proof_sec.find(class_="proof-foot").find("a") if proof_sec.find(class_="proof-foot") else None) or proof_sec.find(class_="btn-ghost") or proof_sec.find(class_="btn--ghost")
            pf_data = p_data.get("proof-foot", {})
            bg_info = pf_data.get("btn-ghost") or pf_data.get("btn--ghost") or {}
            if btn_g and bg_info:
                svg = btn_g.find("svg")
                btn_g.clear()
                btn_g.append(str(bg_info.get("text", "")))
                if svg:
                    btn_g.append(" ")
                    btn_g.append(svg)
                _set_href(btn_g, bg_info.get("url"))

        # why-me
        why_sec = soup.find("section", id="why-me") or soup.find("section", class_=lambda c: c and ("why-me" in c or "why_me" in c)) or (soup.find(class_="why-grid").find_parent("section") if soup.find(class_="why-grid") else None)
        wm_data = final_data.get("why-me") or final_data.get("why_me_section")
        if why_sec and wm_data:
            sec_head = why_sec.find(class_="sec-head") or why_sec
            sh_data = wm_data.get("sec-head") or wm_data
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))

            cards = why_sec.find_all(class_="why-card")
            w_grid = wm_data.get("grid g3") or wm_data.get("why-grid") or []
            for i, card_entry in enumerate(w_grid):
                if i < len(cards):
                    c_info = card_entry.get("why-card", card_entry)
                    _set_text(cards[i].find(class_="why-tag"), c_info.get("why-tag"))
                    _set_text(cards[i].find("h3"), c_info.get("h3"))
                    _set_text(cards[i].find("p"), c_info.get("p"))

        # testimonials (client-words)
        tst_sec = soup.find("section", id="testimonials") or soup.find("section", class_=lambda c: c and ("client-words" in c or "client_words" in c or "testimonials" in c)) or (soup.find(class_="tst-grid").find_parent("section") if soup.find(class_="tst-grid") else None)
        tst_data = final_data.get("testimonials") or final_data.get("client-words") or final_data.get("client_words_section")
        if tst_sec and tst_data:
            sec_head = tst_sec.find(class_="sec-head") or tst_sec.find(class_="center") or tst_sec
            sh_data = tst_data.get("sec-head") or tst_data.get("center") or tst_data
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))
            _set_text(sec_head.find(class_="lede"), sh_data.get("lede"))

            cards = tst_sec.find_all("figure", class_="tst-card") or tst_sec.find_all(class_="tst-card")
            t_grid = tst_data.get("grid g3") or tst_data.get("tst-grid") or []
            for i, card_entry in enumerate(t_grid):
                if i < len(cards):
                    c_info = card_entry.get("tst-card", card_entry)
                    _set_text(cards[i].find(class_="tst-quote"), c_info.get("tst-quote"))
                    who = c_info.get("tst-who", {})
                    who_el = cards[i].find(class_="tst-who")
                    if who_el and who:
                        _set_text(who_el.find(class_="tst-avatar"), who.get("tst-avatar"))
                        _set_text(who_el.find("b"), who.get("b"))
                        _set_text(who_el.find(class_="tst-role"), who.get("tst-role") or who.get("span"))
                        _set_text(who_el.find(class_="tst-src"), who.get("tst-src"))

        # insights
        ins_sec = soup.find("section", id="insights") or soup.find("section", class_=lambda c: c and "insights" in c) or (soup.find(class_="blog-grid").find_parent("section") if soup.find(class_="blog-grid") else None)
        ins_data = final_data.get("insights") or final_data.get("insights_section") or final_data.get("blog_section")
        if ins_sec and ins_data:
            sec_head = ins_sec.find(class_="sec-head") or ins_sec
            sh_data = ins_data.get("sec-head") or ins_data
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))
            _set_text(sec_head.find(class_="lede"), sh_data.get("lede"))

            cards = ins_sec.find_all("article", class_="blog-card") or ins_sec.find_all(class_="blog-card")
            b_grid = ins_data.get("grid g3") or ins_data.get("blog-grid") or []
            for i, card_entry in enumerate(b_grid):
                if i < len(cards):
                    c_info = card_entry.get("blog-card", card_entry)
                    _set_text(cards[i].find(class_="proof-cat"), c_info.get("proof-cat") or c_info.get("blog-cat"))
                    b_inner = c_info.get("blog-inner", c_info)
                    _set_text(cards[i].find("h3"), b_inner.get("h3"))
                    _set_text(cards[i].find("p"), b_inner.get("p"))
                    cta = cards[i].find("a", class_="link-cta") or cards[i].find(class_="link-cta")
                    if cta and "link-cta" in b_inner:
                        svg = cta.find("svg")
                        cta.clear()
                        cta.append(str(b_inner["link-cta"].get("text", "")))
                        if svg:
                            cta.append(" ")
                            cta.append(svg)
                        _set_href(cta, b_inner["link-cta"].get("url"))

            btn_g = (ins_sec.find(class_="blog-foot").find("a") if ins_sec.find(class_="blog-foot") else None) or ins_sec.find(class_="btn-ghost") or ins_sec.find(class_="btn--ghost")
            bf_data = ins_data.get("blog-foot", {})
            bg_info = bf_data.get("btn-ghost") or bf_data.get("btn--ghost") or {}
            if btn_g and bg_info:
                svg = btn_g.find("svg")
                btn_g.clear()
                btn_g.append(str(bg_info.get("text", "")))
                if svg:
                    btn_g.append(" ")
                    btn_g.append(svg)
                _set_href(btn_g, bg_info.get("url"))

        # faq
        faq_sec = soup.find("section", id="faq") or soup.find("section", class_=lambda c: c and ("faq-section" in c or "faq" in c)) or (soup.find(class_="faq-wrap").find_parent("section") if soup.find(class_="faq-wrap") else None)
        faq_data = final_data.get("faq") or final_data.get("faq-section") or final_data.get("faq_section")
        if faq_sec and faq_data:
            sec_head = faq_sec.find(class_="sec-head") or faq_sec.find(class_="center") or faq_sec
            sh_data = faq_data.get("sec-head") or faq_data.get("center") or faq_data
            _set_text(sec_head.find(class_="eyebrow"), sh_data.get("eyebrow"))
            _set_text(sec_head.find("h2"), sh_data.get("h2"))
            _set_text(sec_head.find(class_="lede"), sh_data.get("lede"))

            items = faq_sec.find_all("details") or faq_sec.find_all(class_="faq-item")
            f_wrap = faq_data.get("faq") or faq_data.get("faq-wrap") or []
            for i, f_entry in enumerate(f_wrap):
                if i < len(items):
                    f_info = f_entry.get("faq-item", f_entry)
                    q_el = items[i].find("summary") or items[i].find(class_="faq-q")
                    if q_el and "faq-q" in f_info:
                        plus = q_el.find(class_="plus")
                        q_el.clear()
                        q_el.append(str(f_info["faq-q"]))
                        if plus:
                            q_el.append(plus)

                    a_el = items[i].find(class_="a") or items[i].find(class_="faq-a")
                    if a_el and "faq-a" in f_info:
                        a_el.string = str(f_info["faq-a"])

        # call-me-now / lets-talk (if present in template)
        cmn_sec = soup.find("section", id="lets-talk") or soup.find("section", class_=lambda c: c and ("call-me-now" in c or "call_me_now" in c or "final" in c))
        cmn_data = final_data.get("call-me-now") or final_data.get("call_me_now_section") or final_data.get("cta_section")
        if cmn_sec and cmn_data:
            cta_box = cmn_sec.select_one(".final-grid") or cmn_sec.select_one(".cta-grid > div") or cmn_sec
            _set_text(cta_box.find(class_="eyebrow"), cmn_data.get("eyebrow"))
            _set_text(cta_box.find("h2"), cmn_data.get("h2"))
            _set_text(cta_box.find(class_="lede"), cmn_data.get("lede"))

            contact_box = cta_box.find(class_="fcontact") or cta_box.find(class_="cta-contact")
            if contact_box and "cta-contact" in cmn_data:
                for c_btn_data in cmn_data["cta-contact"]:
                    if "btn--wa" in c_btn_data or "btn-primary" in c_btn_data:
                        wa_btn = contact_box.find(class_="btn--wa") or contact_box.find(class_="btn-primary")
                        b_val = c_btn_data.get("btn--wa") or c_btn_data.get("btn-primary")
                        if wa_btn and b_val:
                            svg = wa_btn.find("svg")
                            wa_btn.clear()
                            if svg:
                                wa_btn.append(svg)
                                wa_btn.append(" ")
                            wa_btn.append(str(b_val.get("text", "")))
                            _set_href(wa_btn, b_val.get("url"))
                    elif "btn--ghost" in c_btn_data or "btn-ghost" in c_btn_data:
                        ghost_btn = contact_box.find(class_="btn--ghost") or contact_box.find(class_="btn-ghost")
                        b_val = c_btn_data.get("btn--ghost") or c_btn_data.get("btn-ghost")
                        if ghost_btn and b_val:
                            svg = ghost_btn.find("svg")
                            ghost_btn.clear()
                            if svg:
                                ghost_btn.append(svg)
                                ghost_btn.append(" ")
                            ghost_btn.append(str(b_val.get("text", "")))
                            _set_href(ghost_btn, b_val.get("url"))

            meta_el = cta_box.find(class_="fmeta") or cta_box.find(class_="cta-meta")
            if meta_el and "cta-meta" in cmn_data:
                svg = meta_el.find("svg")
                meta_el.clear()
                if svg:
                    meta_el.append(svg)
                    meta_el.append(" ")
                meta_el.append(str(cmn_data["cta-meta"]))

            author_box = cta_box.find(class_="author-row")
            if author_box and "author-row" in cmn_data:
                ar = cmn_data["author-row"]
                img_el = author_box.find("img")
                if img_el and "img" in ar:
                    img_el["src"] = str(ar["img"])
                _set_text(author_box.find("b"), ar.get("b"))
                _set_text(author_box.find("span"), ar.get("span"))

        print("  ✓ Final section applied.")

    # ─────────────────────────────────────────────────────────────
    # META & JSON-LD UPDATE
    # ─────────────────────────────────────────────────────────────
    _update_meta_and_jsonld(soup, role, city, state)

    # ─────────────────────────────────────────────────────────────
    # PLACEHOLDER REPLACEMENT
    # ─────────────────────────────────────────────────────────────
    html_out = str(soup)
    html_out = html_out.replace("<lineargradient", "<linearGradient").replace("</lineargradient>", "</linearGradient>")
    html_out = html_out.replace("viewbox=", "viewBox=")
    slug = city.lower().replace(" ", "-")
    html_out = html_out.replace("{{CITY}}", city)
    html_out = html_out.replace("{{STATE}}", state)
    html_out = html_out.replace("{{GEO_CODE}}", geo_code)
    html_out = html_out.replace("{{LANDMARKS}}", landmarks)
    html_out = html_out.replace("{{DOMINENT_INDUSTRIES}}", dominent_industries)

    # Clean CSS comments (/* ... */) inside <style> blocks
    def _clean_css_comments(match):
        css = match.group(1)
        cleaned_css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
        return f"<style>{cleaned_css}</style>"

    html_out = re.sub(r"<style[^>]*>(.*?)</style>", _clean_css_comments, html_out, flags=re.DOTALL)

    # Strip viewer widget sentinel comments if present
    sentinels = [
        "<!-- [VIEWER-WIDGET-CSS:START] -->",
        "<!-- [VIEWER-WIDGET-CSS:END] -->",
        "<!-- [VIEWER-WIDGET-JS:START] -->",
        "<!-- [VIEWER-WIDGET-JS:END] -->",
    ]
    for s in sentinels:
        html_out = html_out.replace(s, "")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"\n  ✓ Final website written to: {output_path}")


# ── main entry point ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Full pipeline: generate content for all sections via LLM, then compile into a final website."
    )
    parser.add_argument("--role", type=str, required=True,
                        help="Target role/service (e.g., 'Machine Learning Engineer', 'Data Scientist').")
    parser.add_argument("--city", type=str, required=True,
                        help="City name to replace {{CITY}} placeholders.")
    parser.add_argument("--state", type=str, required=True,
                        help="State name to replace {{STATE}} placeholders.")
    parser.add_argument("--geo-code", type=str, required=True,
                        help="Geo Code (ISO 3166-2:IN) to replace {{GEO_CODE}} placeholders.")
    parser.add_argument("--landmarks", type=str, required=True,
                        help="Landmark separated by comma to replace {{LANDMARKS}} placeholders.")
    parser.add_argument("--dominentIindustries", type=str, required=True,
                        help="Dominant industries separated by comma to replace {{DOMINENT_INDUSTRIES}} placeholders.")
    parser.add_argument("--model", type=str, default="openrouter/meta-llama/llama-3.3-70b-instruct",
                        help="OpenRouter model to use for generation.")
    parser.add_argument("--output", type=str, default=None,
                        help="Output HTML filename (default: location-page-<city-slug>.html).")
    parser.add_argument("--skip-generate", action="store_true",
                        help="Skip LLM generation and only compile HTML from existing generated/ files.")
    parser.add_argument("--skip-widget", action="store_true",
                        help="Skip hero viewer widget generation and injection.")
    parser.add_argument("--sample-widget", type=str, default=None,
                        help="Filename of a specific widget in widgets/ to use as blueprint (random if omitted).")
    args = parser.parse_args()

    load_dotenv()

    if not os.environ.get("OPENROUTER_API_KEY") and not args.skip_generate:
        print("Error: OPENROUTER_API_KEY not found in environment or .env file.")
        return

    slug = args.city.lower().replace(" ", "-")
    output_html = args.output or f"location-page-{slug}.html"
    if os.path.isabs(output_html):
        output_path = output_html
    else:
        output_path = os.path.join(HTML_PAGES_DIR, os.path.basename(output_html))

    # ── Step 1: Generate content for each section ──
    if not args.skip_generate:
        print("\n" + "="*60)
        print("  STEP 1: Generating content via LLM")
        print("="*60)

        os.makedirs(GENERATED_DIR, exist_ok=True)

        for i, section in enumerate(SECTIONS, 1):
            data_path = os.path.join(ACTUAL_DATA_DIR, section["data"])
            rules_path = os.path.join(RULES_DIR, section["rules"])
            output_path_json = os.path.join(GENERATED_DIR, section["output"])

            if not os.path.exists(data_path):
                print(f"  ⚠ Skipping {section['data']} — file not found in actual_data/")
                continue
            if not os.path.exists(rules_path):
                print(f"  ⚠ Skipping {section['data']} — rules file not found in rules/")
                continue

            sec_title = section.get("name", f"Section {i}")
            generate_section(
                args.role, args.city, args.state, args.geo_code, args.landmarks, args.dominentIindustries, args.model,
                data_path, rules_path, output_path_json,
                step_num=i, total_steps=len(SECTIONS), section_title=sec_title
            )
    else:
        print("\n  Skipping LLM generation (--skip-generate). Using existing generated/ files.")

    # ── Step 2: Compile final HTML ──
    print("\n" + "="*60)
    print("  STEP 2: Compiling HTML")
    print("="*60)

    compile_html(args.role, args.city, args.state, args.geo_code, args.landmarks, args.dominentIindustries, output_path)

    # ── Step 3: Hero Viewer Widget Generation & Injection ──
    if not args.skip_widget:
        print("\n" + "="*60)
        print("  STEP 3: Hero Viewer Widget Generation & Injection")
        print("="*60)

        tmp_widget_path = os.path.join(BASE_DIR, "generated_components", "interactive_viewer.html")

        if not args.skip_generate or not os.path.exists(tmp_widget_path):
            print("  Generating role-specific hero viewer widget via LLM...")
            print(f"  Sample widget: {args.sample_widget or '(random)'} ")
            generate_viewer(
                role                = args.role,
                city                = args.city,
                state               = args.state,
                geo_code            = args.geo_code,
                landmarks           = args.landmarks,
                dominent_industries = args.dominentIindustries,
                sample_widget_path  = args.sample_widget,
                model               = args.model or "openrouter/deepseek/deepseek-v4-flash",
                output_path         = tmp_widget_path,
            )
        else:
            print(f"  Using existing hero widget file: {tmp_widget_path}")

        if os.path.exists(tmp_widget_path):
            with open(tmp_widget_path, "r", encoding="utf-8") as f:
                widget_html = f.read()
            with open(output_path, "r", encoding="utf-8") as f:
                page_html = f.read()

            try:
                updated_html = inject_widget_into_html(page_html, widget_html)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(updated_html)
                print(f"  ✓ Hero viewer widget injected into: {output_path}")
            except Exception as e:
                print(f"  ⚠ Failed to inject hero viewer widget into {output_path}: {e}")

    print("\n" + "="*60)
    print("  PIPELINE COMPLETE")
    print(f"  Output: {output_path}")
    print("="*60)


if __name__ == "__main__":
    main()
