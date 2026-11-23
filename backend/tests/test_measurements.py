"""
Tests for POST /measurements endpoint.
FR-6: Validate batch accept, coordinate ranges, RSRP plausibility.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import Contributor


@pytest.fixture
def contributor(db):
    return Contributor.objects.create_user(
        username="testuser",
        email="test@altisignal.dev",
        password="TestPass123!",
    )


@pytest.fixture
def auth_client(contributor):
    client = APIClient()
    refresh = RefreshToken.for_user(contributor)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


VALID_READING = {
    "timestamp": "2026-11-22T10:00:00Z",
    "longitude": 78.350,
    "latitude": 17.440,
    "altitude": 90.0,
    "altitude_band": "90",
    "rsrp": -95.0,
    "rsrq": -10.0,
    "sinr": 5.0,
    "cell_id": "123456",
    "pci": 42,
    "band": "B40",
    "network_type": "LTE",
    "device_model": "Pixel 7",
    "operator": "Airtel",
}


@pytest.mark.django_db
class TestMeasurementBatch:
    url = "/api/v1/measurements/"

    def test_unauthenticated_returns_401(self, client):
        response = client.post(self.url, {"readings": [VALID_READING]}, content_type="application/json")
        assert response.status_code == 401

    def test_valid_batch_accepted(self, auth_client):
        response = auth_client.post(
            self.url,
            {"readings": [VALID_READING]},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["accepted"] == 1

    def test_multiple_readings_accepted(self, auth_client):
        readings = [{**VALID_READING, "rsrp": -80.0 - i} for i in range(5)]
        response = auth_client.post(self.url, {"readings": readings}, format="json")
        assert response.status_code == 201
        assert response.data["accepted"] == 5

    def test_invalid_rsrp_rejected(self, auth_client):
        bad_reading = {**VALID_READING, "rsrp": 10.0}  # Out of range
        response = auth_client.post(self.url, {"readings": [bad_reading]}, format="json")
        assert response.status_code == 400

    def test_invalid_longitude_rejected(self, auth_client):
        bad_reading = {**VALID_READING, "longitude": 200.0}
        response = auth_client.post(self.url, {"readings": [bad_reading]}, format="json")
        assert response.status_code == 400

    def test_empty_batch_rejected(self, auth_client):
        response = auth_client.post(self.url, {"readings": []}, format="json")
        assert response.status_code == 400

    def test_too_large_batch_rejected(self, auth_client):
        readings = [VALID_READING] * 1001
        response = auth_client.post(self.url, {"readings": readings}, format="json")
        assert response.status_code == 400

    def test_h3_index_assigned(self, auth_client):
        from apps.measurements.models import Measurement
        auth_client.post(self.url, {"readings": [VALID_READING]}, format="json")
        m = Measurement.objects.last()
        assert m.h3_index != ""

    def test_contributor_attached(self, auth_client, contributor):
        from apps.measurements.models import Measurement
        auth_client.post(self.url, {"readings": [VALID_READING]}, format="json")
        m = Measurement.objects.last()
        assert m.contributor == contributor

    def test_altitude_band_auto_classified(self, auth_client):
        from apps.measurements.models import Measurement
        reading_no_band = {**VALID_READING, "altitude": 62.0}
        reading_no_band.pop("altitude_band")
        response = auth_client.post(self.url, {"readings": [reading_no_band]}, format="json")
        assert response.status_code == 201
        m = Measurement.objects.last()
        assert m.altitude_band == "60"


@pytest.mark.django_db
class TestCellsAndGapViews:
    def test_cells_list_and_gap_views(self, auth_client):
        from apps.cells.models import CellStat
        from django.contrib.gis.geos import Point

        CellStat.objects.create(
            h3_index="8860a25997fffff",
            altitude_band="0",
            centroid=Point(78.35, 17.44, srid=4326),
            count=20,
            mean_rsrp=-75.0,
            fraction_below_threshold=0.0,
            confidence=0.8,
        )
        CellStat.objects.create(
            h3_index="8860a25997fffff",
            altitude_band="90",
            centroid=Point(78.35, 17.44, srid=4326),
            count=15,
            mean_rsrp=-115.0,
            fraction_below_threshold=0.8,
            confidence=0.75,
        )

        # GET /api/v1/cells/
        res_cells = auth_client.get("/api/v1/cells/?altitude=90")
        assert res_cells.status_code == 200

        # GET /api/v1/cells/gap/
        res_gap = auth_client.get("/api/v1/cells/gap/?altitude=90")
        assert res_gap.status_code == 200
        data = res_gap.data
        assert len(data) >= 1
        assert data[0]["delta_rsrp"] == 40.0  # -75 - (-115) = 40 dBm drop

        # Direct PRD path GET /api/v1/gap/
        res_gap_direct = auth_client.get("/api/v1/gap/?altitude=90")
        assert res_gap_direct.status_code == 200
        assert len(res_gap_direct.data) >= 1


@pytest.mark.django_db
class TestRouteRisk:
    url = "/api/v1/predictions/route-risk/"

    def test_valid_route(self, auth_client):
        payload = {
            "route": {
                "type": "LineString",
                "coordinates": [
                    [78.330, 17.420],
                    [78.360, 17.450],
                    [78.380, 17.470],
                ]
            },
            "altitude_band": "90",
        }
        response = auth_client.post(self.url, payload, format="json")
        assert response.status_code == 200
        data = response.data
        assert "segments" in data
        assert "overall_risk" in data
        assert "advisory" in data
        assert len(data["segments"]) == 2  # 3 coords = 2 segments

        # Direct PRD path POST /api/v1/route-risk/
        res_direct = auth_client.post("/api/v1/route-risk/", payload, format="json")
        assert res_direct.status_code == 200
        assert len(res_direct.data["segments"]) == 2

    def test_invalid_geometry_rejected(self, auth_client):
        payload = {
            "route": {"type": "Point", "coordinates": [78.35, 17.44]},
            "altitude_band": "60",
        }
        response = auth_client.post(self.url, payload, format="json")
        assert response.status_code == 400

    def test_single_coordinate_rejected(self, auth_client):
        payload = {
            "route": {"type": "LineString", "coordinates": [[78.35, 17.44]]},
            "altitude_band": "60",
        }
        response = auth_client.post(self.url, payload, format="json")
        assert response.status_code == 400
