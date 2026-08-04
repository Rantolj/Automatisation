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
# CONTRAINTES MVP (V1)
# =============================================================================

# Formats acceptés (whitelist)
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json', '.txt'}

# Taille max (10 MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Timeout de traitement synchrone (en secondes)
PROCESS_TIMEOUT_SECONDS = 10

# Rate limit basique (30 req/min/IP)
RATE_LIMIT_REQUESTS_PER_WINDOW = 30
RATE_LIMIT_WINDOW_SECONDS = 60

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
async def root():
    """
    Point d'entrée racine - Vérification que l'API est en ligne
    
    Usage : Health check depuis l'app mobile ou monitoring
    """
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
