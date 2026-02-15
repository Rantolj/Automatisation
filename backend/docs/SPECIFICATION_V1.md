# Spécification Fonctionnelle V1 — Résumé Statistique

> **Document de référence** pour le développement de l'application mobile et du backend Python.  
> Dernière mise à jour : 15 février 2026

---

## 1. Objectif V1 (MVP)

L'application génère un **résumé statistique intelligent** à partir d'un fichier tabulaire (Excel, CSV) uploadé depuis l'application mobile.

### Proposition de valeur
> "Voir en 3 secondes ce qu'il faudrait 5 minutes à analyser manuellement"

---

## 2. Flux Utilisateur

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Sélection  │ ──▶ │   Upload    │ ──▶ │  Analyse    │ ──▶ │  Résultat   │
│  fichier    │     │   API       │     │  Backend    │     │  Affiché    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. L'utilisateur sélectionne un fichier Excel ou CSV sur son mobile
2. Le fichier est envoyé au backend via `POST /process`
3. Le backend analyse et génère le résumé statistique
4. L'application affiche le résultat de manière lisible

---

## 3. Formats Supportés

| Extension | Description | Support V1 |
|-----------|-------------|------------|
| `.xlsx` | Microsoft Excel (moderne) | ✅ Complet |
| `.xls` | Microsoft Excel (ancien) | ✅ Complet |
| `.csv` | Valeurs séparées | ✅ Complet |

---

## 4. Résultat Produit

### 4.1 Vue Utilisateur (ce que voit l'utilisateur)

