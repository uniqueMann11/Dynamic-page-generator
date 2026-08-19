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
try:
    from litellm import completion
except ImportError:
    print("litellm not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "litellm"])
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
    HTML_PAGES_DIR = os.path.join(ROOT_DIR, "HTML pages")

ACTUAL_DATA_DIR = os.path.join(BASE_DIR, "actual_data")
RULES_DIR = os.path.join(BASE_DIR, "rules")
os.makedirs(HTML_PAGES_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

TEMPLATE_PATH = os.path.join(ROOT_DIR, "hire-machine-learning-engineer-ahmedabad.html")
if not os.path.exists(TEMPLATE_PATH):
    TEMPLATE_PATH = os.path.join(BASE_DIR, "hire-machine-learning-engineer-ahmedabad.html")
if not os.path.exists(TEMPLATE_PATH):
    TEMPLATE_PATH = os.path.join(HTML_PAGES_DIR, "location-page-template.html")

# The four sections in order — each entry maps:
#   data file name  ->  rules file name  ->  generated output name
SECTIONS = [
    {"data": "hero.json",           "rules": "hero_rules.json",           "output": "new_hero.json"},
    {"data": "second_hero.json",    "rules": "second_hero_rules.json",    "output": "new_second_hero.json"},
    {"data": "third_section.json",  "rules": "third_section_rules.json",  "output": "new_third_section.json"},
    {"data": "final_section.json",  "rules": "final_section_rules.json",  "output": "new_final_section.json"},
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


def generate_section(role, city, state, geo_code, landmarks, dominentIindustries, model, data_path, rules_path, output_path):
    """Send one section through the LLM and save the result."""
    section_name = os.path.basename(data_path)
    print(f"\n{'='*60}")
    print(f"  Generating: {section_name}  ->  {os.path.basename(output_path)}")
    print(f"{'='*60}")

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
        # Some models wrap the entire response as a string inside a single-key object
        # e.g. {"": "{"value-strip": ...}"} or {"response": "{...}"}
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
                    pass  # Not double-encoded, leave as-is

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2)

        print(f"  [OK] Saved to {output_path}")
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
    Updates the <p> elements within a .prose container.
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

    # Update existing or create new
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

    # Remove any extra <p> elements that existed in template but not in new data!
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

    Uses targeted string replacement within each attribute value so that
    only the template city/state/role tokens are swapped — no blind global
    replace that could damage class names or CSS.
    """
    old_city  = TEMPLATE_CITY
    old_state = TEMPLATE_STATE
    old_role  = TEMPLATE_ROLE

    old_slug  = old_city.lower().replace(" ", "-")
    new_slug  = city.lower().replace(" ", "-")

    old_role_slug = old_role.lower().replace(" ", "-")
    new_role_slug = role.lower().replace(" ", "-")

    # Helper: swap template tokens inside a string
    def _swap(text):
        if not text:
            return text
        text = text.replace(old_city, city)
        text = text.replace(old_state, state)
        text = text.replace(old_role, role)
        # Slug-based replacements (URLs)
        text = text.replace(old_slug, new_slug)
        text = text.replace(old_role_slug, new_role_slug)
        return text

    head = soup.find("head")
    if not head:
        print("  ⚠ No <head> found — skipping meta/JSON-LD update.")
        return

    # ── 1. <title> ────────────────────────────────────────────────────────
    title_el = head.find("title")
    if title_el and title_el.string:
        title_el.string = _swap(title_el.string)

    # ── 2. <meta> tags ────────────────────────────────────────────────────
    for meta in head.find_all("meta"):
        for attr in ("content",):
            val = meta.get(attr)
            if val:
                meta[attr] = _swap(val)

    # ── 3. <link rel="canonical"> ─────────────────────────────────────────
    canon = head.find("link", rel="canonical")
    if canon and canon.get("href"):
        canon["href"] = _swap(canon["href"])

    # ── 4. <script type="application/ld+json"> ───────────────────────────
    for script in head.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            ld = json.loads(script.string)
        except json.JSONDecodeError:
            print("  ⚠ Could not parse JSON-LD — skipping.")
            continue

        # Recursively walk the JSON and swap string values
        def _walk(obj):
            if isinstance(obj, dict):
                return {k: _walk(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_walk(item) for item in obj]
            elif isinstance(obj, str):
                return _swap(obj)
            return obj

        ld = _walk(ld)

        # Also update specific structured fields for safety:
        graph = ld.get("@graph", [])
        for node in graph:
            ntype = node.get("@type", "")

            if ntype == "ProfessionalService":
                # Update areaServed city/state names
                for area in node.get("areaServed", []):
                    if area.get("@type") == "City":
                        area["name"] = city
                    elif area.get("@type") == "State":
                        area["name"] = state
                # Update address
                addr = node.get("address", {})
                if addr:
                    addr["addressLocality"] = city
                    addr["addressRegion"] = state
                # Update founder jobTitle
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
    # 1. HERO & TRUSTBAR (from new_hero.json)
    # ─────────────────────────────────────────────────────────────
    hero_sec = soup.find("section", class_="hero")
    if hero_sec and "hero" in hero_data:
        hd = hero_data["hero"]

        # hero-badge
        badge_el = hero_sec.find(class_="hero-badge")
        if badge_el and "hero-badge" in hd:
            dot_span = badge_el.find(class_="dot")
            badge_el.clear()
            if dot_span:
                badge_el.append(dot_span)
            else:
                badge_el.append(soup.new_tag("span", attrs={"class": "dot"}))
            badge_el.append(" " + str(hd["hero-badge"]))

        # h1
        h1_el = hero_sec.find("h1")
        if h1_el and "h1" in hd:
            h1_data = hd["h1"]
            h1_el.clear()
            if isinstance(h1_data, dict):
                if "h1-text" in h1_data:
                    h1_el.append(str(h1_data["h1-text"]) + " ")
                if "em" in h1_data:
                    em_tag = soup.new_tag("em")
                    em_tag.string = str(h1_data["em"])
                    h1_el.append(em_tag)
                if "h1-suffix" in h1_data:
                    h1_el.append(str(h1_data["h1-suffix"]))
            else:
                h1_el.string = str(h1_data)

        # hero-sub
        sub_el = hero_sec.find(class_="hero-sub")
        if sub_el and "hero-sub" in hd:
            sub_el.string = str(hd["hero-sub"])

        # hero-stats
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

        # hero-actions
        actions_container = hero_sec.find(class_="hero-actions")
        if actions_container and "hero-actions" in hd:
            btns = actions_container.find_all("a", class_="btn")
            for i, btn_entry in enumerate(hd["hero-actions"]):
                if i < len(btns):
                    btn_el = btns[i]
                    b_info = btn_entry.get("btn--primary") or btn_entry.get("btn--ghost") or btn_entry
                    if isinstance(b_info, dict):
                        svg = btn_el.find("svg")
                        btn_el.clear()
                        btn_el.append(str(b_info.get("text", "")))
                        if svg:
                            btn_el.append(" ")
                            btn_el.append(svg)
                        if "url" in b_info:
                            btn_el["href"] = str(b_info["url"])

        # hero-note
        note_el = hero_sec.find(class_="hero-note")
        if note_el and "hero-note" in hd:
            svg = note_el.find("svg")
            note_el.clear()
            if svg:
                note_el.append(svg)
                note_el.append(" ")
            note_el.append(str(hd["hero-note"]))

        # route-card
        rc_el = hero_sec.find(class_="route-card")
        if rc_el and "route-card" in hd:
            rc_data = hd["route-card"]
            if "route-title" in rc_data:
                _set_text(rc_el.find(class_="route-title"), rc_data["route-title"])

            nodes = rc_el.find_all(class_="route-node")
            if "route-nodes" in rc_data:
                for i, node_entry in enumerate(rc_data["route-nodes"]):
                    if i < len(nodes):
                        n_info = list(node_entry.values())[0] if isinstance(node_entry, dict) and not "b" in node_entry else node_entry
                        if isinstance(n_info, dict):
                            txt_box = nodes[i].find(class_="txt")
                            if txt_box:
                                _set_text(txt_box.find("b"), n_info.get("b"))
                                _set_text(txt_box.find("span"), n_info.get("span"))
                            if "tag" in n_info and nodes[i].find(class_="tag"):
                                _set_text(nodes[i].find(class_="tag"), n_info["tag"])

            foot = rc_el.find(class_="route-foot")
            if foot and "route-foot" in rc_data:
                spans = foot.find_all("span")
                for i, f_item in enumerate(rc_data["route-foot"]):
                    if i < len(spans):
                        spans[i].clear()
                        if "text" in f_item:
                            spans[i].append(str(f_item["text"]) + " ")
                        if "b" in f_item:
                            b_tag = soup.new_tag("b")
                            b_tag.string = str(f_item["b"])
                            spans[i].append(b_tag)

    # Trustbar
    trustbar_el = soup.find(class_="trustbar")
    if trustbar_el and "trustbar" in hero_data:
        tb_items = trustbar_el.find_all(class_="trust-item")
        t_data = hero_data["trustbar"].get("trust-item", [])
        for i, item_text in enumerate(t_data):
            if i < len(tb_items):
                svg = tb_items[i].find("svg")
                tb_items[i].clear()
                if svg:
                    tb_items[i].append(svg)
                tb_items[i].append(str(item_text))

    print("  ✓ Hero section applied.")

    # ─────────────────────────────────────────────────────────────
    # 2. SECOND HERO (from new_second_hero.json)
    # ─────────────────────────────────────────────────────────────
    if second_data:
        # value-strip
        val_sec = soup.find("section", class_=lambda c: c and "value-strip" in c) or (soup.find(class_="value-grid").find_parent("section") if soup.find(class_="value-grid") else None)
        v_data = second_data.get("value-strip") or second_data.get("value_strip_section")
        if val_sec and v_data:
            center_el = val_sec.find(class_="center")
            if center_el and "center" in v_data:
                _set_text(center_el.find(class_="eyebrow"), v_data["center"].get("eyebrow"))
                _set_text(center_el.find("h2"), v_data["center"].get("h2"))

            cards = val_sec.find_all(class_="value-card")
            v_grid = v_data.get("value-grid", [])
            for i, card_entry in enumerate(v_grid):
                if i < len(cards):
                    c_info = card_entry.get("value-card", card_entry)
                    _set_text(cards[i].find("h3"), c_info.get("h3"))
                    _set_text(cards[i].find("p"), c_info.get("p"))

        # quick-answer
        qa_sec = soup.find("section", class_=lambda c: c and "quick-answer" in c) or (soup.find(class_="answer-card").find_parent("section") if soup.find(class_="answer-card") else None)
        q_data = second_data.get("quick-answer") or second_data.get("plain_answer_section")
        if qa_sec and q_data:
            pg = q_data.get("prose-grid", q_data)
            _set_text(qa_sec.find(class_="eyebrow"), pg.get("eyebrow"))
            _set_text(qa_sec.find("h2"), pg.get("h2"))

            ans_card = qa_sec.find(class_="answer-card")
            if ans_card and "answer-card" in pg:
                _set_text(ans_card.find(class_="tag"), pg["answer-card"].get("tag"))
                _set_text(ans_card.find("p"), pg["answer-card"].get("p"))

            prose_el = qa_sec.find(class_="prose")
            if prose_el and "prose" in pg:
                _update_prose_paragraphs(prose_el, pg["prose"].get("p", []), soup)

                chk_list = pg["prose"].get("checklist", [])
                if isinstance(chk_list, str):
                    chk_list = [chk_list]
                li_els = prose_el.select(".checklist li")
                for i, li_text in enumerate(chk_list):
                    if i < len(li_els):
                        svg = li_els[i].find("svg")
                        li_els[i].clear()
                        if svg:
                            li_els[i].append(svg)
                            li_els[i].append(" ")
                        li_els[i].append(str(li_text))
                for i in range(len(chk_list), len(li_els)):
                    li_els[i].decompose()

        print("  ✓ Second hero section applied.")

    # ─────────────────────────────────────────────────────────────
    # 3. THIRD SECTION (from new_third_section.json)
    # ─────────────────────────────────────────────────────────────
    if third_data:
        # what-I-build
        wb_sec = soup.find("section", class_=lambda c: c and ("what-I-build" in c or "what_i_build" in c)) or (soup.find(class_="svc-grid").find_parent("section") if soup.find(class_="svc-grid") else None)
        wb_data = third_data.get("what-I-build") or third_data.get("what_i_build_section")
        if wb_sec and wb_data:
            _set_text(wb_sec.find(class_="eyebrow"), wb_data.get("eyebrow"))
            _set_text(wb_sec.find("h2"), wb_data.get("h2"))
            _set_text(wb_sec.find(class_="lede"), wb_data.get("lede"))

            cards = wb_sec.find_all(class_="svc-card")
            svc_grid = wb_data.get("svc-grid", [])
            for i, card_entry in enumerate(svc_grid):
                if i < len(cards):
                    c_info = card_entry.get("svc-card", card_entry)
                    _set_text(cards[i].find(class_="svc-num"), c_info.get("svc-num"))
                    _set_text(cards[i].find("h3"), c_info.get("h3"))
                    _set_text(cards[i].find("p"), c_info.get("p"))
                    cta = cards[i].find(class_="link-cta")
                    if cta and "link-cta" in c_info:
                        svg = cta.find("svg")
                        cta.clear()
                        cta.append(str(c_info["link-cta"].get("text", "")))
                        if svg:
                            cta.append(" ")
                            cta.append(svg)
                        _set_href(cta, c_info["link-cta"].get("url"))

            explore_el = wb_sec.find(class_="svc-explore")
            if explore_el and "svc-explore" in wb_data:
                _set_text(explore_el.find("span"), wb_data["svc-explore"].get("span"))
                chips = explore_el.find_all(class_="chip")
                for i, chip_data in enumerate(wb_data["svc-explore"].get("chip", [])):
                    if i < len(chips):
                        _set_text(chips[i], chip_data.get("text"))
                        _set_href(chips[i], chip_data.get("url"))

        # comparison
        cmp_sec = soup.find("section", class_=lambda c: c and "comparison" in c) or (soup.find(class_="cmp").find_parent("section") if soup.find(class_="cmp") else None)
        cmp_data = third_data.get("comparison") or third_data.get("honest_comparison_section")
        if cmp_sec and cmp_data:
            _set_text(cmp_sec.find(class_="eyebrow"), cmp_data.get("eyebrow"))
            _set_text(cmp_sec.find("h2"), cmp_data.get("h2"))
            _set_text(cmp_sec.find(class_="lede"), cmp_data.get("lede"))

            tbl = cmp_sec.find("table", class_="cmp")
            if tbl and "cmp" in cmp_data:
                th_list = cmp_data["cmp"].get("thead", [])
                th_els = tbl.select("thead th")
                for i, text in enumerate(th_list):
                    if i < len(th_els):
                        th_els[i].string = str(text)

                tr_els = tbl.select("tbody tr")
                for i, row in enumerate(cmp_data["cmp"].get("tbody", [])):
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

            btn_p = cmp_sec.find(class_="btn--primary")
            if btn_p and "btn--primary" in cmp_data:
                svg = btn_p.find("svg")
                btn_p.clear()
                btn_p.append(str(cmp_data["btn--primary"].get("text", "")))
                if svg:
                    btn_p.append(" ")
                    btn_p.append(svg)
                _set_href(btn_p, cmp_data["btn--primary"].get("url"))

        # local-context
        lc_sec = soup.find("section", class_=lambda c: c and ("local-context" in c or "local_context" in c)) or (soup.find(class_="ctx-grid").find_parent("section") if soup.find(class_="ctx-grid") else None)
        lc_data = third_data.get("local-context") or third_data.get("local_context_section")
        if lc_sec and lc_data:
            cgrid = lc_data.get("ctx-grid", lc_data)
            _set_text(lc_sec.find(class_="eyebrow"), cgrid.get("eyebrow"))
            _set_text(lc_sec.find("h2"), cgrid.get("h2"))

            prose_el = lc_sec.find(class_="prose")
            if prose_el and "prose" in cgrid:
                _update_prose_paragraphs(prose_el, cgrid["prose"].get("p", []), soup)

            cta = lc_sec.find(class_="link-cta")
            if cta and "link-cta" in cgrid:
                svg = cta.find("svg")
                cta.clear()
                cta.append(str(cgrid["link-cta"].get("text", "")))
                if svg:
                    cta.append(" ")
                    cta.append(svg)
                _set_href(cta, cgrid["link-cta"].get("url"))

            wt = lc_sec.find(class_="widget-title")
            if wt:
                wt_text = str(cgrid.get("widget-title", f"{city} · ML ecosystem"))
                wt_text = wt_text.replace("Ahmedabad", city).replace("Delhi", city).replace("{{CITY}}", city)
                _set_text(wt, wt_text)

            floats = lc_sec.find_all(class_="ctx-float")
            for i, f_data in enumerate(cgrid.get("ctx-float", [])):
                if i < len(floats):
                    _set_text(floats[i].find("b"), f_data.get("b"))
                    _set_text(floats[i].find("span"), f_data.get("span"))

        print("  ✓ Third section applied.")

    # ─────────────────────────────────────────────────────────────
    # 4. FINAL SECTION (from new_final_section.json)
    # ─────────────────────────────────────────────────────────────
    if final_data:
        # how-i-work
        hiw_sec = soup.find("section", class_=lambda c: c and ("how-i-work" in c or "how_i_work" in c)) or (soup.find(class_="timeline").find_parent("section") if soup.find(class_="timeline") else None)
        hiw_data = final_data.get("how-i-work") or final_data.get("how_i_work_section")
        if hiw_sec and hiw_data:
            _set_text(hiw_sec.find(class_="eyebrow"), hiw_data.get("eyebrow"))
            _set_text(hiw_sec.find("h2"), hiw_data.get("h2"))
            _set_text(hiw_sec.find(class_="lede"), hiw_data.get("lede"))

            tl_items = hiw_sec.find_all(class_="tl-item")
            for i, step_entry in enumerate(hiw_data.get("timeline", [])):
                if i < len(tl_items):
                    s_info = step_entry.get("tl-item", step_entry)
                    when = s_info.get("tl-when", {})
                    body = s_info.get("tl-body", {})
                    _set_text(tl_items[i].find(class_="pill"), when.get("pill"))
                    _set_text(tl_items[i].find(class_="sub"), when.get("sub"))
                    _set_text(tl_items[i].find("h3"), body.get("h3"))
                    _set_text(tl_items[i].find("p"), body.get("p"))

            btn = hiw_sec.find(class_="btn--primary")
            if btn and "btn--primary" in hiw_data:
                svg = btn.find("svg")
                btn.clear()
                btn.append(str(hiw_data["btn--primary"].get("text", "")))
                if svg:
                    btn.append(" ")
                    btn.append(svg)
                _set_href(btn, hiw_data["btn--primary"].get("url"))

        # proof-section
        proof_sec = soup.find("section", class_=lambda c: c and ("proof-section" in c or "proof" in c)) or (soup.find(class_="proof-grid").find_parent("section") if soup.find(class_="proof-grid") else None)
        p_data = final_data.get("proof-section") or final_data.get("proof_section")
        if proof_sec and p_data:
            _set_text(proof_sec.find(class_="eyebrow"), p_data.get("eyebrow"))
            _set_text(proof_sec.find("h2"), p_data.get("h2"))
            _set_text(proof_sec.find(class_="lede"), p_data.get("lede"))

            cards = proof_sec.find_all(class_="proof-card")
            for i, card_entry in enumerate(p_data.get("proof-grid", [])):
                if i < len(cards):
                    c_info = card_entry.get("proof-card", card_entry)
                    _set_text(cards[i].find(class_="proof-cat"), c_info.get("proof-cat"))
                    inner = c_info.get("proof-inner", {})
                    _set_text(cards[i].find("h3"), inner.get("h3"))
                    _set_text(cards[i].find("p"), inner.get("p"))

                    pm = cards[i].find(class_="proof-metric")
                    if pm and "proof-metric" in inner:
                        _set_text(pm.find("b"), inner["proof-metric"].get("b"))
                        _set_text(pm.find("span"), inner["proof-metric"].get("span"))

                    cta = cards[i].find(class_="link-cta")
                    if cta and "link-cta" in inner:
                        svg = cta.find("svg")
                        cta.clear()
                        cta.append(str(inner["link-cta"].get("text", "")))
                        if svg:
                            cta.append(" ")
                            cta.append(svg)
                        _set_href(cta, inner["link-cta"].get("url"))

            btn_g = proof_sec.find(class_="btn--ghost")
            if btn_g and "proof-foot" in p_data:
                bg_info = p_data["proof-foot"].get("btn--ghost", {})
                svg = btn_g.find("svg")
                btn_g.clear()
                btn_g.append(str(bg_info.get("text", "")))
                if svg:
                    btn_g.append(" ")
                    btn_g.append(svg)
                _set_href(btn_g, bg_info.get("url"))

        # why-me
        why_sec = soup.find("section", class_=lambda c: c and ("why-me" in c or "why_me" in c)) or (soup.find(class_="why-grid").find_parent("section") if soup.find(class_="why-grid") else None)
        wm_data = final_data.get("why-me") or final_data.get("why_me_section")
        if why_sec and wm_data:
            _set_text(why_sec.find(class_="eyebrow"), wm_data.get("eyebrow"))
            _set_text(why_sec.find("h2"), wm_data.get("h2"))

            cards = why_sec.find_all(class_="why-card")
            for i, card_entry in enumerate(wm_data.get("why-grid", [])):
                if i < len(cards):
                    c_info = card_entry.get("why-card", card_entry)
                    _set_text(cards[i].find(class_="why-tag"), c_info.get("why-tag"))
                    _set_text(cards[i].find("h3"), c_info.get("h3"))
                    _set_text(cards[i].find("p"), c_info.get("p"))

        # client-words
        cw_sec = soup.find("section", class_=lambda c: c and ("client-words" in c or "client_words" in c)) or (soup.find(class_="tst-grid").find_parent("section") if soup.find(class_="tst-grid") else None)
        cw_data = final_data.get("client-words") or final_data.get("client_words_section") or final_data.get("testimonials_section")
        if cw_sec and cw_data:
            center_el = cw_sec.find(class_="center")
            if center_el and "center" in cw_data:
                _set_text(center_el.find(class_="eyebrow"), cw_data["center"].get("eyebrow"))
                _set_text(center_el.find("h2"), cw_data["center"].get("h2"))
                _set_text(center_el.find(class_="lede"), cw_data["center"].get("lede"))

            cards = cw_sec.find_all(class_="tst-card")
            for i, card_entry in enumerate(cw_data.get("tst-grid", [])):
                if i < len(cards):
                    c_info = card_entry.get("tst-card", card_entry)
                    _set_text(cards[i].find(class_="tst-quote"), c_info.get("tst-quote"))
                    who = c_info.get("tst-who", {})
                    who_el = cards[i].find(class_="tst-who")
                    if who_el:
                        _set_text(who_el.find(class_="tst-avatar"), who.get("tst-avatar"))
                        _set_text(who_el.find("b"), who.get("b"))
                        b_el = who_el.find("b")
                        role_span = b_el.find_next_sibling("span") if b_el else who_el.select_one("span > span")
                        _set_text(role_span, who.get("span"))
                        _set_text(who_el.find(class_="tst-src"), who.get("tst-src"))

        # insights
        ins_sec = soup.find("section", class_=lambda c: c and "insights" in c) or (soup.find(class_="blog-grid").find_parent("section") if soup.find(class_="blog-grid") else None)
        ins_data = final_data.get("insights") or final_data.get("insights_section") or final_data.get("blog_section")
        if ins_sec and ins_data:
            _set_text(ins_sec.find(class_="eyebrow"), ins_data.get("eyebrow"))
            _set_text(ins_sec.find("h2"), ins_data.get("h2"))
            _set_text(ins_sec.find(class_="lede"), ins_data.get("lede"))

            cards = ins_sec.find_all(class_="blog-card")
            for i, card_entry in enumerate(ins_data.get("blog-grid", [])):
                if i < len(cards):
                    c_info = card_entry.get("blog-card", card_entry)
                    b_inner = c_info.get("blog-inner", {})
                    _set_text(cards[i].find(class_="blog-cat"), b_inner.get("blog-cat"))
                    _set_text(cards[i].find("h3"), b_inner.get("h3"))
                    _set_text(cards[i].find("p"), b_inner.get("p"))
                    cta = cards[i].find(class_="link-cta")
                    if cta and "link-cta" in b_inner:
                        svg = cta.find("svg")
                        cta.clear()
                        cta.append(str(b_inner["link-cta"].get("text", "")))
                        if svg:
                            cta.append(" ")
                            cta.append(svg)
                        _set_href(cta, b_inner["link-cta"].get("url"))

            btn_g = ins_sec.find(class_="btn--ghost")
            if btn_g and "blog-foot" in ins_data:
                bg_info = ins_data["blog-foot"].get("btn--ghost", {})
                svg = btn_g.find("svg")
                btn_g.clear()
                btn_g.append(str(bg_info.get("text", "")))
                if svg:
                    btn_g.append(" ")
                    btn_g.append(svg)
                _set_href(btn_g, bg_info.get("url"))

        # faq-section
        faq_sec = soup.find("section", class_=lambda c: c and ("faq-section" in c or "faq" in c)) or (soup.find(class_="faq-wrap").find_parent("section") if soup.find(class_="faq-wrap") else None)
        faq_data = final_data.get("faq-section") or final_data.get("faq_section")
        if faq_sec and faq_data:
            center_el = faq_sec.find(class_="center")
            if center_el and "center" in faq_data:
                _set_text(center_el.find(class_="eyebrow"), faq_data["center"].get("eyebrow"))
                _set_text(center_el.find("h2"), faq_data["center"].get("h2"))
                _set_text(center_el.find(class_="lede"), faq_data["center"].get("lede"))

            items = faq_sec.find_all("details") or faq_sec.find_all(class_="faq-item")
            for i, f_entry in enumerate(faq_data.get("faq-wrap", [])):
                if i < len(items):
                    f_info = f_entry.get("faq-item", f_entry)
                    q_el = items[i].find("summary") or items[i].find(class_="faq-q")
                    if q_el and "faq-q" in f_info:
                        plus = q_el.find(class_="plus")
                        q_el.clear()
                        q_el.append(str(f_info["faq-q"]))
                        if plus:
                            q_el.append(plus)

                    a_el = items[i].find(class_="faq-a")
                    if a_el and "faq-a" in f_info:
                        a_el.string = str(f_info["faq-a"])

        # call-me-now
        cmn_sec = soup.find("section", class_=lambda c: c and ("call-me-now" in c or "call_me_now" in c)) or soup.find("section", id="lets-talk")
        cmn_data = final_data.get("call-me-now") or final_data.get("call_me_now_section") or final_data.get("cta_section")
        if cmn_sec and cmn_data:
            cta_grid_div = cmn_sec.select_one(".cta-grid > div") or cmn_sec
            _set_text(cta_grid_div.find(class_="eyebrow"), cmn_data.get("eyebrow"))
            _set_text(cta_grid_div.find("h2"), cmn_data.get("h2"))
            _set_text(cta_grid_div.find(class_="lede"), cmn_data.get("lede"))

            contact_box = cta_grid_div.find(class_="cta-contact")
            if contact_box and "cta-contact" in cmn_data:
                for c_btn_data in cmn_data["cta-contact"]:
                    if "btn--wa" in c_btn_data:
                        wa_btn = contact_box.find(class_="btn--wa")
                        if wa_btn:
                            svg = wa_btn.find("svg")
                            wa_btn.clear()
                            if svg:
                                wa_btn.append(svg)
                                wa_btn.append(" ")
                            wa_btn.append(str(c_btn_data["btn--wa"].get("text", "")))
                            _set_href(wa_btn, c_btn_data["btn--wa"].get("url"))
                    elif "btn--ghost" in c_btn_data:
                        ghost_btn = contact_box.find(class_="btn--ghost")
                        if ghost_btn:
                            svg = ghost_btn.find("svg")
                            ghost_btn.clear()
                            if svg:
                                ghost_btn.append(svg)
                                ghost_btn.append(" ")
                            ghost_btn.append(str(c_btn_data["btn--ghost"].get("text", "")))
                            _set_href(ghost_btn, c_btn_data["btn--ghost"].get("url"))

            meta_el = cta_grid_div.find(class_="cta-meta")
            if meta_el and "cta-meta" in cmn_data:
                svg = meta_el.find("svg")
                meta_el.clear()
                if svg:
                    meta_el.append(svg)
                    meta_el.append(" ")
                meta_el.append(str(cmn_data["cta-meta"]))

            author_box = cta_grid_div.find(class_="author-row")
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
    # Clean CSS comments (/* ... */) inside <style> blocks
    def _clean_css_comments(match):
        css = match.group(1)
        cleaned_css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
        return f"<style>{cleaned_css}</style>"

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

        for section in SECTIONS:
            data_path = os.path.join(ACTUAL_DATA_DIR, section["data"])
            rules_path = os.path.join(RULES_DIR, section["rules"])
            output_path_json = os.path.join(GENERATED_DIR, section["output"])

            if not os.path.exists(data_path):
                print(f"  ⚠ Skipping {section['data']} — file not found in actual_data/")
                continue
            if not os.path.exists(rules_path):
                print(f"  ⚠ Skipping {section['data']} — rules file not found in rules/")
                continue

            generate_section(args.role, args.city, args.state, args.geo_code, args.landmarks, args.dominentIindustries, args.model, data_path, rules_path, output_path_json)
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
                model               = "openrouter/deepseek/deepseek-v4-flash",
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
