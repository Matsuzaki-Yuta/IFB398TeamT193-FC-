from unittest.mock import patch


def test_package_match_missing_analysis(client):
    response = client.post(
        "/api/packages/match",
        json={}
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_ANALYSIS"


@patch("backend.routes.api_routes.fetch_matching_packages")
def test_package_match_success(mock_match, client):
    mock_match.return_value = [
        {
            "id": "package-001",
            "destination": "Bali, Indonesia",
            "match_score": 2
        }
    ]

    response = client.post(
        "/api/packages/match",
        json={
            "analysis": {
                "detected_destinations": ["Bali"],
                "destination_region": "Indonesia",
                "travel_style": ["adventure"]
            }
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["total_matches"] == 1
    assert len(data["packages"]) == 1

    mock_match.assert_called_once_with(
        ["Bali", "Indonesia"],
        ["adventure"]
    )


@patch("backend.routes.api_routes.fetch_matching_packages")
def test_package_match_failure(mock_match, client):
    mock_match.side_effect = Exception(
        "Database failure"
    )

    response = client.post(
        "/api/packages/match",
        json={
            "analysis": {
                "detected_destinations": ["Bali"],
                "travel_style": ["adventure"]
            }
        }
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "MATCHING_FAILED"


def test_package_match_rejects_invalid_destinations(client):
    response = client.post(
        "/api/packages/match",
        json={
            "analysis": {
                "detected_destinations": "Bali",
                "travel_style": ["adventure"]
            }
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_DESTINATIONS"


def test_package_match_rejects_invalid_travel_style(client):
    response = client.post(
        "/api/packages/match",
        json={
            "analysis": {
                "detected_destinations": ["Bali"],
                "travel_style": "adventure"
            }
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_TRAVEL_STYLE"


def test_package_match_rejects_non_object_analysis(client):
    response = client.post(
        "/api/packages/match",
        json={
            "analysis": "invalid"
        }
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_ANALYSIS"