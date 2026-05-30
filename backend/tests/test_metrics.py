import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_metrics_endpoint_returns_data():
    """
    Verify that the /api/v1/metrics endpoint returns Prometheus formatted metrics.
    """
    # Trigger a request on some endpoint first to generate metrics data
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    # Fetch metrics
    metrics_res = client.get("/api/v1/metrics")
    assert metrics_res.status_code == 200
    assert metrics_res.headers["content-type"].startswith("text/plain")

    # Assert some metrics are visible
    metrics_text = metrics_res.text
    assert "http_requests_total" in metrics_text
    assert "http_request_duration_seconds" in metrics_text
    assert "dramatiq_queue_depth" in metrics_text

    # Check that it recorded our /health call
    assert 'method="GET"' in metrics_text
    assert 'endpoint="/api/v1/health"' in metrics_text
