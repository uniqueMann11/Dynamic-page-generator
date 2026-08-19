import os
import sys
import json
import re
import subprocess
import asyncio
from typing import Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

IS_VERCEL = "VERCEL" in os.environ or "AWS_LAMBDA_FUNCTION_NAME" in os.environ
if IS_VERCEL:
    import tempfile
    HTML_PAGES_DIR = os.path.join(tempfile.gettempdir(), "HTML pages")
else:
    HTML_PAGES_DIR = os.path.join(BASE_DIR, "HTML pages")

os.makedirs(HTML_PAGES_DIR, exist_ok=True)

load_dotenv(os.path.join(BASE_DIR, ".env"))

app = FastAPI(title="Location Page Pipeline Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PRESETS = [
    {
        "name": "Gurgaon",
        "role": "Machine Learning Engineer",
        "city": "Gurgaon",
        "state": "Haryana",
        "geo_code": "IN-HR",
        "landmarks": "DLF Cyber City, Cyber Hub, Golf Course Road",
        "dominentIindustries": "IT/BPO, Management Consulting, Automotive HQs",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Mumbai",
        "role": "Machine Learning Engineer",
        "city": "Mumbai",
        "state": "Maharashtra",
        "geo_code": "IN-MH",
        "landmarks": "Marine Drive, Bandra Kurla Complex (BKC), Nariman Point",
        "dominentIindustries": "Financial Services, Banking, Media and Entertainment, Technology",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Delhi",
        "role": "Machine Learning Engineer",
        "city": "Delhi",
        "state": "Delhi",
        "geo_code": "IN-DL",
        "landmarks": "Connaught Place, India Gate, Aerocity",
        "dominentIindustries": "Government Tech, E-Commerce, Logistics, SaaS",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Ahmedabad",
        "role": "Machine Learning Engineer",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "geo_code": "IN-GJ",
        "landmarks": "Sabarmati Riverfront, GIFT City, SG Highway",
        "dominentIindustries": "IT and Software, Textiles, Pharmaceuticals, Fintech",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Bangalore",
        "role": "Machine Learning Engineer",
        "city": "Bangalore",
        "state": "Karnataka",
        "geo_code": "IN-KA",
        "landmarks": "Electronic City, Whitefield, Indiranagar, Koramangala",
        "dominentIindustries": "AI and DeepTech, IT Services, SaaS, Venture Capital Startups",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Hyderabad",
        "role": "Machine Learning Engineer",
        "city": "Hyderabad",
        "state": "Telangana",
        "geo_code": "IN-TG",
        "landmarks": "HITEC City, Gachibowli, Financial District",
        "dominentIindustries": "Pharma and Biotech, IT Services, Enterprise AI, Cloud",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Chennai",
        "role": "Machine Learning Engineer",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "geo_code": "IN-TN",
        "landmarks": "OMR (IT Corridor), T. Nagar, Guindy",
        "dominentIindustries": "Automotive Engineering, SaaS, HealthTech, Hardware and Manufacturing",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Pune",
        "role": "Machine Learning Engineer",
        "city": "Pune",
        "state": "Maharashtra",
        "geo_code": "IN-MH",
        "landmarks": "Hinjawadi IT Park, Magarpatta City, Viman Nagar",
        "dominentIindustries": "Automotive R and D, IT Services, Engineering and Manufacturing",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Kolkata",
        "role": "Machine Learning Engineer",
        "city": "Kolkata",
        "state": "West Bengal",
        "geo_code": "IN-WB",
        "landmarks": "Salt Lake Sector V, New Town, Park Street",
        "dominentIindustries": "IT Services, Analytics and Research, Banking, Fintech",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    }
]

class PipelineRequest(BaseModel):
    role: str = "Machine Learning Engineer"
    city: str
    state: str
    geo_code: str
    landmarks: str
    dominentIindustries: str
    model: str = "openrouter/deepseek/deepseek-v4-flash"
    output_filename: Optional[str] = None
    skip_generate: bool = False
    skip_widget: bool = False

def find_html_file(filename: str) -> str:
    if os.path.isabs(filename):
        return filename
    in_html_pages = os.path.join(HTML_PAGES_DIR, filename)
    if os.path.exists(in_html_pages):
        return in_html_pages
    in_base = os.path.join(BASE_DIR, filename)
    if os.path.exists(in_base):
        return in_base
    return in_html_pages

