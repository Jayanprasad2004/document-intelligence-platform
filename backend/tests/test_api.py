"""
Basic API-flow test. Extend once extraction_service/ocr_service are
implemented -- currently /documents/process will raise NotImplementedError
via the stubbed OCR/extraction layers.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
