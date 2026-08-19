import os
import sys
import json
import re
import subprocess
import asyncio
import logging
from typing import Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Ensure UTF-8 output encoding on Windows terminals and logging streams
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# =============================================================================
# 1. LOGGING CONFIGURATION
# =============================================================================
# Configure unbuffered, timestamped standard logging so messages are immediately
# captured by Vercel Runtime Logs / container stdout streams without memory buffering.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
logger = logging.getLogger("backend")
logger.info("Backend server logger initialized")

# =============================================================================
# 2. PATHS & ENVIRONMENT CONFIGURATION
# =============================================================================
# Determine directories dynamically based on deployment environment:
# - Local / VPS: Writes to project root & backend folders.
# - Vercel / Serverless: Writes temporary output files to `/tmp` (as filesystem is read-only).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

IS_VERCEL = "VERCEL" in os.environ or "AWS_LAMBDA_FUNCTION_NAME" in os.environ
if IS_VERCEL:
    import tempfile
    HTML_PAGES_DIR = os.path.join(tempfile.gettempdir(), "HTML pages")
else:
    HTML_PAGES_DIR = os.path.join(BACKEND_DIR, "HTML pages")

os.makedirs(HTML_PAGES_DIR, exist_ok=True)

# Load environment variables from .env file (for local dev)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# =============================================================================
# 3. FASTAPI APPLICATION & CORS SETUP
# =============================================================================
app = FastAPI(
    title="Location Page Pipeline Studio API",
    description="Backend API for generating, decomposing, and previewing localized ML landing pages",
    version="1.0.0"
)

# Enable CORS for frontend requests (local Vite dev server and deployed Vercel origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 4. DATA MODELS & CITY PRESETS
# =============================================================================
class PipelineRequest(BaseModel):
    role: str
    city: str
    state: str
    geo_code: str
    landmarks: str
    dominentIindustries: str
    model: str = "openrouter/deepseek/deepseek-v4-flash"
    output_filename: Optional[str] = None
    skip_generate: bool = False
    skip_widget: bool = False

# Default city presets available in the frontend UI for quick 1-click selection
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
        "landmarks": "Bandra-Kurla Complex (BKC), Nariman Point, Powai",
        "dominentIindustries": "Fintech & Banking, Media & Entertainment, E-Commerce, Logistics",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Bangalore",
        "role": "Machine Learning Engineer",
        "city": "Bangalore",
        "state": "Karnataka",
        "geo_code": "IN-KA",
        "landmarks": "Electronic City, Whitefield, Koramangala, Manyata Tech Park",
        "dominentIindustries": "SaaS, Artificial Intelligence, Aerospace, DeepTech Startups",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Hyderabad",
        "role": "Machine Learning Engineer",
        "city": "Hyderabad",
        "state": "Telangana",
        "geo_code": "IN-TG",
        "landmarks": "HITEC City, Gachibowli, Financial District",
        "dominentIindustries": "Pharma & Biotech, Enterprise IT, HealthTech, Defense Tech",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Delhi",
        "role": "Machine Learning Engineer",
        "city": "Delhi",
        "state": "Delhi",
        "geo_code": "IN-DL",
        "landmarks": "Connaught Place, Okhla Industrial Area, Nehru Place",
        "dominentIindustries": "GovTech, LegalTech, Media & Publishing, Logistics & Supply Chain",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Noida",
        "role": "Machine Learning Engineer",
        "city": "Noida",
        "state": "Uttar Pradesh",
        "geo_code": "IN-UP",
        "landmarks": "Sector 62 Tech Zone, Film City, Expressway IT Parks",
        "dominentIindustries": "Telecom, Mobile Software, Data Centers, Hardware Electronics",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Pune",
        "role": "Machine Learning Engineer",
        "city": "Pune",
        "state": "Maharashtra",
        "geo_code": "IN-MH",
        "landmarks": "Hinjewadi IT Park, Magarpatta City, Kharadi",
        "dominentIindustries": "Automotive Engineering, Manufacturing AI, EduTech, IT Services",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Chennai",
        "role": "Machine Learning Engineer",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "geo_code": "IN-TN",
        "landmarks": "OMR (IT Corridor), Tidel Park, Guindy Industrial Estate",
        "dominentIindustries": "Automobile Manufacturing, Healthcare AI, SaaS, DeepTech",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    },
    {
        "name": "Ahmedabad",
        "role": "Machine Learning Engineer",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "geo_code": "IN-GJ",
        "landmarks": "GIFT City, SG Highway, Prahlad Nagar, Sanand Industrial Area",
        "dominentIindustries": "Fintech, Pharmaceuticals, Textiles & Manufacturing, Chemical Tech",
        "model": "openrouter/deepseek/deepseek-v4-flash"
    }
]

