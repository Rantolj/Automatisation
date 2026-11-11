"""
=============================================================================
PHASE 1 - API Backend Python (Proof of Concept)
=============================================================================

Objectif : Valider le flux de bout en bout
- Recevoir un fichier depuis une app mobile
- Le traiter côté serveur
- Retourner un résultat exploitable

Technologie : FastAPI
Justification : 
  - Léger et performant (basé sur Starlette + Uvicorn)
  - Documentation automatique (Swagger UI)
  - Validation native avec Pydantic
  - Support async natif
  - Idéal pour les APIs REST modernes

=============================================================================
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import os
import tempfile
from datetime import datetime
from pathlib import Path
import asyncio
import time
import uuid
import re

import anyio

# Import des services de traitement
from services.file_processor import FileProcessor
from services.statistical_summary import StatisticalSummaryService

# Import de la configuration
from config import settings

# =============================================================================
# INITIALISATION DE L'APPLICATION
# =============================================================================

app = FastAPI(
    title=settings.app_name,
    description="Backend Python pour traitement de fichiers depuis application mobile",
    version=settings.api_version
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Création des dossiers s'ils n'existent pas
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)

# Instances des services de traitement
processor = FileProcessor()
statistical_service = StatisticalSummaryService()

# =============================================================================
# VARIABLES DEPUIS LA CONFIG
# =============================================================================

STATISTICAL_EXTENSIONS = settings.statistical_extensions
ALLOWED_EXTENSIONS = settings.allowed_extensions
MAX_FILE_SIZE_BYTES = settings.max_file_size_bytes
PROCESS_TIMEOUT_SECONDS = settings.process_timeout_seconds
RATE_LIMIT_REQUESTS_PER_WINDOW = settings.rate_limit_requests_per_window
RATE_LIMIT_WINDOW_SECONDS = settings.rate_limit_window_seconds
UPLOAD_DIR = settings.upload_dir
OUTPUT_DIR = settings.output_dir

# Stockage en mémoire pour rate limiting (MVP)
_rate_limit_store = {}


# =============================================================================
# ENDPOINTS
# =============================================================================


def _wants_html(request: Request) -> bool:
    """Retourne True si le client préfère une réponse HTML (typiquement un navigateur)."""
    accept = (request.headers.get("accept") or "").lower()
    return ("text/html" in accept) and ("application/json" not in accept)


def _sanitize_filename(filename: str) -> str:
    """Sanitise un nom de fichier pour éviter chemins et caractères dangereux."""
    # Retirer les chemins potentiels
    name = os.path.basename(filename)
    # Remplacer caractères non sûrs
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    # Empêcher les noms vides
    return name or "uploaded_file"


def _error_payload(
    *,
    request_id: str,
    error_code: str,
    message: str,
    hint: str | None = None,
    details: dict | None = None,
):
    payload = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "request_id": request_id,
    }
    if hint:
        payload["hint"] = hint
    if details:
        payload["details"] = details
    return payload


def _error_html(*, request_id: str, error_code: str, message: str, hint: str | None = None) -> str:
    hint_html = f"<p><b>Suggestion</b> : {hint}</p>" if hint else ""
    return f"""<!doctype html>
<html lang=\"fr\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Erreur API</title>
  </head>
  <body style=\"font-family: sans-serif; margin: 24px;\">
    <h1>Une erreur est survenue</h1>
    <p><b>Code</b> : {error_code}</p>
    <p><b>Message</b> : {message}</p>
    {hint_html}
    <hr />
    <p><b>Request ID</b> : {request_id}</p>
  </body>
</html>"""


def _home_page_html() -> str:
        return """<!doctype html>
