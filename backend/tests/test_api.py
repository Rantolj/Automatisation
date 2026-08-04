"""
Tests API automatisés avec FastAPI TestClient
À lancer avec: pytest tests/test_api.py -v
"""

import pytest
import tempfile
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHealthAndRoot:
    """Tests des endpoints basiques"""
    
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "online"
    
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestUpload:
    """Tests de l'endpoint /upload"""
    
    def test_upload_text_file_success(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            f.flush()
            
            with open(f.name, 'rb') as upload_file:
                response = client.post(
                    "/upload",
                    files={"file": ("test.txt", upload_file, "text/plain")}
                )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "file_info" in response.json()
    
    def test_upload_unsupported_format(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.exe', delete=False) as f:
            f.write("fake")
            f.flush()
            
            with open(f.name, 'rb') as upload_file:
                response = client.post(
                    "/upload",
                    files={"file": ("bad.exe", upload_file)}
                )
        
        assert response.status_code == 415
        assert response.json()["error_code"] == "UNSUPPORTED_FORMAT"
    
    def test_upload_no_file(self):
        response = client.post("/upload")
        assert response.status_code == 422


class TestProcess:
    """Tests de l'endpoint /process"""
    
    def test_process_text_file(self):
        content = "Line 1\nLine 2\nLine 3"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            f.flush()
            
            with open(f.name, 'rb') as upload_file:
                response = client.post(
                    "/process",
                    files={"file": ("test.txt", upload_file, "text/plain")}
                )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "processing_result" in result
    
    def test_process_csv_file(self):
        content = "nom,age\nAlice,30\nBob,25"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            
            with open(f.name, 'rb') as upload_file:
                response = client.post(
                    "/process",
                    files={"file": ("data.csv", upload_file, "text/csv")}
                )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "summary" in result["processing_result"]
    
    def test_process_json_file(self):
        content = '{"name": "test", "value": 123}'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(content)
            f.flush()
            
            with open(f.name, 'rb') as upload_file:
                response = client.post(
                    "/process",
                    files={"file": ("config.json", upload_file, "application/json")}
                )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
    
    def test_process_unsupported_format(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.exe', delete=False) as f:
            f.write("fake")
            f.flush()
            
            with open(f.name, 'rb') as upload_file:
                response = client.post(
                    "/process",
                    files={"file": ("bad.exe", upload_file)}
                )
        
        assert response.status_code == 415
        assert response.json()["error_code"] == "UNSUPPORTED_FORMAT"


class TestErrors:
    """Tests de gestion d'erreurs"""
    
    def test_error_payload_structure(self):
        """Vérifie que les erreurs ont le bon format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.exe', delete=False) as f:
            f.write("fake")
            f.flush()
            
            with open(f.name, 'rb') as upload_file:
                response = client.post(
                    "/process",
                    files={"file": ("bad.exe", upload_file)}
                )
        
        assert response.status_code == 415
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data
        assert data["success"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])