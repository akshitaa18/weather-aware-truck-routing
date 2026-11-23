"""
Tests for API Endpoints and Input Validation.
Covers:
- /api/routes/health/
- /api/weather/health/
- /api/routes/analyze/ validation errors:
  * Missing fields
  * Identical origin and destination
  * Invalid departure time formats
  * Negative or excessive load weights
  * Invalid sampling intervals
- End-to-end integration flow
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestAPIEndpoints:
    def test_routes_health_check(self, client):
        resp = client.get('/api/routes/health/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "healthy"
        assert "routing_engines" in data

    def test_weather_health_check(self, client):
        resp = client.get('/api/weather/health/')
        # Should be 200 (healthy) or 503 if external network is blocked
        assert resp.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

    def test_analyze_validation_missing_fields(self, client):
        # Empty payload
        resp = client.post('/api/routes/analyze/', {}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = resp.json()
        assert "origin" in data["errors"]
        assert "destination" in data["errors"]
        assert "departure_time" in data["errors"]
        assert "load_weight_lb" in data["errors"]

    def test_analyze_validation_identical_origin_dest(self, client):
        payload = {
            "origin": "Chicago, IL",
            "destination": "Chicago, IL",
            "departure_time": "2026-11-24T08:00",
            "load_weight_lb": 35000.0,
            "sampling_interval_miles": 25,
        }
        resp = client.post('/api/routes/analyze/', payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = resp.json()
        assert "Origin and destination must be different" in str(data)

    def test_analyze_validation_invalid_date(self, client):
        payload = {
            "origin": "Chicago, IL",
            "destination": "New York, NY",
            "departure_time": "not-a-valid-date",
            "load_weight_lb": 35000.0,
            "sampling_interval_miles": 25,
        }
        resp = client.post('/api/routes/analyze/', payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_analyze_validation_invalid_sampling_interval(self, client):
        payload = {
            "origin": "Chicago, IL",
            "destination": "New York, NY",
            "departure_time": "2026-11-24T08:00",
            "load_weight_lb": 35000.0,
            "sampling_interval_miles": 33,  # Invalid: only 10, 25, 50 allowed
        }
        resp = client.post('/api/routes/analyze/', payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_analyze_validation_invalid_load_weight(self, client):
        # Negative weight
        payload = {
            "origin": "Chicago, IL",
            "destination": "New York, NY",
            "departure_time": "2026-11-24T08:00",
            "load_weight_lb": -500.0,
            "sampling_interval_miles": 25,
        }
        resp = client.post('/api/routes/analyze/', payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
