"""
=============================================================================
SCRIPT DE TEST - Phase 1
=============================================================================

Script simple pour tester l'API sans framework de test.
Exécutable directement pour valider le bon fonctionnement.

Usage :
    1. Lancer le serveur : python main.py
    2. Dans un autre terminal : python tests/test_api.py

=============================================================================
"""

import requests
import json
import tempfile
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"

# Couleurs pour l'affichage console
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_header(title: str):
    """Affiche un en-tête de section"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")


def print_result(test_name: str, success: bool, details: str = ""):
    """Affiche le résultat d'un test"""
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if success else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {Colors.YELLOW}{details}{Colors.END}")


def test_health_check():
    """Test du endpoint /health"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        success = response.status_code == 200 and response.json().get("status") == "healthy"
        print_result("Health Check", success, f"Status: {response.json().get('status')}")
        return success
    except Exception as e:
        print_result("Health Check", False, str(e))
        return False


def test_root_endpoint():
    """Test du endpoint racine /"""
    try:
        response = requests.get(f"{BASE_URL}/")
        success = response.status_code == 200 and "status" in response.json()
        print_result("Root Endpoint", success)
        return success
    except Exception as e:
        print_result("Root Endpoint", False, str(e))
        return False


def test_upload_text_file():
    """Test d'upload d'un fichier texte"""
    try:
        # Création d'un fichier temporaire
        content = "Ceci est un test.\nDeuxième ligne.\nTroisième ligne."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/upload",
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            success = response.status_code == 200 and response.json().get("success") == True
            print_result("Upload Text File", success, 
                        f"Size: {response.json().get('file_info', {}).get('size_readable', 'N/A')}")
            return success
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        print_result("Upload Text File", False, str(e))
        return False


def test_process_text_file():
    """Test de traitement d'un fichier texte"""
    try:
        content = """Voici un fichier de test.
Il contient plusieurs lignes.
Chaque ligne est analysée.
Le traitement compte les mots et caractères.
Fin du fichier."""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/process",
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            result = response.json()
            analysis = result.get('processing_result', {}).get('analysis', {})
            
            success = (
                response.status_code == 200 and 
                result.get("success") == True and
                analysis.get('line_count', 0) == 5
            )
            
            print_result("Process Text File", success,
                        f"Lines: {analysis.get('line_count')}, Words: {analysis.get('word_count')}")
            return success
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        print_result("Process Text File", False, str(e))
        return False


def test_process_csv_file():
    """Test de traitement d'un fichier CSV"""
    try:
        content = """nom,age,ville
Alice,30,Paris
Bob,25,Lyon
Charlie,35,Marseille"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/process",
                    files={"file": ("data.csv", f, "text/csv")}
                )
            
            result = response.json()
            analysis = result.get('processing_result', {}).get('analysis', {})
            
            success = (
                response.status_code == 200 and
                analysis.get('column_count') == 3 and
                analysis.get('data_row_count') == 3
            )
            
            print_result("Process CSV File", success,
                        f"Columns: {analysis.get('headers')}, Rows: {analysis.get('data_row_count')}")
            return success
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        print_result("Process CSV File", False, str(e))
        return False


def test_process_json_file():
    """Test de traitement d'un fichier JSON"""
    try:
        data = {
            "name": "Test Project",
            "version": "1.0.0",
            "features": ["upload", "process", "download"],
            "config": {
                "debug": True,
                "port": 8000
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(data, f)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/process",
                    files={"file": ("config.json", f, "application/json")}
                )
            
            result = response.json()
            processing = result.get('processing_result', {})
            
            success = (
                response.status_code == 200 and
                processing.get('valid') == True and
                processing.get('structure', {}).get('type') == 'dict'
            )
            
            print_result("Process JSON File", success,
                        f"Valid: {processing.get('valid')}, Keys: {processing.get('structure', {}).get('key_count')}")
            return success
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        print_result("Process JSON File", False, str(e))
        return False


def test_process_invalid_json():
    """Test de traitement d'un JSON invalide"""
    try:
        # JSON invalide (manque une accolade)
        content = '{"name": "test", "value": '
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/process",
                    files={"file": ("invalid.json", f, "application/json")}
                )
            
            result = response.json()
            processing = result.get('processing_result', {})
            
            # Le test réussit si l'API détecte bien que le JSON est invalide
            success = (
                response.status_code == 200 and
                processing.get('valid') == False
            )
            
            print_result("Process Invalid JSON", success,
                        f"Correctly detected as invalid: {processing.get('valid') == False}")
            return success
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        print_result("Process Invalid JSON", False, str(e))
        return False


def test_upload_without_file():
    """Test d'upload sans fichier (doit échouer)"""
    try:
        response = requests.post(f"{BASE_URL}/upload")
        
        # Doit retourner une erreur 422 (Unprocessable Entity)
        success = response.status_code == 422
        
        print_result("Upload Without File (should fail)", success,
                    f"Status code: {response.status_code} (expected 422)")
        return success
        
    except Exception as e:
        print_result("Upload Without File", False, str(e))
        return False


def run_all_tests():
    """Exécute tous les tests et affiche un résumé"""
    
    print_header("TESTS API - Phase 1")
    print(f"URL: {BASE_URL}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Vérification que le serveur est accessible
    print_header("1. Tests de connectivité")
    
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}ERREUR: Le serveur n'est pas accessible sur {BASE_URL}{Colors.END}")
        print(f"{Colors.YELLOW}Lancez le serveur avec: python main.py{Colors.END}")
        return
    
    results = []
    
    # Tests de base
    results.append(("Health Check", test_health_check()))
    results.append(("Root Endpoint", test_root_endpoint()))
    
    # Tests d'upload
    print_header("2. Tests d'upload")
    results.append(("Upload Text File", test_upload_text_file()))
    results.append(("Upload Without File", test_upload_without_file()))
    
    # Tests de traitement
    print_header("3. Tests de traitement")
    results.append(("Process Text File", test_process_text_file()))
    results.append(("Process CSV File", test_process_csv_file()))
    results.append(("Process JSON File", test_process_json_file()))
    results.append(("Process Invalid JSON", test_process_invalid_json()))
    
    # Résumé
    print_header("RÉSUMÉ")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nTests réussis: {passed}/{total}")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ Tous les tests sont passés !{Colors.END}")
    else:
        print(f"{Colors.RED}✗ Certains tests ont échoué{Colors.END}")
        print("\nTests échoués:")
        for name, success in results:
            if not success:
                print(f"  - {name}")


if __name__ == "__main__":
    run_all_tests()
