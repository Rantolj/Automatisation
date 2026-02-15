# =============================================================================
# FEUILLE DE ROUTE - PHASE 2
# =============================================================================
# 
# Ce document décrit les améliorations à apporter pour passer
# de la Phase 1 (Proof of Concept) à la Phase 2 (Production Ready)
#
# =============================================================================

## PRIORITÉ HAUTE

### 1. Structure du Projet
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Point d'entrée, configuration FastAPI
│   ├── config.py            # Configuration centralisée (Pydantic Settings)
│   ├── dependencies.py      # Injection de dépendances
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py    # Router principal v1
│   │   │   └── endpoints/
│   │   │       ├── files.py
│   │   │       ├── health.py
│   │   │       └── auth.py
│   │   │
│   │   └── v2/              # Préparation versioning API
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py      # JWT, hashing, validation
│   │   ├── exceptions.py    # Exceptions métier personnalisées
│   │   └── logging.py       # Configuration des logs
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py       # Pydantic models (request/response)
│   │   └── domain.py        # Modèles métier
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_processor.py
│   │   ├── pdf_service.py
│   │   ├── excel_service.py
│   │   └── image_service.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Fixtures pytest
│   ├── test_api/
│   │   └── test_files.py
│   └── test_services/
│       └── test_processor.py
│
├── alembic/                  # Migrations DB (si besoin)
├── docs/
├── scripts/
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

### 2. Sécurité

- [ ] Validation stricte des types de fichiers (magic bytes, pas juste extension)
- [ ] Limite de taille des fichiers (configurable)
- [ ] Sanitization des noms de fichiers
- [ ] Rate limiting par IP/user
- [ ] Authentification JWT
- [ ] CORS restrictif (liste blanche d'origines)
- [ ] Headers de sécurité (HSTS, X-Content-Type-Options, etc.)
- [ ] Pas d'exposition de paths internes dans les erreurs

### 3. Gestion des Erreurs

```python
# Exemple de hiérarchie d'exceptions
class AppException(Exception):
    """Exception de base"""
    pass

class FileProcessingError(AppException):
    """Erreur lors du traitement de fichier"""
    pass

class UnsupportedFileTypeError(FileProcessingError):
    """Type de fichier non supporté"""
    pass

class FileTooLargeError(FileProcessingError):
    """Fichier trop volumineux"""
    pass

class InvalidFileContentError(FileProcessingError):
    """Contenu de fichier invalide"""
    pass
```

### 4. Configuration

```python
# config.py avec Pydantic Settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API
    app_name: str = "File Processing API"
    debug: bool = False
    api_prefix: str = "/api/v1"
    
    # Fichiers
    max_file_size_mb: int = 10
    allowed_extensions: list = [".txt", ".csv", ".json", ".pdf", ".xlsx"]
    upload_dir: str = "uploads"
    
    # Sécurité
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: list = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
```

## PRIORITÉ MOYENNE

### 5. Nouveaux Formats de Fichiers

- [ ] PDF (extraction de texte avec PyPDF2 ou pdfplumber)
- [ ] Excel (.xlsx avec openpyxl)
- [ ] Images (métadonnées avec Pillow)
- [ ] Word (.docx avec python-docx)

### 6. Logging Structuré

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, 'request_id'):
            log_obj['request_id'] = record.request_id
        return json.dumps(log_obj)
```

### 7. Tests

- [ ] Tests unitaires avec pytest
- [ ] Tests d'intégration avec TestClient FastAPI
- [ ] Tests de charge avec locust
- [ ] Couverture de code > 80%

```python
# Exemple de test avec pytest
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_process_text_file():
    content = b"Hello World"
    response = client.post(
        "/process",
        files={"file": ("test.txt", content, "text/plain")}
    )
    assert response.status_code == 200
    assert response.json()["success"] == True
```

## PRIORITÉ BASSE

### 8. Fonctionnalités Avancées

- [ ] Traitement asynchrone avec tâches en arrière-plan (Celery, RQ)
- [ ] File d'attente pour les gros fichiers
- [ ] Cache des résultats (Redis)
- [ ] Notifications push vers le mobile
- [ ] Stockage cloud (S3, Azure Blob)

### 9. Monitoring et Observabilité

- [ ] Métriques Prometheus
- [ ] Tracing distribué (Jaeger, Zipkin)
- [ ] Health checks avancés
- [ ] Dashboard de monitoring

### 10. Déploiement

- [ ] Dockerfile optimisé
- [ ] docker-compose.yml
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Configuration Kubernetes (optionnel)

```dockerfile
# Dockerfile optimisé
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

COPY ./app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## CHECKLIST AVANT PRODUCTION

- [ ] Pas de debug=True
- [ ] Secrets dans variables d'environnement
- [ ] HTTPS configuré
- [ ] Logs en production
- [ ] Backup des données
- [ ] Monitoring actif
- [ ] Documentation API à jour
- [ ] Tests passent à 100%
- [ ] Review de sécurité effectuée
- [ ] Plan de rollback défini
