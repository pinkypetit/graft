import os
import re
import json
import asyncio
import shutil
import uvicorn
import webbrowser
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="GRAFT Local")

# Mount static folder
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Supported English voices (Microsoft Edge-TTS) for reading the vocabulary and example sentences
VOICES = [
    {"id": "en-US-EmmaNeural", "name": "Emma (US Female - Default)"},
    {"id": "en-US-BrianNeural", "name": "Brian (US Male)"},
    {"id": "en-US-AvaNeural", "name": "Ava (US Female)"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (UK Female)"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (UK Male)"}
]

# Supported native languages for translations/definitions
NATIVE_LANGUAGES = [
    {"id": "english", "name": "English"},
    {"id": "spanish", "name": "Español"},
    {"id": "french", "name": "Français"},
    {"id": "german", "name": "Deutsch"}
]

# Global task state
task_state = {
    "status": "idle",  # "idle", "running", "done", "error"
    "category": "",
    "logs": []
}

log_queue = asyncio.Queue()

# Thread-safe/Async logging helper
def log_line(line: str):
    task_state["logs"].append(line)
    # Put line in the queue for any active SSE stream
    log_queue.put_nowait(line)

async def run_cmd_async(cmd):
    log_line(f"Executing command: {' '.join(cmd)}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded_line = line.decode('utf-8').strip()
        if decoded_line:
            log_line(decoded_line)
            
    code = await process.wait()
    if code != 0:
        log_line(f"Command failed with exit code: {code}")
        raise Exception(f"Command failed: {cmd}")
    log_line("Command finished successfully.")

import requests
async def translate_query_to_english(query: str):
    log_line(f"Translating search query to English keywords: '{query}'...")
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "qwen2.5:14b",
        "messages": [
            {"role": "user", "content": f"Translate this academic/technical search query into a simple English keyword query for arXiv. Output ONLY the translated query, no explanations or quotes.\nQuery: {query}"}
        ],
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }
    try:
        response = requests.post("http://localhost:11434/api/chat", headers=headers, json=payload, timeout=12)
        response.raise_for_status()
        translated = response.json()['message']['content'].strip()
        translated = translated.replace('"', '').replace("'", "")
        log_line(f"Translated query: '{translated}'")
        return translated
    except Exception as e:
        log_line(f"Failed to translate query: {e}. Using raw query.")
        return query

async def pipeline_worker(category: str, query: str, limit: int, voice: str, language: str):
    global task_state
    try:
        # Category directory
        cat_dir = f"papers/{category}"
        os.makedirs(cat_dir, exist_ok=True)
        
        # Check source papers availability
        pdf_count = len([f for f in os.listdir(cat_dir) if f.endswith(".pdf")])
        if pdf_count == 0 and not query:
            log_line("\nERROR: No PDF files found in category folder and no search query was provided.")
            log_line("Please drag and drop your PDFs first, or write a query/theme in the 'Búsqueda Automatizada en arXiv' field.")
            raise Exception("No PDF source files found and no arXiv search query specified.")
            
        # 1. Download papers dynamically if a query is provided
        if query:
            # Translate query to English dynamically using local LLM to fetch English papers
            english_query = await translate_query_to_english(query)
            
            log_line(f"\n--- STEP 1: DOWNLOADING PAPERS FOR '{category}' ---")
            # Check existing paper count. If count is < 8, download deficit
            pdf_count = len([f for f in os.listdir(cat_dir) if f.endswith(".pdf")])
            if pdf_count < 8:
                deficit = 8 - pdf_count
                log_line(f"Current paper count is {pdf_count}. Downloading {deficit} papers using English keywords '{english_query}'...")
                cmd = ["./venv/bin/python", "scripts/download_papers.py", "--query", english_query, "--category", category, "--limit", str(deficit)]
                await run_cmd_async(cmd)
            else:
                log_line(f"Vocabulary richness check: Category has {pdf_count} papers (>= 8). Skipping download.")
                
        # 2. Convert PDFs to MD
        log_line(f"\n--- STEP 2: CONVERTING PAPERS TO MARKDOWN ---")
        cmd = ["./venv/bin/python", "scripts/convert_papers.py"]
        await run_cmd_async(cmd)
        
        # 3. TF-IDF Ranking
        log_line(f"\n--- STEP 3: RUNNING TF-IDF VOCABULARY RANKER ---")
        cmd = ["./venv/bin/python", "scripts/rank_words.py"]
        await run_cmd_async(cmd)
        
        # 4. Generate curated data and TTS audios
        log_line(f"\n--- STEP 4: CURATING VOCABULARY VIA LOCAL LLM & SOTA TTS ---")
        cmd = ["./venv/bin/python", "scripts/generate_anki_data.py", "--category", category, "--limit", str(limit), "--voice", voice, "--language", language]
        await run_cmd_async(cmd)
        
        # 5. Compile Anki Deck
        log_line(f"\n--- STEP 5: COMPILING ANKI PACKAGE (.APKG) ---")
        cmd = ["./venv/bin/python", "scripts/build_deck.py", "--category", category]
        await run_cmd_async(cmd)
        
        task_state["status"] = "done"
        log_line("\n--- ALL STEPS COMPLETED SUCCESSFULLY ---")
        log_line(f"SUCCESS: Your Anki deck for '{category}' is ready for download!")
        
    except Exception as e:
        task_state["status"] = "error"
        log_line(f"\nERROR in pipeline execution: {e}")

