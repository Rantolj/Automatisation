"""
Configuration centralisée de l'API
Tous les paramètres en un seul endroit, facile à modifier
"""

from pydantic_settings import BaseSettings
from typing import Set

class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # API
    app_name: str = "API Automatisation"
    debug: bool = False
    api_version: str = "1.0.0"
    
    # Fichiers
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    max_file_size_mb: int = 10
    max_file_size_bytes: int = 10 * 1024 * 1024
    
    # Formats acceptés
    allowed_extensions: Set[str] = {'.csv', '.xlsx', '.json', '.txt'}
    statistical_extensions: Set[str] = {'.xlsx', '.csv'}
    
    # Traitement
    process_timeout_seconds: int = 10
    
    # Rate limiting
    rate_limit_requests_per_window: int = 30
    rate_limit_window_seconds: int = 60
    
    # CORS (à restreindre en production)
    cors_origins: list = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Instance unique
settings = Settings()