def extract_code_components(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Title
    title_tag = soup.find("title")
    title = title_tag.get_text() if title_tag else ""

    # 2. Main HTML
    main_tag = soup.find("main")
    main_html = str(main_tag) if main_tag else ""
    main_inner_html = "".join(str(c) for c in main_tag.children).strip() if main_tag else ""

    # 3. CSS (<style>)
    styles = [s.get_text().strip() for s in soup.find_all("style") if s.get_text().strip()]
    css_content = "\n\n/* ========================================== */\n\n".join(styles) if styles else ""

    # 4. JavaScript (<script> excluding application/ld+json)
    scripts = []
    for s in soup.find_all("script"):
        stype = s.get("type", "").lower()
        if "application/ld+json" not in stype and s.string and s.string.strip():
            scripts.append(s.string.strip())
    js_content = "\n\n// ==========================================\n\n".join(scripts) if scripts else ""

    # 5. JSON-LD structured data
    json_ld_list = []
    for s in soup.find_all("script", type=re.compile(r"application/ld\+json", re.I)):
        raw_json = s.string.strip() if s.string else s.get_text().strip()
        try:
            parsed = json.loads(raw_json)
            json_ld_list.append(json.dumps(parsed, indent=2))
        except Exception:
            json_ld_list.append(raw_json)
    json_ld_content = "\n\n".join(json_ld_list) if json_ld_list else ""

    # 6. Meta tags
    meta_tags = [str(m) for m in soup.find_all(["meta", "link"])]
    meta_content = "\n".join(meta_tags)

    return {
        "title": title,
        "full_html": html_content,
        "main_html": main_html,
        "main_inner_html": main_inner_html,
        "css": css_content,
        "js": js_content,
        "json_ld": json_ld_content,
        "meta": meta_content,
        "stats": {
            "full_lines": len(html_content.splitlines()),
            "full_size_kb": round(len(html_content.encode("utf-8")) / 1024, 2),
            "main_lines": len(main_html.splitlines()),
            "css_lines": len(css_content.splitlines()),
            "js_lines": len(js_content.splitlines()),
            "json_ld_lines": len(json_ld_content.splitlines()),
        }
    }

@app.get("/api/presets")
def get_presets():
    return {"presets": PRESETS}

@app.get("/api/files")
def get_existing_files():
    files = []
    seen = set()
    dirs_to_scan = [HTML_PAGES_DIR, BASE_DIR]
    for d in dirs_to_scan:
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if f.endswith(".html") and f not in seen:
                seen.add(f)
                fpath = os.path.join(d, f)
                size_kb = round(os.path.getsize(fpath) / 1024, 2)
                mtime = os.path.getmtime(fpath)
                files.append({
                    "filename": f,
                    "size_kb": size_kb,
                    "modified": mtime,
                    "is_location_page": f.startswith("location-page-") or "machine-learning" in f
                })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"files": files}

@app.get("/api/decompose")
def decompose_file(file: str = Query(..., description="Filename to decompose")):
    file_path = find_html_file(file)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{file}' not found.")
    
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    components = extract_code_components(html_content)
    components["filename"] = file
    components["preview_url"] = f"/api/preview/{file}"
    return components

@app.get("/api/preview/{filename}")
def preview_file(filename: str):
    file_path = find_html_file(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content, media_type="text/html")

@app.post("/api/run-pipeline")
async def run_pipeline(req: PipelineRequest):
    slug = req.city.lower().replace(" ", "-")
    output_filename = req.output_filename or f"location-page-{slug}.html"
    output_path = find_html_file(output_filename)

    cmd = [
        sys.executable,
        os.path.join(BACKEND_DIR, "pipeline.py"),
        "--role", req.role,
        "--city", req.city,
        "--state", req.state,
        "--geo-code", req.geo_code,
        "--landmarks", req.landmarks,
        "--dominentIindustries", req.dominentIindustries,
        "--model", req.model,
        "--output", output_filename,
    ]

    if req.skip_generate:
        cmd.append("--skip-generate")
    if req.skip_widget:
        cmd.append("--skip-widget")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=BASE_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": stderr_text or stdout_text,
                    "logs": stdout_text,
                    "cmd": " ".join(cmd)
                }
            )

        output_path = find_html_file(output_filename)
        if not os.path.exists(output_path):
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Output file '{output_filename}' was not created.",
                    "logs": stdout_text
                }
            )

        with open(output_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        components = extract_code_components(html_content)
        components["success"] = True
        components["filename"] = output_filename
        components["preview_url"] = f"/api/preview/{output_filename}"
        components["logs"] = stdout_text

        return components

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post("/api/run-pipeline-stream")
async def run_pipeline_stream(req: PipelineRequest):
    slug = req.city.lower().replace(" ", "-")
    output_filename = req.output_filename or f"location-page-{slug}.html"

    cmd = [
        sys.executable,
        "-u",
        os.path.join(BACKEND_DIR, "pipeline.py"),
        "--role", req.role,
        "--city", req.city,
        "--state", req.state,
        "--geo-code", req.geo_code,
        "--landmarks", req.landmarks,
        "--dominentIindustries", req.dominentIindustries,
        "--model", req.model,
        "--output", output_filename,
    ]

    if req.skip_generate:
        cmd.append("--skip-generate")
    if req.skip_widget:
        cmd.append("--skip-widget")

    async def event_generator() -> AsyncGenerator[str, None]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=BASE_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        log_lines = []
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace")
            log_lines.append(line_str)
            msg = json.dumps({"type": "log", "text": line_str})
            yield f"data: {msg}\n\n"

        await proc.wait()

        output_path = find_html_file(output_filename)
        if proc.returncode == 0 and os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            components = extract_code_components(html_content)
            components["success"] = True
            components["filename"] = output_filename
            components["preview_url"] = f"/api/preview/{output_filename}"
            components["logs"] = "".join(log_lines)
            msg = json.dumps({"type": "complete", "data": components})
            yield f"data: {msg}\n\n"
        else:
            msg = json.dumps({"type": "error", "text": "Pipeline process failed", "code": proc.returncode})
            yield f"data: {msg}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Static files handled by Vite dev server (React frontend)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
