# API Automatisation - Backend Python

## Vue d'ensemble

Backend Python pour application mobile de traitement automatisé de fichiers.

```
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│   Mobile    │ ─────▶ │    API      │ ─────▶ │  Traitement │
│   App       │        │   FastAPI   │        │   Fichiers  │
│             │ ◀───── │             │ ◀───── │             │
└─────────────┘        └─────────────┘        └─────────────┘
     HTTP                 REST                   Python
```

## Structure du Projet

```
backend/
├── main.py                    # Point d'entrée API FastAPI
├── requirements.txt           # Dépendances Python
├── services/
│   ├── __init__.py
│   └── file_processor.py      # Logique de traitement des fichiers
├── uploads/                   # Fichiers uploadés (auto-créé)
├── outputs/                   # Fichiers générés (auto-créé)
└── tests/
    └── test_api.py            # Scripts de test
```

## Installation

### Prérequis
- Python 3.9+
- pip

### Étapes

```bash
# 1. Créer un environnement virtuel
python -m venv venv

# 2. Activer l'environnement
# Windows PowerShell :
.\venv\Scripts\Activate.ps1
# Windows CMD :
.\venv\Scripts\activate.bat
# Linux/Mac :
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt
```

## Démarrage

```bash
# Lancer le serveur de développement
python main.py

# Ou avec uvicorn directement
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Le serveur démarre sur `http://localhost:8000`

## Documentation API

Une fois le serveur lancé :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Info API et liste des endpoints |
| GET | `/health` | Health check |
| POST | `/upload` | Upload d'un fichier |
| POST | `/process` | Upload + traitement en une requête |

## Utilisation

### Test avec cURL

```bash
# Health check
curl http://localhost:8000/health

# Upload d'un fichier
curl -X POST "http://localhost:8000/upload" \
  -F "file=@monFichier.txt"

# Traitement d'un fichier
curl -X POST "http://localhost:8000/process" \
  -F "file=@monFichier.csv"
```

### Test avec PowerShell

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Upload
$file = Get-Item "monFichier.txt"
Invoke-RestMethod -Uri "http://localhost:8000/upload" `
  -Method Post `
  -InFile $file.FullName `
  -ContentType "multipart/form-data"
```

### Test avec Python

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Traitement d'un fichier
with open("monFichier.csv", "rb") as f:
    response = requests.post(
        "http://localhost:8000/process",
        files={"file": f}
    )
print(response.json())
```

## Formats Supportés (Phase 1)

| Extension | Traitement |
|-----------|------------|
| `.txt`, `.md`, `.log` | Comptage lignes/mots/caractères, aperçu |
| `.csv` | Structure, colonnes, aperçu des données |
| `.json` | Validation, structure, clés |
| Binaires | Détection de type, métadonnées basiques |

## Phases du Projet

### Phase 1 (Actuelle) - Proof of Concept
- ✅ API fonctionnelle minimale
- ✅ Upload de fichiers
- ✅ Traitement basique (texte, CSV, JSON)
- ✅ Documentation automatique
- ✅ Code pédagogique et commenté

### Phase 2 (À venir) - Production Ready
- 🔲 Structure modulaire avancée
- 🔲 Gestion d'erreurs robuste
- 🔲 Validation stricte des fichiers
- 🔲 Sécurité (types de fichiers, tailles)
- 🔲 Tests unitaires et d'intégration
- 🔲 Support PDF, Excel, Images
- 🔲 Authentification JWT
- 🔲 Rate limiting
- 🔲 Logs structurés

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         API LAYER                            │
│  main.py - FastAPI                                           │
│  • Routing HTTP                                              │
│  • Validation des requêtes (Pydantic)                        │
│  • Gestion des erreurs HTTP                                  │
│  • Documentation OpenAPI                                     │
├──────────────────────────────────────────────────────────────┤
│                       SERVICE LAYER                          │
│  services/file_processor.py                                  │
│  • Logique métier                                            │
│  • Détection de type de fichier                              │
│  • Traitement selon le format                                │
│  • Indépendant du framework web                              │
├──────────────────────────────────────────────────────────────┤
│                        DATA LAYER                            │
│  uploads/ - Fichiers reçus                                   │
│  outputs/ - Fichiers générés                                 │
└──────────────────────────────────────────────────────────────┘
```

## Choix Techniques

| Choix | Justification |
|-------|---------------|
| **FastAPI** | Performance, documentation auto, validation native, moderne |
| **Uvicorn** | Serveur ASGI recommandé, support async, hot reload |
| **Pydantic** | Validation robuste, intégré à FastAPI |
| **Bibliothèques std** | `json`, `csv`, `io` - Pas de dépendance inutile |

## Contribution

1. Les modifications de logique métier vont dans `services/`
2. Les endpoints vont dans `main.py`
3. Chaque fonction doit être documentée
4. Les erreurs doivent être gérées proprement

## Licence

Projet interne - À définir
