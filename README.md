# Automatisation

Backend Python d'une application mobile destinée à analyser automatiquement des fichiers et à retourner un résumé exploitable par l'utilisateur.

Le projet expose une API REST basée sur **FastAPI**. Une application mobile peut envoyer un fichier, demander son traitement, puis afficher les résultats sous forme de données JSON.

> **État actuel :** proof of concept / MVP fonctionnel. Le projet constitue une bonne base de démonstration, mais il nécessite encore plusieurs améliorations avant une mise en production.

## Fonctionnalités

- Upload de fichiers via une API REST.
- Vérification de l'extension et de la taille des fichiers.
- Nettoyage des noms de fichiers reçus.
- Analyse de fichiers texte (`.txt`, `.md`, `.log`).
- Analyse de fichiers JSON : validation et détection de structure.
- Analyse de fichiers CSV : lignes, colonnes, en-têtes et aperçu.
- Résumé statistique de fichiers CSV et Excel (`.csv`, `.xlsx`, `.xls`).
- Détection de types de colonnes : texte, nombre et date.
- Calcul de statistiques numériques : minimum, maximum, moyenne, médiane, somme et écart-type.
- Détection de problèmes courants : valeurs manquantes, colonnes peu remplies, valeurs uniques et doublons.
- Réponses d'erreur standardisées avec `error_code`, message et identifiant de requête.
- Documentation interactive générée automatiquement par FastAPI.
- Rate limiting basique : 30 requêtes par minute et par adresse IP dans la configuration actuelle.

## Architecture

```text
Automatisation/
├── backend/
│   ├── main.py                    # Application FastAPI et endpoints HTTP
│   ├── config.py                  # Configuration centralisée
│   ├── requirements.txt            # Dépendances de production
│   ├── requirements-dev.txt        # Dépendances de développement et tests
│   ├── services/
│   │   ├── file_processor.py       # Traitement texte, CSV, JSON et métadonnées
│   │   └── statistical_summary.py  # Analyse statistique CSV et Excel
│   ├── tests/
│   │   ├── test_api.py             # Tests des endpoints FastAPI
│   │   └── test_statistical_summary.py
│   └── docs/
│       ├── SPECIFICATION_V1.md     # Spécification fonctionnelle du MVP
│       ├── PHASE_2_ROADMAP.md       # Feuille de route vers la production
│       └── mobile_integration_examples.py
├── uploads/                        # Exemples de fichiers reçus
├── commande.txt                    # Commandes de démarrage initiales
└── readmePrompt.txt                # Vision et contexte fonctionnel du projet
```

### Fonctionnement global

```text
Application mobile
       │
       │ multipart/form-data
       ▼
API FastAPI (backend/main.py)
       │
       ├── Validation du fichier
       ├── Limite de taille et extension
       ├── Traitement générique
       │      └── services/file_processor.py
       └── Analyse statistique CSV/Excel
              └── services/statistical_summary.py
                       │
                       ▼
                 Résultat JSON
```

## Technologies utilisées

- **Python 3.9+**
- **FastAPI** : création de l'API REST et documentation OpenAPI.
- **Uvicorn** : serveur ASGI utilisé pour lancer l'application.
- **Pydantic / pydantic-settings** : validation et configuration.
- **pandas** : lecture et analyse de données tabulaires.
- **openpyxl** : lecture des fichiers Excel `.xlsx`.
- **xlrd** : lecture des fichiers Excel `.xls`.
- **pytest** : exécution des tests.

## Installation

### Prérequis

- Python 3.9 ou une version plus récente.
- `pip`.
- Windows, Linux ou macOS.

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Linux ou macOS

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Configuration optionnelle

Copiez le fichier d'exemple `.env.example` vers `.env` dans le dossier `backend` :

```bash
cp .env.example .env
```

Sous PowerShell :

```powershell
Copy-Item .env.example .env
```

Les paramètres principaux sont :

- `MAX_FILE_SIZE_MB` : taille maximale d'un fichier.
- `UPLOAD_DIR` : dossier de stockage des fichiers reçus.
- `OUTPUT_DIR` : dossier prévu pour les fichiers générés.
- `ALLOWED_EXTENSIONS` : extensions acceptées.
- `PROCESS_TIMEOUT_SECONDS` : durée maximale de traitement.
- `RATE_LIMIT_REQUESTS_PER_WINDOW` : nombre maximal de requêtes par fenêtre.
- `CORS_ORIGINS` : origines autorisées. La valeur `*` est pratique en développement, mais doit être restreinte en production.

## Démarrage de l'API

Depuis le dossier `backend` et avec l'environnement virtuel activé :

```bash
python main.py
```

Ou directement avec Uvicorn :

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

L'API est alors disponible à l'adresse :

```text
http://localhost:8000
```

Documentation interactive :

- Swagger UI : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`
- OpenAPI JSON : `http://localhost:8000/openapi.json`

