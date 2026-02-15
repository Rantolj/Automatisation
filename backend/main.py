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

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
from datetime import datetime
from pathlib import Path

# Import des services de traitement
from services.file_processor import FileProcessor
from services.statistical_summary import StatisticalSummaryService

# =============================================================================
# INITIALISATION DE L'APPLICATION
# =============================================================================

app = FastAPI(
    title="API Automatisation - Phase 1",
    description="Backend Python pour traitement de fichiers depuis application mobile",
    version="1.0.0"
)

# Configuration CORS pour permettre les appels depuis l'app mobile
# En Phase 1, on autorise tout. Phase 2 : restreindre aux origines légitimes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dossiers de travail
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

# Création des dossiers s'ils n'existent pas
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Instances des services de traitement
processor = FileProcessor()
statistical_service = StatisticalSummaryService()

# Extensions pour le résumé statistique (V1)
STATISTICAL_EXTENSIONS = {'.xlsx', '.xls', '.csv'}


# =============================================================================
# ENDPOINTS
# =============================================================================

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
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit avoir un nom"
        )
    
    # Génération d'un nom unique pour éviter les collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    # Sauvegarde du fichier
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la sauvegarde : {str(e)}"
        )
    
    # Calcul de la taille
    file_size = len(contents)
    
    return {
        "success": True,
        "message": "Fichier uploadé avec succès",
        "file_info": {
            "original_name": file.filename,
            "saved_name": safe_filename,
            "size_bytes": file_size,
            "size_readable": _format_size(file_size),
            "content_type": file.content_type,
            "path": file_path
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
        raise HTTPException(status_code=400, detail="Fichier requis")
    
    # Lecture du contenu
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de lecture : {str(e)}"
        )
    
    # Détection de l'extension pour router vers le bon service
    extension = Path(file.filename).suffix.lower()
    
    try:
        # Fichiers tabulaires (Excel, CSV) → Résumé Statistique V1
        if extension in STATISTICAL_EXTENSIONS:
            result = statistical_service.analyze(
                filename=file.filename,
                content=contents,
                content_type=file.content_type
            )
        # Autres fichiers → Traitement basique
        else:
            result = processor.process(
                filename=file.filename,
                content=contents,
                content_type=file.content_type
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de traitement : {str(e)}"
        )
    
    return {
        "success": result.get("success", True),
        "filename": file.filename,
        "file_size": _format_size(len(contents)),
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