```
┌─────────────────────────────────────────────────────────────┐
│  📁 fichier_ventes.xlsx                                     │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  📋 STRUCTURE                                               │
│     • 1 254 lignes de données                               │
│     • 8 colonnes détectées                                  │
│     • Période : 01/01/2026 → 31/01/2026                     │
│                                                             │
│  📊 RÉSUMÉ PAR COLONNE                                      │
│  ┌─────────────┬───────────┬───────────┬──────────────────┐ │
│  │ Colonne     │ Type      │ Rempli    │ Résumé           │ │
│  ├─────────────┼───────────┼───────────┼──────────────────┤ │
│  │ Date        │ Date      │ 100%      │ 31 jours uniques │ │
│  │ Produit     │ Texte     │ 100%      │ 47 valeurs       │ │
│  │ Quantité    │ Nombre    │ 98%       │ Moy: 12.5        │ │
│  │ Prix        │ Nombre    │ 100%      │ Total: 45 230 €  │ │
│  └─────────────┴───────────┴───────────┴──────────────────┘ │
│                                                             │
│  ⚠️ POINTS D'ATTENTION                                      │
│     • 25 valeurs manquantes dans "Quantité"                 │
│     • Colonne "Notes" peu remplie (23%)                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Format Technique (JSON retourné par l'API)

```json
{
  "success": true,
  "filename": "fichier_ventes.xlsx",
  "file_size": "45.23 KB",
  "processed_at": "2026-02-15T14:32:07",
  
  "processing_result": {
    "success": true,
    "file_type": "tabular",
    "extension": ".xlsx",
    
    "summary": {
      "structure": {
        "row_count": 1254,
        "column_count": 8,
        "has_header": true,
        "memory_usage_kb": 125.5,
        "date_range": {
          "detected": true,
          "column": "Date",
          "start": "2026-01-01",
          "end": "2026-01-31"
        }
      },
      
      "columns": [
        {
          "name": "Produit",
          "type": "text",
          "fill_rate": 100,
          "missing_count": 0,
          "unique_count": 47,
          "top_values": ["Produit A", "Produit B", "Produit C"]
        },
        {
          "name": "Quantité",
          "type": "number",
          "fill_rate": 98,
          "missing_count": 25,
          "unique_count": 45,
          "stats": {
            "min": 1,
            "max": 150,
            "mean": 12.5,
            "median": 10,
            "sum": 15675,
            "std": 8.3
          }
        }
      ],
      
      "alerts": [
        {
          "type": "missing_values",
          "severity": "warning",
          "column": "Quantité",
          "count": 25,
          "percentage": 2.0,
          "message": "25 valeurs manquantes (2.0%)"
        },
        {
          "type": "low_fill_rate",
          "severity": "warning",
          "column": "Notes",
          "fill_rate": 23,
          "message": "Colonne peu remplie (23%)"
        }
      ]
    },
    
    "preview": {
      "headers": ["Date", "Produit", "Quantité", "Prix"],
      "rows": [
        ["2026-01-01", "Produit A", 5, 29.99],
        ["2026-01-01", "Produit B", 12, 15.50]
      ],
      "total_rows": 1254,
      "showing": 5
    }
  }
}
```

---

## 5. Données Incluses / Exclues

### ✅ Incluses (V1)

| Catégorie | Données | Utilité |
|-----------|---------|---------|
| Structure | Lignes, colonnes, en-tête | Vue d'ensemble du fichier |
| Typage | Type par colonne (texte/nombre/date) | Comprendre les données |
| Complétude | Taux de remplissage, valeurs manquantes | Qualité des données |
| Statistiques | Min/Max/Moyenne/Total (nombres) | KPIs instantanés |
| Cardinalité | Valeurs uniques, top valeurs (texte) | Diversité des données |
| Aperçu | 5 premières lignes | Contexte visuel |
| Alertes | Manquants, colonnes vides, doublons | Aide à la décision |

### ❌ Exclues (reportées V2+)

| Données | Raison |
|---------|--------|
| Graphiques | Complexité mobile |
| Corrélations | Nécessite config utilisateur |
| Prédictions | Hors scope MVP |
| Export PDF/Excel | Valeur secondaire |
| Comparaison historique | Nécessite stockage |

---

## 6. Types d'Alertes

| Type | Sévérité | Condition |
|------|----------|-----------|
| `missing_values` | warning/info | Valeurs manquantes détectées |
| `low_fill_rate` | warning | Colonne remplie < 50% |
| `single_value` | info | Colonne avec 1 seule valeur |
| `duplicates` | warning | Lignes dupliquées |

---

## 7. Critères d'Acceptation

| Critère | Validation |
|---------|------------|
| Fichiers acceptés | `.xlsx`, `.xls`, `.csv` traités sans erreur |
| Réponse complète | Structure + colonnes + alertes présents |
| Performance | < 5 secondes pour < 10 000 lignes |
| Lisibilité | JSON exploitable directement par l'app mobile |
| Robustesse | Erreurs capturées et messages explicites |

---

## 8. Endpoint API

### `POST /process`

**Request:**
```
Content-Type: multipart/form-data
Body: file (fichier Excel ou CSV)
```

**Response (succès):**
```json
{
  "success": true,
  "filename": "...",
  "file_size": "...",
  "processing_result": { ... },
  "processed_at": "..."
}
```

**Response (erreur):**
```json
{
  "success": false,
  "filename": "...",
  "processing_result": {
    "success": false,
    "error": "Description de l'erreur"
  }
}
```

---

## 9. Évolutions Futures (V2+)

| Version | Fonctionnalité |
|---------|----------------|
| V2 | Filtrage et extraction ciblée |
| V2 | Export du résumé en PDF |
| V2 | Détection d'anomalies avancée |
| V3 | Graphiques intégrés |
| V3 | Comparaison entre fichiers |
| V3 | Alertes personnalisées |

---

## 10. Architecture Services

```
backend/
├── main.py                           # API FastAPI
├── services/
│   ├── file_processor.py             # Traitement générique (txt, json...)
│   └── statistical_summary.py        # ⭐ Résumé statistique V1 (Excel/CSV)
```

---

## 11. Justification du Choix V1

### Simplicité
- Aucune configuration requise
- Fonctionne avec tout fichier tabulaire
- Implémentation avec pandas (standard Python)

### Valeur Utilisateur
- Gain de temps immédiat
- Détection automatique des problèmes
- Résumé en langage naturel

### Évolutivité
- Base pour toutes les fonctionnalités futures
- Structure JSON extensible
- Services découplés

---

**Ce document sert de référence unique pour le développement.**
