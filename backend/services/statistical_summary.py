"""
=============================================================================
SERVICE DE RÉSUMÉ STATISTIQUE - V1 (MVP)
=============================================================================

Ce service génère un résumé statistique intelligent à partir de fichiers
tabulaires (Excel, CSV). Il constitue le cœur fonctionnel de la V1.

Responsabilités :
    - Analyser la structure du fichier (lignes, colonnes, en-têtes)
    - Détecter le type de chaque colonne (texte, nombre, date)
    - Calculer les statistiques pertinentes par type
    - Identifier les alertes (valeurs manquantes, anomalies)
    - Générer un aperçu des premières lignes

Formats supportés :
    - Excel (.xlsx, .xls)
    - CSV (.csv)

=============================================================================
"""

import io
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# pandas pour l'analyse statistique
import pandas as pd

# openpyxl pour la lecture Excel
import openpyxl


class StatisticalSummaryService:
    """
    Service de génération de résumé statistique pour fichiers tabulaires.
    
    Usage:
        service = StatisticalSummaryService()
        result = service.analyze(filename, content)
    """
    
    # Extensions supportées
    SUPPORTED_EXTENSIONS = {'.xlsx', '.csv'}

    # Limites MVP (évite traitements trop lourds en synchrone)
    MAX_ROWS = 10_000
    MAX_COLUMNS = 200
    MAX_CELLS = 2_000_000
    
    # Seuils pour les alertes
    LOW_FILL_RATE_THRESHOLD = 50  # % en dessous duquel on alerte
    
    def __init__(self):
        """Initialisation du service"""
        pass
    
    def analyze(
        self,
        filename: str,
        content: bytes,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Point d'entrée principal - Analyse un fichier et génère le résumé.
        
        Args:
            filename: Nom du fichier (pour détection du format)
            content: Contenu binaire du fichier
            content_type: Type MIME optionnel
        
        Returns:
            Dictionnaire structuré avec le résumé statistique complet
        """
        
        extension = Path(filename).suffix.lower()
        
        # Vérification du format supporté
        if extension not in self.SUPPORTED_EXTENSIONS:
            return {
                "success": False,
                "error_code": "UNSUPPORTED_FORMAT",
                "message": f"Format non supporté: {extension}",
                "hint": "Formats acceptés : .csv, .xlsx",
                "details": {"supported_formats": sorted(self.SUPPORTED_EXTENSIONS)},
            }
        
        try:
            # Lecture du fichier en DataFrame pandas
            df = self._read_file(content, extension)

            # Validation des limites (MVP)
            limit_error = self._validate_limits(df)
            if limit_error is not None:
                return limit_error
            
            # Génération du résumé complet
            summary = self._generate_summary(df)
            
            return {
                "success": True,
                "file_type": "tabular",
                "extension": extension,
                "summary": summary,
                "preview": self._generate_preview(df)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error_code": "ANALYSIS_FAILED",
                "message": "Erreur d'analyse",
                "hint": "Vérifiez que le fichier est un Excel/CSV valide et non corrompu.",
                "details": {"reason": str(e), "extension": extension},
            }
    
    def _read_file(self, content: bytes, extension: str) -> pd.DataFrame:
        """
        Lit le fichier et retourne un DataFrame pandas.
        
        Args:
            content: Contenu binaire
            extension: Extension du fichier
        
        Returns:
            DataFrame pandas
        """
        
        buffer = io.BytesIO(content)
        
        if extension == '.csv':
            # Détection automatique de l'encodage et du séparateur
            text, encoding = self._decode_csv(content)
            delimiter = self._sniff_delimiter(text)
            df = pd.read_csv(io.StringIO(text), encoding=encoding, sep=delimiter)
        
        elif extension == '.xlsx':
            df = pd.read_excel(buffer, engine='openpyxl')
        
        elif extension == '.xls':
            df = pd.read_excel(buffer, engine='xlrd')
        
        else:
            raise ValueError(f"Format non géré: {extension}")
        
        return df

    def _decode_csv(self, content: bytes) -> tuple[str, str]:
        """Décodage CSV UTF-8 puis fallback latin-1."""
        try:
            return content.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            try:
                return content.decode("latin-1"), "latin-1"
            except Exception as e:
                raise ValueError("Encodage invalide") from e

    def _sniff_delimiter(self, text: str) -> str:
        """Détection du séparateur CSV via csv.Sniffer (fallback: ',')."""
        sample = text[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
            return dialect.delimiter
        except Exception:
            return ","

    def _validate_limits(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Valide limites MVP (lignes/colonnes/cellules). Retourne erreur dict ou None."""
        rows = len(df)
        cols = len(df.columns)
        cells = rows * cols

        if rows > self.MAX_ROWS or cols > self.MAX_COLUMNS or cells > self.MAX_CELLS:
            return {
                "success": False,
                "error_code": "LIMITS_EXCEEDED",
                "message": "Fichier trop volumineux pour un traitement synchrone",
                "hint": "Réduisez le nombre de lignes/colonnes ou divisez le fichier.",
                "details": {
                    "max_rows": self.MAX_ROWS,
                    "max_columns": self.MAX_COLUMNS,
                    "max_cells": self.MAX_CELLS,
                    "actual_rows": rows,
                    "actual_columns": cols,
                    "actual_cells": cells,
                },
            }
        return None
    
    def _generate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Génère le résumé complet du DataFrame.
        
        Args:
            df: DataFrame pandas à analyser
        
        Returns:
            Dictionnaire avec structure, colonnes et alertes
        """
        
        return {
            "structure": self._analyze_structure(df),
            "columns": self._analyze_columns(df),
            "alerts": self._detect_alerts(df)
        }
    
    def _analyze_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyse la structure globale du fichier.
        """
        
        structure = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "has_header": True,  # Hypothèse: pandas détecte les headers
            "memory_usage_kb": round(df.memory_usage(deep=True).sum() / 1024, 2)
        }
        
        # Détection de plage de dates si colonne date présente
        date_columns = df.select_dtypes(include=['datetime64']).columns
        if len(date_columns) > 0:
            first_date_col = date_columns[0]
            dates = df[first_date_col].dropna()
            if len(dates) > 0:
                structure["date_range"] = {
                    "detected": True,
                    "column": first_date_col,
                    "start": dates.min().strftime("%Y-%m-%d"),
                    "end": dates.max().strftime("%Y-%m-%d")
                }
        
        return structure
    
    def _analyze_columns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Analyse chaque colonne du DataFrame.
        
        Retourne pour chaque colonne:
            - Nom
            - Type détecté
            - Taux de remplissage
            - Statistiques selon le type
        """
        
        columns_analysis = []
        
        for col_name in df.columns:
            col_data = df[col_name]
            col_info = self._analyze_single_column(col_name, col_data, len(df))
            columns_analysis.append(col_info)
        
        return columns_analysis
    
    def _analyze_single_column(
        self,
        col_name: str,
        col_data: pd.Series,
        total_rows: int
    ) -> Dict[str, Any]:
        """
        Analyse une colonne individuelle.
        """
        
        # Comptage des valeurs manquantes
        missing_count = col_data.isna().sum()
        fill_count = total_rows - missing_count
        fill_rate = round((fill_count / total_rows) * 100, 1) if total_rows > 0 else 0
        
        # Détection du type
        col_type = self._detect_column_type(col_data)
        
        col_info = {
            "name": str(col_name),
            "type": col_type,
            "fill_rate": fill_rate,
            "missing_count": int(missing_count),
            "unique_count": int(col_data.nunique())
        }
        
        # Statistiques spécifiques selon le type
        if col_type == "number":
            col_info["stats"] = self._compute_numeric_stats(col_data)
        
        elif col_type == "text":
            col_info["top_values"] = self._get_top_values(col_data, n=5)
        
        elif col_type == "date":
            col_info["date_info"] = self._get_date_info(col_data)
        
        return col_info
    
    def _detect_column_type(self, col_data: pd.Series) -> str:
        """
        Détecte le type logique d'une colonne.
        
        Returns:
            "number", "text", "date", ou "mixed"
        """
        
        dtype = col_data.dtype
        
        if pd.api.types.is_numeric_dtype(dtype):
            return "number"
        
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return "date"
        
        elif pd.api.types.is_object_dtype(dtype):
            # Vérifier si c'est potentiellement des dates en texte
            sample = col_data.dropna().head(10)
            if len(sample) > 0:
                try:
                    pd.to_datetime(sample)
                    return "date"
                except:
                    pass
            return "text"
        
        return "mixed"
    
    def _compute_numeric_stats(self, col_data: pd.Series) -> Dict[str, Any]:
        """
        Calcule les statistiques pour une colonne numérique.
        """
        
        clean_data = col_data.dropna()
        
        if len(clean_data) == 0:
            return None
        
        stats = {
            "min": round(float(clean_data.min()), 2),
            "max": round(float(clean_data.max()), 2),
            "mean": round(float(clean_data.mean()), 2),
            "median": round(float(clean_data.median()), 2),
            "sum": round(float(clean_data.sum()), 2),
            "std": round(float(clean_data.std()), 2) if len(clean_data) > 1 else 0
        }
        
        return stats
    
    def _get_top_values(self, col_data: pd.Series, n: int = 5) -> List[str]:
        """
        Retourne les N valeurs les plus fréquentes d'une colonne texte.
        """
        
        value_counts = col_data.value_counts().head(n)
        return [str(v) for v in value_counts.index.tolist()]
    
    def _get_date_info(self, col_data: pd.Series) -> Dict[str, Any]:
        """
        Extrait les informations d'une colonne date.
        """
        
        try:
            dates = pd.to_datetime(col_data.dropna())
            if len(dates) == 0:
                return None
            
            return {
                "min": dates.min().strftime("%Y-%m-%d"),
                "max": dates.max().strftime("%Y-%m-%d"),
                "range_days": (dates.max() - dates.min()).days
            }
        except:
            return None
    
    def _detect_alerts(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Détecte les points d'attention dans les données.
        
        Types d'alertes:
            - missing_values: Valeurs manquantes significatives
            - low_fill_rate: Colonne peu remplie
            - single_value: Colonne avec une seule valeur (peu utile)
            - duplicates: Lignes dupliquées
        """
        
        alerts = []
        
        for col_name in df.columns:
            col_data = df[col_name]
            total = len(df)
            missing = col_data.isna().sum()
            fill_rate = ((total - missing) / total) * 100 if total > 0 else 0
            
            # Alerte: valeurs manquantes
            if missing > 0 and missing < total:
                severity = "warning" if missing > total * 0.1 else "info"
                alerts.append({
                    "type": "missing_values",
                    "severity": severity,
                    "column": str(col_name),
                    "count": int(missing),
                    "percentage": round(100 - fill_rate, 1),
                    "message": f"{missing} valeurs manquantes ({round(100 - fill_rate, 1)}%)"
                })
            
            # Alerte: colonne peu remplie
            if fill_rate < self.LOW_FILL_RATE_THRESHOLD and fill_rate > 0:
                alerts.append({
                    "type": "low_fill_rate",
                    "severity": "warning",
                    "column": str(col_name),
                    "fill_rate": round(fill_rate, 1),
                    "message": f"Colonne peu remplie ({round(fill_rate, 1)}%)"
                })
            
            # Alerte: colonne avec une seule valeur
            if col_data.nunique() == 1 and not col_data.isna().all():
                alerts.append({
                    "type": "single_value",
                    "severity": "info",
                    "column": str(col_name),
                    "value": str(col_data.dropna().iloc[0]) if len(col_data.dropna()) > 0 else None,
                    "message": "Colonne avec une seule valeur unique"
                })
        
        # Alerte: lignes dupliquées
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            alerts.append({
                "type": "duplicates",
                "severity": "warning",
                "count": int(duplicate_count),
                "percentage": round((duplicate_count / len(df)) * 100, 1),
                "message": f"{duplicate_count} lignes dupliquées détectées"
            })
        
        # Tri par sévérité
        severity_order = {"warning": 0, "info": 1}
        alerts.sort(key=lambda x: severity_order.get(x["severity"], 2))
        
        return alerts
    
    def _generate_preview(self, df: pd.DataFrame, n_rows: int = 5) -> Dict[str, Any]:
        """
        Génère un aperçu des premières lignes du fichier.
        """
        
        # Conversion en liste pour JSON
        headers = [str(col) for col in df.columns.tolist()]
        
        # Premières lignes (converties en strings pour éviter problèmes de sérialisation)
        rows = []
        for _, row in df.head(n_rows).iterrows():
            row_data = []
            for val in row:
                if pd.isna(val):
                    row_data.append(None)
                elif isinstance(val, (datetime, pd.Timestamp)):
                    row_data.append(val.strftime("%Y-%m-%d"))
                else:
                    row_data.append(str(val) if not isinstance(val, (int, float)) else val)
            rows.append(row_data)
        
        return {
            "headers": headers,
            "rows": rows,
            "total_rows": len(df),
            "showing": min(n_rows, len(df))
        }


# =============================================================================
# FONCTION UTILITAIRE POUR FORMATS SUPPORTÉS
# =============================================================================

def get_supported_formats() -> Dict[str, str]:
    """
    Retourne la liste des formats supportés avec description.
    """
    return {
        ".xlsx": "Microsoft Excel (format moderne XLSX)",
        ".csv": "Fichier CSV (valeurs séparées par virgules)"
    }