<html lang="fr">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>API Automatisation</title>
        <style>
            :root {
                --bg: #0f172a;
                --panel: rgba(15, 23, 42, 0.82);
                --panel-2: rgba(30, 41, 59, 0.9);
                --text: #e2e8f0;
                --muted: #94a3b8;
                --accent: #38bdf8;
                --accent-2: #22c55e;
                --border: rgba(148, 163, 184, 0.18);
                --danger: #fb7185;
            }

            * { box-sizing: border-box; }
            body {
                margin: 0;
                min-height: 100vh;
                font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                color: var(--text);
                background:
                    radial-gradient(circle at top left, rgba(56, 189, 248, 0.22), transparent 30%),
                    radial-gradient(circle at top right, rgba(34, 197, 94, 0.14), transparent 28%),
                    linear-gradient(160deg, #020617 0%, #0f172a 50%, #111827 100%);
            }

            .shell {
                width: min(1180px, calc(100% - 32px));
                margin: 0 auto;
                padding: 24px 0 48px;
            }

            .hero {
                display: grid;
                grid-template-columns: 1.25fr 0.75fr;
                gap: 20px;
                align-items: stretch;
            }

            .card {
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 24px;
                box-shadow: 0 24px 80px rgba(2, 6, 23, 0.45);
                backdrop-filter: blur(18px);
            }

            .hero-main { padding: 28px; }
            .kicker {
                display: inline-flex;
                gap: 8px;
                align-items: center;
                padding: 8px 12px;
                border-radius: 999px;
                border: 1px solid var(--border);
                background: rgba(15, 23, 42, 0.52);
                color: var(--muted);
                font-size: 0.92rem;
            }

            h1 {
                margin: 18px 0 12px;
                font-size: clamp(2rem, 4vw, 4.2rem);
                line-height: 0.98;
                letter-spacing: -0.04em;
            }

            .lead {
                margin: 0;
                max-width: 62ch;
                color: var(--muted);
                font-size: 1.02rem;
                line-height: 1.7;
            }

            .metrics {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 12px;
                margin-top: 22px;
            }

            .metric {
                padding: 16px;
                border-radius: 18px;
                background: rgba(15, 23, 42, 0.62);
                border: 1px solid var(--border);
            }

            .metric .label { color: var(--muted); font-size: 0.82rem; }
            .metric .value { margin-top: 8px; font-size: 1.2rem; font-weight: 700; }

            .side {
                padding: 20px;
                display: grid;
                gap: 12px;
            }

            .side h2 {
                margin: 0 0 6px;
                font-size: 1.1rem;
            }

            .check {
                display: flex;
                gap: 12px;
                align-items: flex-start;
                padding: 14px;
                border-radius: 16px;
                border: 1px solid var(--border);
                background: rgba(15, 23, 42, 0.54);
            }

            .check .dot {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-top: 6px;
                background: var(--accent-2);
                box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.12);
            }

            .workspace {
                margin-top: 20px;
                display: grid;
                grid-template-columns: 0.9fr 1.1fr;
                gap: 18px;
            }

            .panel {
                padding: 22px;
            }

            .panel h2 {
                margin: 0 0 8px;
                font-size: 1.2rem;
            }

            .panel p.sub {
                margin: 0 0 18px;
                color: var(--muted);
            }

            .dropzone {
                border: 1.5px dashed rgba(56, 189, 248, 0.45);
                border-radius: 20px;
                min-height: 240px;
                display: grid;
                place-items: center;
                text-align: center;
                padding: 22px;
                background: linear-gradient(180deg, rgba(15, 23, 42, 0.65), rgba(15, 23, 42, 0.35));
                transition: 180ms ease;
            }

            .dropzone.dragover {
                transform: translateY(-2px);
                border-color: var(--accent);
                box-shadow: 0 0 0 6px rgba(56, 189, 248, 0.1);
            }

            .dropzone strong {
                display: block;
                font-size: 1.05rem;
                margin-bottom: 8px;
            }

            .dropzone small { color: var(--muted); }

            .actions {
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
                margin-top: 16px;
            }

            .btn {
                appearance: none;
                border: 0;
                border-radius: 14px;
                padding: 12px 16px;
                font-weight: 700;
                cursor: pointer;
                transition: transform 120ms ease, opacity 120ms ease, background 120ms ease;
            }

            .btn:hover { transform: translateY(-1px); }
            .btn-primary { background: linear-gradient(135deg, var(--accent), #0ea5e9); color: #02111d; }
            .btn-secondary { background: rgba(148, 163, 184, 0.18); color: var(--text); border: 1px solid var(--border); }
            .btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

            input[type="file"] { display: none; }

            .result {
                min-height: 240px;
                background: rgba(2, 6, 23, 0.4);
                border: 1px solid var(--border);
                border-radius: 20px;
                padding: 18px;
                overflow: auto;
            }

            .result pre {
                margin: 0;
                white-space: pre-wrap;
                word-break: break-word;
                color: #dbeafe;
                font-size: 0.93rem;
                line-height: 1.6;
            }

            .status {
                margin-top: 14px;
                min-height: 22px;
                color: var(--muted);
            }

            .status.error { color: var(--danger); }
            .pill {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 8px 12px;
                border-radius: 999px;
                border: 1px solid var(--border);
                background: rgba(15, 23, 42, 0.5);
                color: var(--muted);
                font-size: 0.84rem;
            }

            @media (max-width: 920px) {
                .hero, .workspace { grid-template-columns: 1fr; }
                .metrics { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="shell">
            <section class="hero">
                <div class="card hero-main">
                    <div class="kicker">API Automatisation <span class="pill">FastAPI</span></div>
                    <h1>Une vraie page front pour envoyer un fichier et lire le résumé.</h1>
                    <p class="lead">
                        Cette interface permet de tester l’API sans Postman ni terminal. Tu glisses un fichier,
                        tu l’envoies, et le résultat s’affiche directement dans le navigateur.
                    </p>
                    <div class="metrics">
                        <div class="metric">
                            <div class="label">Formats</div>
                            <div class="value">CSV, JSON, TXT, XLSX</div>
                        </div>
                        <div class="metric">
                            <div class="label">Réponse</div>
                            <div class="value">Résultat JSON lisible</div>
                        </div>
                        <div class="metric">
                            <div class="label">URL</div>
                            <div class="value">http://localhost:8000</div>
                        </div>
                    </div>
                </div>
                <aside class="card side">
                    <div>
                        <h2>Ce que fait la page</h2>
                        <p class="lead" style="font-size: .95rem; line-height: 1.65;">
                            Elle envoie le fichier vers <code>/process</code> et affiche la réponse API en brut.
                        </p>
                    </div>
                    <div class="check"><span class="dot"></span><div><strong>Upload immédiat</strong><div style="color: var(--muted); margin-top: 4px;">Tu sélectionnes un fichier puis tu cliques sur envoyer.</div></div></div>
                    <div class="check"><span class="dot"></span><div><strong>Retour visuel</strong><div style="color: var(--muted); margin-top: 4px;">La réponse s’affiche en JSON formaté dans le panneau de droite.</div></div></div>
                    <div class="check"><span class="dot"></span><div><strong>Compatible mobile</strong><div style="color: var(--muted); margin-top: 4px;">L’interface reste lisible sur téléphone et tablette.</div></div></div>
                </aside>
            </section>

            <section class="workspace">
                <div class="card panel">
                    <h2>Envoyer un fichier</h2>
                    <p class="sub">Formats acceptés selon le backend : <strong>.csv</strong>, <strong>.xlsx</strong>, <strong>.json</strong>, <strong>.txt</strong>.</p>

                    <div id="dropzone" class="dropzone">
                        <div>
                            <strong>Glisse ton fichier ici</strong>
                            <small>ou clique pour le sélectionner</small>
                            <div class="actions">
                                <label class="btn btn-secondary" for="fileInput">Choisir un fichier</label>
                                <button id="sendBtn" class="btn btn-primary" type="button">Envoyer</button>
                            </div>
                            <input id="fileInput" type="file" />
                            <div id="fileName" class="status">Aucun fichier sélectionné.</div>
                        </div>
                    </div>

                    <div id="status" class="status"></div>
                </div>

                <div class="card panel">
                    <h2>Résultat</h2>
                    <p class="sub">La réponse de l’API s’affiche ici.</p>
                    <div class="result"><pre id="result">Aucun résultat pour le moment.</pre></div>
                </div>
            </section>
        </div>

        <script>
            const fileInput = document.getElementById('fileInput');
            const fileName = document.getElementById('fileName');
            const result = document.getElementById('result');
            const statusBox = document.getElementById('status');
            const sendBtn = document.getElementById('sendBtn');
            const dropzone = document.getElementById('dropzone');
            let selectedFile = null;

            function setStatus(message, isError = false) {
                statusBox.textContent = message || '';
                statusBox.classList.toggle('error', Boolean(isError));
            }

            function prettyPrint(value) {
                return JSON.stringify(value, null, 2);
            }

            fileInput.addEventListener('change', () => {
                selectedFile = fileInput.files[0] || null;
                fileName.textContent = selectedFile ? `Fichier sélectionné : ${selectedFile.name}` : 'Aucun fichier sélectionné.';
                setStatus('');
            });

            dropzone.addEventListener('click', (event) => {
                if (event.target === dropzone) {
                    fileInput.click();
                }
            });

            dropzone.addEventListener('dragover', (event) => {
                event.preventDefault();
                dropzone.classList.add('dragover');
            });

            dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

            dropzone.addEventListener('drop', (event) => {
                event.preventDefault();
                dropzone.classList.remove('dragover');
                if (event.dataTransfer.files.length) {
                    selectedFile = event.dataTransfer.files[0];
                    fileInput.files = event.dataTransfer.files;
                    fileName.textContent = `Fichier sélectionné : ${selectedFile.name}`;
                    setStatus('');
                }
            });

            async function sendFile() {
                if (!selectedFile) {
                    setStatus('Sélectionne un fichier avant de l’envoyer.', true);
                    return;
                }

                const formData = new FormData();
                formData.append('file', selectedFile);
                sendBtn.disabled = true;
                setStatus('Envoi en cours...');
                result.textContent = 'Traitement en cours...';

                try {
                    const response = await fetch('/process', {
                        method: 'POST',
                        body: formData,
                    });
                    const payload = await response.json();
                    result.textContent = prettyPrint(payload);
                    if (!response.ok) {
                        setStatus(`Erreur HTTP ${response.status}`, true);
                        return;
                    }
                    setStatus('Fichier traité avec succès.');
                } catch (error) {
                    result.textContent = String(error);
                    setStatus('Impossible de joindre l’API.', true);
                } finally {
                    sendBtn.disabled = false;
                }
            }

            sendBtn.addEventListener('click', sendFile);
        </script>
    </body>
</html>"""


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Ne pas limiter l'accès à /docs et /redoc (aide dev)
    if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc") or request.url.path.startswith("/openapi"):
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _rate_limit_store.get(ip, [])
    timestamps = [t for t in timestamps if t >= window_start]
    if len(timestamps) >= RATE_LIMIT_REQUESTS_PER_WINDOW:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        retry_after = 5
        payload = _error_payload(
            request_id=request_id,
            error_code="RATE_LIMIT",
            message="Trop de requêtes, veuillez réessayer plus tard",
            hint=f"Attendez {retry_after} secondes puis réessayez.",
            details={"limit": RATE_LIMIT_REQUESTS_PER_WINDOW, "window_seconds": RATE_LIMIT_WINDOW_SECONDS},
        )
        if _wants_html(request):
            return HTMLResponse(_error_html(request_id=request_id, error_code="RATE_LIMIT", message=payload["message"], hint=payload.get("hint")), status_code=429, headers={"Retry-After": str(retry_after), "x-request-id": request_id})
        return JSONResponse(payload, status_code=429, headers={"Retry-After": str(retry_after), "x-request-id": request_id})

    timestamps.append(now)
    _rate_limit_store[ip] = timestamps
    return await call_next(request)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    # Supporter detail en str ou dict
    if isinstance(exc.detail, dict):
        error_code = exc.detail.get("error_code", "HTTP_ERROR")
        message = exc.detail.get("message", "Erreur")
        hint = exc.detail.get("hint")
        details = exc.detail.get("details")
    else:
        error_code = "HTTP_ERROR"
        message = str(exc.detail)
        hint = None
        details = None

    payload = _error_payload(request_id=request_id, error_code=error_code, message=message, hint=hint, details=details)
    if _wants_html(request):
        return HTMLResponse(_error_html(request_id=request_id, error_code=error_code, message=message, hint=hint), status_code=exc.status_code)
    return JSONResponse(payload, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    payload = _error_payload(
        request_id=request_id,
        error_code="VALIDATION_ERROR",
        message="Requête invalide",
        hint="Vérifiez les champs requis et le type de données.",
        details={"errors": exc.errors()},
    )
    if _wants_html(request):
        return HTMLResponse(_error_html(request_id=request_id, error_code="VALIDATION_ERROR", message=payload["message"], hint=payload.get("hint")), status_code=422)
    return JSONResponse(payload, status_code=422)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    payload = _error_payload(
        request_id=request_id,
        error_code="INTERNAL_ERROR",
        message="Erreur interne du serveur",
        hint="Réessayez. Si le problème persiste, contactez le support avec le Request ID.",
    )
    if _wants_html(request):
        return HTMLResponse(_error_html(request_id=request_id, error_code="INTERNAL_ERROR", message=payload["message"], hint=payload.get("hint")), status_code=500)
    return JSONResponse(payload, status_code=500)

@app.get("/")
async def root(request: Request):
    """
    Point d'entrée racine - Vérification que l'API est en ligne
    
    Usage : Health check depuis l'app mobile ou monitoring
    """
    if _wants_html(request):
        return HTMLResponse(_home_page_html())
    return {
        "status": "online",
        "message": "API Automatisation - Phase 1",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "upload": "/upload (POST)",
            "process": "/process (POST)"
        }
    }


@app.get("/health")
async def health_check():
    """
    Endpoint de santé - Utilisé pour vérifier la disponibilité du service
    
    Retourne :
        - status : état du service
        - uptime_info : informations de disponibilité
    """
    return {
        "status": "healthy",
        "service": "file-processing-api",
        "version": "1.0.0"
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint d'upload - Reçoit un fichier et le sauvegarde
    
    Flux :
        1. Réception du fichier (multipart/form-data)
        2. Validation basique (présence, nom)
        3. Sauvegarde temporaire
        4. Retour des métadonnées
    
    Args:
        file: Fichier uploadé depuis l'application mobile
    
    Returns:
        JSON avec les informations du fichier sauvegardé
    """
    
    # Validation basique : le fichier a-t-il un nom ?
    if not file.filename:
        raise HTTPException(status_code=400, detail={"error_code": "MISSING_FILENAME", "message": "Le fichier doit avoir un nom"})

    original_name = file.filename
    sanitized_name = _sanitize_filename(original_name)
    extension = Path(sanitized_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail={
                "error_code": "UNSUPPORTED_FORMAT",
                "message": f"Format non supporté: {extension}",
                "hint": "Formats acceptés : .csv, .xlsx, .xls, .json, .txt",
                "details": {"allowed_extensions": sorted(ALLOWED_EXTENSIONS)},
            },
        )
    
    # Génération d'un nom unique pour éviter les collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{sanitized_name}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    # Sauvegarde du fichier
    try:
        contents = await file.read()
        file_size = len(contents)
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "error_code": "FILE_TOO_LARGE",
                    "message": f"Fichier trop volumineux (max {MAX_FILE_SIZE_BYTES} bytes)",
                    "hint": "Réduisez la taille du fichier ou divisez-le en plusieurs fichiers.",
                    "details": {"max_bytes": MAX_FILE_SIZE_BYTES, "actual_bytes": file_size},
                },
            )

        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail={"error_code": "UPLOAD_FAILED", "message": "Erreur lors de la sauvegarde", "details": {"reason": str(e)}})
    
    return {
        "success": True,
        "message": "Fichier uploadé avec succès",
        "file_info": {
            "original_name": original_name,
            "sanitized_name": sanitized_name,
            "saved_name": safe_filename,
            "size_bytes": file_size,
            "size_readable": _format_size(file_size),
            "content_type": file.content_type,
        }
    }


@app.post("/process")
async def process_file(file: UploadFile = File(...)):
    """
    Endpoint principal - Upload + Traitement en une seule requête
    
    C'est l'endpoint clé de la V1 :
        1. Reçoit le fichier
        2. Détecte le type (Excel, CSV, autre)
        3. Applique le traitement approprié
        4. Retourne le résultat structuré
    
    Traitement V1 :
        - Excel/CSV : Résumé statistique complet (structure, colonnes, alertes)
        - Texte : Comptage lignes/mots/caractères
        - JSON : Validation et structure
        - Autres : Métadonnées basiques
    
    Args:
        file: Fichier à traiter (Excel, CSV, ou autre)
    
    Returns:
        JSON avec le résumé statistique ou résultat de traitement
    """
    
    if not file.filename:
        raise HTTPException(status_code=400, detail={"error_code": "MISSING_FILE", "message": "Fichier requis"})

    original_name = file.filename
    sanitized_name = _sanitize_filename(original_name)
    extension = Path(sanitized_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail={
                "error_code": "UNSUPPORTED_FORMAT",
                "message": f"Format non supporté: {extension}",
                "hint": "Formats acceptés : .csv, .xlsx, .xls, .json, .txt",
                "details": {"allowed_extensions": sorted(ALLOWED_EXTENSIONS)},
            },
        )
    
    # Lecture du contenu
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error_code": "READ_FAILED", "message": "Erreur de lecture du fichier", "details": {"reason": str(e)}})

    file_size = len(contents)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "message": f"Fichier trop volumineux (max 10MB)",
                "hint": "Réduisez la taille du fichier ou divisez-le en plusieurs fichiers.",
                "details": {"max_bytes": MAX_FILE_SIZE_BYTES, "actual_bytes": file_size},
            },
        )

    def _process_sync():
        if extension in STATISTICAL_EXTENSIONS:
            return statistical_service.analyze(filename=sanitized_name, content=contents, content_type=file.content_type)
        return processor.process(filename=sanitized_name, content=contents, content_type=file.content_type)

    try:
        result = await asyncio.wait_for(anyio.to_thread.run_sync(_process_sync), timeout=PROCESS_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={
                "error_code": "TIMEOUT",
                "message": "Le traitement a dépassé le temps maximum",
                "hint": "Essayez de réduire la taille du fichier ou de le segmenter.",
                "details": {"timeout_seconds": PROCESS_TIMEOUT_SECONDS},
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error_code": "PROCESSING_FAILED", "message": "Erreur de traitement", "details": {"reason": str(e)}})

    # Si le service retourne une erreur structurée, mapper en code HTTP cohérent
    if isinstance(result, dict) and result.get("success") is False:
        error_code = result.get("error_code") or "PROCESSING_ERROR"
        message = result.get("message") or result.get("error") or "Erreur de traitement"
        hint = result.get("hint")
        details = result.get("details")
        status_map = {
            "UNSUPPORTED_FORMAT": 415,
            "FILE_TOO_LARGE": 413,
            "LIMITS_EXCEEDED": 422,
            "INVALID_ENCODING": 422,
            "INVALID_CSV": 422,
        }
        raise HTTPException(status_code=status_map.get(error_code, 422), detail={"error_code": error_code, "message": message, "hint": hint, "details": details})
    
    return {
        "success": result.get("success", True),
        "filename": original_name,
        "sanitized_filename": sanitized_name,
        "file_size": _format_size(file_size),
        "processing_result": result,
        "processed_at": datetime.now().isoformat()
    }


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def _format_size(size_bytes: int) -> str:
    """
    Convertit une taille en bytes vers un format lisible
    
    Exemple : 1536 -> "1.50 KB"
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Lancement du serveur de développement
    # Port 8000 par défaut, accessible sur toutes les interfaces (0.0.0.0)
    # reload=True pour le rechargement automatique en développement
    print("=" * 60)
    print("Démarrage de l'API - Phase 1 (Proof of Concept)")
    print("=" * 60)
    print("Documentation Swagger : http://localhost:8000/docs")
    print("Documentation ReDoc   : http://localhost:8000/redoc")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
