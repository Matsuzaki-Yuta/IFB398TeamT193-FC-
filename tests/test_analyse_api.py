import io
from unittest.mock import patch


def test_analyse_without_video(client):
    response = client.post("/api/analyse")

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_FILE"


def test_analyse_empty_video(client):
    response = client.post(
        "/api/analyse",
        data={
            "video": (
                io.BytesIO(b""),
                ""
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "EMPTY_FILE"


@patch("backend.routes.api_routes.analyze_video_with_gemini")
def test_analyse_success(mock_analyse, client):
    mock_analyse.return_value = {
        "detected_destinations": ["Bali"],
        "destination_region": "Indonesia",
        "travel_style": ["adventure", "wellness"],
        "estimated_duration_days": 7,
        "activities": ["surfing"],
        "landmarks": ["Uluwatu Temple"],
        "confidence": "high",
    }

    response = client.post(
        "/api/analyse",
        data={
            "video": (
                io.BytesIO(b"fake video data"),
                "test.mp4"
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["analysis"]["detected_destinations"] == ["Bali"]
    assert data["analysis"]["destination_region"] == "Indonesia"

    mock_analyse.assert_called_once()


@patch("backend.routes.api_routes.analyze_video_with_gemini")
def test_analyse_configuration_error(mock_analyse, client):
    mock_analyse.side_effect = ValueError(
        "Gemini API key is not configured."
    )

    response = client.post(
        "/api/analyse",
        data={
            "video": (
                io.BytesIO(b"fake video data"),
                "test.mp4"
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 503

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_CONFIGURATION"


@patch("backend.routes.api_routes.analyze_video_with_gemini")
def test_analyse_internal_error(mock_analyse, client):
    mock_analyse.side_effect = Exception("Unexpected error")

    response = client.post(
        "/api/analyse",
        data={
            "video": (
                io.BytesIO(b"fake video data"),
                "test.mp4"
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "ANALYSIS_FAILED"

def test_analyse_rejects_invalid_file_type(client):
    response = client.post(
        "/api/analyse",
        data={
            "video": (
                io.BytesIO(b"not a video"),
                "test.txt",
                "text/plain"
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 415

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

def test_analyse_rejects_invalid_file_type(client):
    response = client.post(
        "/api/analyse",
        data={
            "video": (
                io.BytesIO(b"not a video"),
                "test.txt",
                "text/plain"
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 415

    data = response.get_json()

    assert data["success"] is False
    assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


@patch("backend.routes.api_routes.analyze_video_with_gemini")
def test_analyse_accepts_mov_file(mock_analyse, client):
    mock_analyse.return_value = {
        "detected_destinations": ["Tokyo"],
        "destination_region": "Japan",
        "travel_style": ["cultural"],
        "activities": [],
        "landmarks": [],
        "confidence": "high",
    }

    response = client.post(
        "/api/analyse",
        data={
            "video": (
                io.BytesIO(b"fake mov data"),
                "test.mov",
                "video/quicktime"
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True


def test_analyse_rejects_oversized_file(client):
    large_file = io.BytesIO(b"a" * (51 * 1024 * 1024))

    response = client.post(
        "/api/analyse",
        data={
            "video": (
                large_file,
                "large_video.mp4",
                "video/mp4"
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 413