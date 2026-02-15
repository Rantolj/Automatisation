"""
=============================================================================
SERVICE DE TRAITEMENT DE FICHIERS - Phase 1
=============================================================================

Ce module encapsule toute la logique de traitement des fichiers.
Séparation claire entre :
  - L'API (réception/réponse HTTP)
  - Le traitement (logique métier)

Principe : Le service ne connaît pas FastAPI, il reçoit des données brutes
et retourne des résultats structurés.

=============================================================================
"""

import json
import csv
import io
from typing import Dict, Any, Optional
from pathlib import Path


class FileProcessor:
    """
    Classe principale de traitement de fichiers.
    
    Responsabilités :
        - Détecter le type de fichier
        - Appliquer le traitement approprié
        - Retourner un résultat structuré
    
    Design Pattern : Strategy (sélection du traitement selon le type)
    """
    
    # Extensions supportées et leurs handlers
    SUPPORTED_EXTENSIONS = {
        '.txt': 'text',
        '.csv': 'csv',
        '.json': 'json',
        '.md': 'text',
        '.log': 'text',
    }
    
    def __init__(self):
        """Initialisation du processeur"""
        pass
    
    def process(
        self,
        filename: str,
        content: bytes,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Point d'entrée principal du traitement.
        
        Args:
            filename: Nom du fichier (pour détection d'extension)
            content: Contenu binaire du fichier
            content_type: Type MIME (optionnel, pour validation)
        
        Returns:
            Dictionnaire avec le résultat du traitement
        
        Le flux de traitement :
            1. Détection du type de fichier
            2. Sélection du handler approprié
            3. Exécution du traitement
            4. Formatage du résultat
        """
        
        # Extraction de l'extension
        extension = Path(filename).suffix.lower()
        
        # Sélection du type de traitement
        file_type = self.SUPPORTED_EXTENSIONS.get(extension, 'binary')
        
        # Dispatch vers le handler approprié
        handlers = {
            'text': self._process_text,
            'csv': self._process_csv,
            'json': self._process_json,
            'binary': self._process_binary,
        }
        
        handler = handlers.get(file_type, self._process_binary)
        
        # Exécution du traitement
        result = handler(content, filename)
        
        # Ajout des métadonnées communes
        result['file_type'] = file_type
        result['extension'] = extension
        result['size_bytes'] = len(content)
        
        return result
    
    def _process_text(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        Traitement des fichiers texte (.txt, .md, .log)
        
        Analyse :
            - Nombre de lignes
            - Nombre de mots
            - Nombre de caractères
            - Aperçu du contenu
        """
        
        try:
            # Décodage du contenu (UTF-8 par défaut)
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback sur latin-1 si UTF-8 échoue
            text = content.decode('latin-1')
        
        # Analyse du texte
        lines = text.split('\n')
        words = text.split()
        
        # Aperçu (premiers 500 caractères)
        preview = text[:500] + ('...' if len(text) > 500 else '')
        
        return {
            'analysis': {
                'line_count': len(lines),
                'word_count': len(words),
                'char_count': len(text),
                'char_count_no_spaces': len(text.replace(' ', '').replace('\n', '')),
                'empty_lines': sum(1 for line in lines if not line.strip()),
            },
            'preview': preview,
            'encoding_detected': 'utf-8',
        }
    
    def _process_csv(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        Traitement des fichiers CSV
        
        Analyse :
            - Nombre de lignes
            - Nombre de colonnes
            - Noms des colonnes (si header présent)
            - Aperçu des premières lignes
        """
        
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')
        
        # Parsing CSV
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        
        if not rows:
            return {
                'analysis': {
                    'row_count': 0,
                    'column_count': 0,
                },
                'error': 'Fichier CSV vide'
            }
        
        # Analyse de la structure
        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []
        
        # Aperçu des premières lignes (max 5)
        preview_rows = rows[:6]  # Header + 5 lignes de données
        
        return {
            'analysis': {
                'row_count': len(rows),
                'data_row_count': len(data_rows),
                'column_count': len(headers),
                'headers': headers,
            },
            'preview': {
                'first_rows': preview_rows,
                'sample_size': min(5, len(data_rows)),
            },
            'structure': {
                'has_header': True,  # Hypothèse Phase 1
                'delimiter': ',',
            }
        }
    
    def _process_json(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        Traitement des fichiers JSON
        
        Analyse :
            - Validation du JSON
            - Structure (objet, tableau, type primitif)
            - Clés de premier niveau
            - Profondeur estimée
        """
        
        try:
            text = content.decode('utf-8')
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'error': f'JSON invalide : {str(e)}',
                'error_position': {
                    'line': e.lineno,
                    'column': e.colno,
                }
            }
        except UnicodeDecodeError:
            return {
                'valid': False,
                'error': 'Encodage invalide'
            }
        
        # Analyse de la structure
        structure_type = type(data).__name__
        
        result = {
            'valid': True,
            'structure': {
                'type': structure_type,
            }
        }
        
        # Analyse spécifique selon le type
        if isinstance(data, dict):
            result['structure']['keys'] = list(data.keys())
            result['structure']['key_count'] = len(data.keys())
            result['preview'] = {k: str(v)[:100] for k, v in list(data.items())[:5]}
            
        elif isinstance(data, list):
            result['structure']['length'] = len(data)
            result['structure']['item_types'] = list(set(type(item).__name__ for item in data[:10]))
            result['preview'] = data[:5] if len(data) <= 5 else data[:5]
            
        else:
            result['structure']['value'] = str(data)[:200]
        
        return result
    
    def _process_binary(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        Traitement des fichiers binaires (fallback)
        
        Pour les fichiers non reconnus, on retourne des métadonnées basiques.
        Phase 2 : ajouter détection MIME, analyse d'images, etc.
        """
        
        # Signature des premiers bytes (magic numbers)
        magic_bytes = content[:8].hex() if len(content) >= 8 else content.hex()
        
        # Détection basique des types courants
        detected_type = 'unknown'
        if content.startswith(b'\x89PNG'):
            detected_type = 'PNG image'
        elif content.startswith(b'\xff\xd8\xff'):
            detected_type = 'JPEG image'
        elif content.startswith(b'%PDF'):
            detected_type = 'PDF document'
        elif content.startswith(b'PK'):
            detected_type = 'ZIP archive (ou DOCX/XLSX)'
        
        return {
            'analysis': {
                'detected_type': detected_type,
                'magic_bytes': magic_bytes,
            },
            'message': 'Fichier binaire - traitement limité en Phase 1',
            'supported_operations': [
                'Métadonnées basiques',
                'Détection de type',
            ],
            'future_support': [
                'Extraction de texte PDF',
                'Analyse d\'images',
                'Lecture Excel/Word',
            ]
        }


# =============================================================================
# FONCTIONS UTILITAIRES (hors classe)
# =============================================================================

def get_supported_formats() -> Dict[str, str]:
    """
    Retourne la liste des formats supportés et leur description.
    Utile pour informer l'utilisateur côté mobile.
    """
    return {
        '.txt': 'Fichier texte - Analyse complète (lignes, mots, caractères)',
        '.csv': 'Fichier CSV - Structure, colonnes, aperçu des données',
        '.json': 'Fichier JSON - Validation, structure, clés',
        '.md': 'Fichier Markdown - Traité comme texte',
        '.log': 'Fichier log - Traité comme texte',
        'autres': 'Métadonnées basiques et détection de type',
    }