@app.get("/")
def get_home():
    if os.path.exists("static/index.html"):
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Welcome to AnkiBrain Local</h1><p>Static index.html not found. Place it in the 'static/' directory.</p>")

@app.get("/api/languages")
def get_languages():
    return NATIVE_LANGUAGES

@app.get("/api/voices")
def get_voices():
    return VOICES

@app.get("/api/status")
def get_status():
    return {
        "status": task_state["status"],
        "category": task_state["category"]
    }

@app.post("/api/generate")
def start_generation(
    background_tasks: BackgroundTasks,
    category: str = Form(...),
    query: str = Form(""),
    limit: int = Form(30),
    voice: str = Form(...),
    language: str = Form("english")
):
    global task_state
    if task_state["status"] == "running":
        raise HTTPException(status_code=400, detail="A generation task is already running.")
        
    # Clean category name
    clean_cat = re.sub(r'[^a-zA-Z0-9_]', '', category.strip().lower().replace(" ", "_"))
    if not clean_cat:
        raise HTTPException(status_code=400, detail="Invalid category name.")
        
    # Reset state
    task_state["status"] = "running"
    task_state["category"] = clean_cat
    task_state["logs"] = []
    
    # Drain any leftover queue lines
    while not log_queue.empty():
        log_queue.get_nowait()
        
    log_line(f"Starting pipeline for category: '{clean_cat}' (Language: {language}, Voice: {voice}, Limit: {limit})")
    
    # Start worker in background
    background_tasks.add_task(pipeline_worker, clean_cat, query, limit, voice, language)
    
    return {"message": "Pipeline started successfully", "category": clean_cat}

@app.post("/api/upload")
async def upload_files(
    category: str = Form(...),
    files: list[UploadFile] = File(...)
):
    clean_cat = re.sub(r'[^a-zA-Z0-9_]', '', category.strip().lower().replace(" ", "_"))
    if not clean_cat:
        raise HTTPException(status_code=400, detail="Invalid category name.")
        
    dest_dir = f"papers/{clean_cat}"
    os.makedirs(dest_dir, exist_ok=True)
    
    saved_count = 0
    for file in files:
        if file.filename.endswith(".pdf"):
            dest_path = os.path.join(dest_dir, file.filename)
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_count += 1
            
    return {"message": f"Successfully uploaded {saved_count} PDFs for category '{clean_cat}'"}

@app.get("/api/download/{category}")
def download_deck(category: str):
    # Normalize category name (lowercase, strip, replace spaces/dashes with underscores)
    clean_cat = re.sub(r'[^a-zA-Z0-9_]', '', category.strip().lower().replace(" ", "_").replace("-", "_"))
    
    # Search for apkg in workspace
    for f in os.listdir("."):
        if f.endswith(".apkg"):
            # Normalize filename for comparison
            f_norm = re.sub(r'[^a-zA-Z0-9_]', '', f.lower().replace(" ", "_").replace("-", "_"))
            if clean_cat in f_norm:
                return FileResponse(f, media_type="application/octet-stream", filename=f)
            
    raise HTTPException(status_code=404, detail=f"No compiled Anki deck found for category '{category}'.")

@app.get("/api/logs")
def stream_logs():
    # SSE Stream generator
    async def log_generator():
        # First, yield all existing logs in history
        for line in task_state["logs"]:
            yield f"data: {line}\n\n"
            
        # Then, wait for and yield any new logs
        while True:
            line = await log_queue.get()
            yield f"data: {line}\n\n"
            log_queue.task_done()
            
            # Stop streaming if done or error
            if "SUCCESS:" in line or "ERROR in pipeline" in line:
                break
                
    return StreamingResponse(log_generator(), media_type="text/event-stream")

def open_browser():
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

if __name__ == "__main__":
    print("Starting AnkiBrain Local web server...")
    
    # Auto-open browser after a short delay
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.call_later(1.5, open_browser)
    
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