# =============================================================================
# 5. HELPER FUNCTIONS
# =============================================================================
def find_html_file(filename: str) -> str:
    """
    Searches for an HTML file across all valid directory locations.
    Checks:
      1. HTML_PAGES_DIR (backend/HTML pages or /tmp/HTML pages on Vercel)
      2. BASE_DIR (project root)
      3. BACKEND_DIR (backend folder)
    Returns absolute path of the first match found, or defaults to HTML_PAGES_DIR.
    """
    candidates = [
        os.path.join(HTML_PAGES_DIR, filename),
        os.path.join(BASE_DIR, filename),
        os.path.join(BACKEND_DIR, filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.join(HTML_PAGES_DIR, filename)


def extract_code_components(html_content: str) -> dict:
    """
    Decomposes a compiled HTML file into distinct, syntax-highlightable blocks:
      - Title (<title>)
      - Main Content (<main> or <body>)
      - Embedded Styles (<style>)
      - Client Scripts (<script>)
      - Structured Data (<script type="application/ld+json">)
      - Head Meta Tags (<meta>, <link>)
      - Summary statistics (lines, size in KB)
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Step 1: Extract Document Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    # Step 2: Extract Main Content
    main_tag = soup.find("main")
    if main_tag:
        main_html = str(main_tag)
        main_inner_html = main_tag.decode_contents().strip()
    else:
        body_tag = soup.find("body")
        main_html = body_tag.decode_contents().strip() if body_tag else html_content
        main_inner_html = main_html

    # Step 3: Extract Embedded Stylesheets (<style>)
    styles = [s.string.strip() for s in soup.find_all("style") if s.string]
    css_content = "\n\n/* ========================================== */\n\n".join(styles) if styles else ""

    # Step 4: Extract JavaScript Code (<script> without ld+json)
    scripts = []
    for s in soup.find_all("script"):
        stype = s.get("type", "").lower()
        if "ld+json" not in stype and s.string:
            scripts.append(s.string.strip())
    js_content = "\n\n// ==========================================\n\n".join(scripts) if scripts else ""

    # Step 5: Extract JSON-LD Structured Data Schema
    json_ld_list = []
    for s in soup.find_all("script", type=re.compile(r"application/ld\+json", re.I)):
        raw_json = s.string.strip() if s.string else s.get_text().strip()
        try:
            parsed = json.loads(raw_json)
            json_ld_list.append(json.dumps(parsed, indent=2))
        except Exception:
            json_ld_list.append(raw_json)
    json_ld_content = "\n\n".join(json_ld_list) if json_ld_list else ""

    # Step 6: Extract Meta & Link Tags
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

# =============================================================================
# 6. API ENDPOINTS
# =============================================================================

# -----------------------------------------------------------------------------
# Endpoint: GET /health & GET /api/health
# Purpose:  Health check endpoint for Render, Vercel, uptime monitors, and load balancers.
# -----------------------------------------------------------------------------
@app.get("/health")
@app.get("/api/health")
def health_check():
    """
    Step 1: Verify server uptime and deployment runtime environment.
    Step 2: Return 200 OK JSON payload confirming the service is healthy.
    """
    return {
        "status": "healthy",
        "service": "location-page-pipeline-studio",
        "version": "1.0.0",
        "is_vercel": IS_VERCEL
    }


# -----------------------------------------------------------------------------
# Endpoint: GET /api/presets
# Purpose:  Returns list of predefined city configuration presets for the React UI.
# -----------------------------------------------------------------------------
@app.get("/api/presets")
def get_presets():
    """
    Step 1: Retrieve curated city metadata (role, city, state, geo_code, landmarks, industries, model).
    Step 2: Return JSON payload to populate the preset picker dropdown.
    """
    logger.info("Serving preset configurations list")
    return {"presets": PRESETS}


# -----------------------------------------------------------------------------
# Endpoint: GET /api/files
# Purpose:  Lists all available compiled HTML pages with metadata (size, mod time).
# -----------------------------------------------------------------------------
@app.get("/api/files")
def get_existing_files():
    """
    Step 1: Scan target directories (HTML_PAGES_DIR and project BASE_DIR).
    Step 2: Filter for '.html' files and deduplicate.
    Step 3: Collect file stats (size in KB, last modified timestamp, is_location_page flag).
    Step 4: Sort newest-first and return list to the frontend file inspector dropdown.
    """
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
    logger.info(f"Retrieved {len(files)} HTML files for file explorer")
    return {"files": files}


# -----------------------------------------------------------------------------
# Endpoint: GET /api/decompose
# Purpose:  Reads a specific HTML file and splits it into separate code tabs.
# -----------------------------------------------------------------------------
@app.get("/api/decompose")
def decompose_file(file: str = Query(..., description="Filename to decompose")):
    """
    Step 1: Locate the requested HTML file using find_html_file().
    Step 2: Validate file existence; raise 404 HTTPException if not found.
    Step 3: Read full UTF-8 HTML content.
    Step 4: Parse into components (Main HTML, CSS, JS, JSON-LD, Meta) using extract_code_components().
    Step 5: Return structured JSON for the React CodeViewer tabs and Preview iframe.
    """
    file_path = find_html_file(file)
    if not os.path.exists(file_path):
        logger.warning(f"File not found for decomposition: {file}")
        raise HTTPException(status_code=404, detail=f"File '{file}' not found.")
    
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    components = extract_code_components(html_content)
    components["filename"] = file
    components["preview_url"] = f"/api/preview/{file}"
    logger.info(f"Successfully decomposed {file} ({components['stats']['full_size_kb']} KB)")
    return components


# -----------------------------------------------------------------------------
# Endpoint: GET /api/preview/{filename}
# Purpose:  Serves the raw HTML document for iframe live previewing.
# -----------------------------------------------------------------------------
@app.get("/api/preview/{filename}")
def preview_file(filename: str):
    """
    Step 1: Locate the target HTML file using find_html_file().
    Step 2: Check existence; return 404 error if missing.
    Step 3: Read and return content as raw 'text/html' response for iframe rendering.
    """
    file_path = find_html_file(filename)
    if not os.path.exists(file_path):
        logger.warning(f"File not found for preview: {filename}")
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content, media_type="text/html")


# -----------------------------------------------------------------------------
# Endpoint: POST /api/run-pipeline
# Purpose:  Synchronously triggers the generation and compilation pipeline.
# -----------------------------------------------------------------------------
@app.post("/api/run-pipeline")
async def run_pipeline(req: PipelineRequest):
    """
    Step 1: Parse request payload and determine target output filename.
    Step 2: Construct CLI command calling 'backend/pipeline.py' with all parameters.
    Step 3: Spawn asynchronous subprocess and await execution completion.
    Step 4: Check return code and verify output HTML file creation.
    Step 5: Extract code components and return success response with logs and preview URL.
    """
    slug = req.city.lower().replace(" ", "-")
    output_filename = req.output_filename or f"location-page-{slug}.html"
    logger.info(f"Starting synchronous pipeline run for {req.city} -> {output_filename}")

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
            logger.error(f"Pipeline process returned non-zero code {proc.returncode}")
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
            logger.error(f"Expected output file not found at {output_path}")
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

        logger.info(f"Pipeline completed successfully for {req.city}")
        return components

    except Exception as e:
        logger.exception(f"Exception during pipeline execution: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# -----------------------------------------------------------------------------
# Endpoint: POST /api/run-pipeline-stream
# Purpose:  Streams real-time generation progress logs to React via Server-Sent Events (SSE).
# -----------------------------------------------------------------------------
@app.post("/api/run-pipeline-stream")
async def run_pipeline_stream(req: PipelineRequest):
    """
    Step 1: Build command arguments to launch 'backend/pipeline.py' in unbuffered (-u) mode.
    Step 2: Spawn async subprocess with piped stdout/stderr.
    Step 3: Yield SSE log events ('data: {"type": "log", "text": "..."}') line-by-line in real-time.
    Step 4: Await process completion; if successful, decompose generated HTML and yield 'complete' event.
    Step 5: If error occurs, yield 'error' event with diagnostic details.
    """
    slug = req.city.lower().replace(" ", "-")
    output_filename = req.output_filename or f"location-page-{slug}.html"
    logger.info(f"Initiating SSE streaming pipeline run for {req.city} -> {output_filename}")

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
            logger.info(f"SSE stream completed successfully for {req.city}")
            msg = json.dumps({"type": "complete", "data": components})
            yield f"data: {msg}\n\n"
        else:
            logger.error(f"SSE stream failed with exit code {proc.returncode}")
            msg = json.dumps({"type": "error", "text": "Pipeline process failed", "code": proc.returncode})
            yield f"data: {msg}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# =============================================================================
# 7. LOCAL SERVER ENTRYPOINT
# =============================================================================
# Run directly with `python backend/server.py` or `python run_studio.py`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