## Endpoints principaux

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Vérifie que l'API est démarrée et liste les endpoints principaux. |
| `GET` | `/health` | Retourne l'état de santé du service. |
| `POST` | `/upload` | Reçoit et sauvegarde un fichier sans l'analyser. |
| `POST` | `/process` | Reçoit un fichier et retourne son analyse au format JSON. |

## Exemples d'utilisation

### Vérifier l'état du service

```bash
curl http://localhost:8000/health
```

### Analyser un fichier CSV

```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@exemple.csv"
```

### Analyser un fichier Excel

```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@exemple.xlsx"
```

### Envoyer un fichier sans traitement

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@exemple.txt"
```

Une réponse réussie de `/process` contient notamment :

```json
{
  "success": true,
  "filename": "exemple.csv",
  "file_size": "1.25 KB",
  "processing_result": {
    "success": true,
    "summary": {
      "structure": {},
      "columns": [],
      "alerts": []
    },
    "preview": {}
  },
  "processed_at": "..."
}
```

## Formats pris en charge

| Format | Traitement |
|---|---|
| `.csv` | Résumé statistique, structure, colonnes, types, statistiques et alertes. |
| `.xlsx` | Lecture et analyse avec pandas/openpyxl. |
| `.xls` | Lecture et analyse avec pandas/xlrd. |
| `.txt`, `.md`, `.log` | Comptage des lignes, mots, caractères et aperçu. |
| `.json` | Validation du JSON et analyse de sa structure. |

La taille maximale par défaut est de **10 MB**. Les fichiers CSV et Excel sont également limités à **10 000 lignes**, **200 colonnes** et **2 000 000 cellules** pour éviter les traitements trop lourds dans le MVP.

## Tests

Depuis le dossier `backend` :

```bash
pytest -v
```

Pour lancer un fichier de test précis :

```bash
pytest tests/test_api.py -v
pytest tests/test_statistical_summary.py -v
```

Les tests couvrent notamment :

- les endpoints `/` et `/health` ;
- l'upload de fichiers ;
- le rejet des extensions non autorisées ;
- le traitement de fichiers texte, CSV et JSON ;
- l'analyse Excel ;
- les valeurs manquantes et les doublons ;
- la détection de dates et les statistiques numériques.

## Évaluation du projet

### Points positifs

- Le périmètre fonctionnel du MVP est clair.
- La séparation entre l'API et les services métier est déjà commencée.
- Les modules `file_processor.py` et `statistical_summary.py` sont réutilisables et relativement faciles à tester.
- La validation des extensions, de la taille, des noms de fichiers et du temps de traitement est prévue.
- Les réponses d'erreur sont structurées et utilisent des codes HTTP cohérents.
- La présence de tests, d'une spécification V1 et d'une roadmap est un très bon signe pour la suite.

### Points à améliorer avant la production

- Vérifier et corriger les imports et la configuration de démarrage dans `backend/main.py`.
- Éviter de versionner un environnement virtuel `venv/` dans Git ; utiliser plutôt un environnement local ignoré par `.gitignore`.
- Éviter de versionner des fichiers utilisateurs dans `uploads/`, surtout s'ils contiennent des données personnelles ou professionnelles.
- Ajouter une authentification si l'API doit être accessible par plusieurs utilisateurs.
- Remplacer le rate limiting en mémoire par une solution partagée en production.
- Restreindre `CORS_ORIGINS` au domaine réel de l'application mobile ou du frontend.
- Ajouter une validation basée sur le contenu réel du fichier, et pas uniquement sur son extension.
- Ajouter une intégration continue GitHub Actions et un rapport de couverture de tests.
- Préparer un traitement asynchrone pour les fichiers volumineux.
- Ajouter un `Dockerfile`, une procédure de déploiement et une licence explicite.

## Feuille de route

La roadmap détaillée se trouve dans [`backend/docs/PHASE_2_ROADMAP.md`](backend/docs/PHASE_2_ROADMAP.md).

Les prochaines étapes prioritaires sont :

1. stabiliser la configuration et le démarrage de l'API ;
2. renforcer la sécurité des fichiers et des erreurs ;
3. structurer l'application en modules et routers versionnés ;
4. améliorer les tests unitaires et d'intégration ;
5. préparer le déploiement avec Docker et CI/CD ;
6. ajouter l'authentification et le traitement asynchrone.

## Documentation complémentaire

- [Documentation du backend](backend/README.md)
- [Spécification fonctionnelle V1](backend/docs/SPECIFICATION_V1.md)
- [Roadmap Phase 2](backend/docs/PHASE_2_ROADMAP.md)
- [Commandes de démarrage](commande.txt)

## Licence

Aucune licence open source n'est actuellement définie. Le projet est indiqué comme projet interne ; ajoutez un fichier `LICENSE` si le dépôt doit être partagé ou réutilisé publiquement.
