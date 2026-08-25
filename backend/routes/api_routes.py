from flask import Blueprint, current_app, jsonify, request

from backend.services.gemini_service import analyze_video_with_gemini
from backend.services.matching_service import fetch_matching_packages

# Creates a group of API routes.
# Every endpoint in this file automatically starts with "/api".
#
# Example:
# @api.get("/health") becomes GET /api/health
api = Blueprint("api", __name__, url_prefix="/api")

def error_response(code, message, status_code):
    """
    Creates a consistent JSON error response.

    Parameters:
        code: A short error identifier used by the frontend.
        message: A user-friendly explanation of the error.
        status_code: The HTTP status code, such as 400 or 500.

    Example response:
        {
            "success": false,
            "error": {
                "code": "MISSING_FILE",
                "message": "Please upload a video."
            }
        }
    """

    return jsonify({
        "success": False,
        "error": {"code": code, "message": message},
    }), status_code

@api.get("/health")
def health():
    """
    Confirms that the Flask backend is running.

    How to use:
        Send a GET request to /api/health.

    No request body or uploaded file is required.

    The frontend can call this endpoint before using the application to
    confirm that it can communicate with the backend.

    Example frontend request:
        fetch("/api/health")

    Success response:
        {
            "success": true,
            "status": "healthy"
        }
    """
    return jsonify({"success": True, "status": "healthy"}), 200
 
@api.post("/analyse")
def analyse_video():
    """
    Receives an uploaded travel video and sends it to Gemini for analysis.

    How to use:
        Send a POST request to /api/analyse using multipart/form-data.

    The uploaded file must use the field name "video".

    Example frontend request:
        const formData = new FormData();
        formData.append("video", selectedFile);

        const response = await fetch("/api/analyse", {
            method: "POST",
            body: formData
        });

    Do not manually set the Content-Type header when using FormData.
    The browser automatically creates the correct multipart boundary.

    Success response:
        {
            "success": true,
            "analysis": {
                "detected_destinations": ["Bali"],
                "destination_region": "Indonesia",
                "travel_style": ["adventure", "wellness"],
                "estimated_duration_days": 7,
                "activities": ["surfing", "yoga"],
                "landmarks": ["Uluwatu Temple"],
                "confidence": "high"
            }
        }
    """
    # Check that the request contains a field called "video".
    if "video" not in request.files:
        return error_response("MISSING_FILE", "Please upload a video.", 400)

    # Retrieve the uploaded video from the request.
    video_file = request.files["video"]
    if not video_file.filename:
        return error_response("EMPTY_FILE", "Please select a video file.", 400)
    
    # The field may exist even though the user did not select a file.
    try:
        # Read the video as bytes and pass it to the Gemini service.
        analysis = analyze_video_with_gemini(
            video_file.read(), video_file.mimetype or "video/mp4"
        )
        # Return Gemini's structured analysis to the frontend.
        return jsonify({"success": True, "analysis": analysis}), 200
    
    except ValueError as error:
        # Handles configuration problems such as a missing Gemini API key.
        return error_response("INVALID_CONFIGURATION", str(error), 503)
    
    except Exception:
        # Record technical information in the server logs.
        current_app.logger.exception("Video analysis failed")
        # Return a safe and understandable message to the user.
        return error_response(
            "ANALYSIS_FAILED",
            "The video could not be analysed. Please try again.",
            500,
        )


@api.post("/packages/match")
def match_packages():
    """
    Uses Gemini's analysis to find relevant packages in the database.

    This endpoint should normally be called after /api/analyse.

    How to use:
        Send a POST request to /api/packages/match with a JSON body.

    Example frontend request:
        const response = await fetch("/api/packages/match", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                analysis: analysisResult
            })
        });

    Example request body:
        {
            "analysis": {
                "detected_destinations": ["Bali"],
                "destination_region": "Indonesia",
                "travel_style": ["adventure", "wellness"],
                "activities": ["surfing"]
            }
        }

    Success response:
        {
            "success": true,
            "packages": [
                {
                    "id": "package-001",
                    "name": "Bali Escape",
                    "destination": "Bali, Indonesia",
                    "match_score": 2,
                    "match_reasons": [
                        "Destination matched: Bali",
                        "Travel style matched: adventure, wellness"
                    ]
                }
            ],
            "total_matches": 1
        }
    """
    # Read the JSON data sent by the frontend.
    #
    # silent=True prevents Flask from showing its own error page when
    # invalid JSON is received. Instead, data will be None.
    data = request.get_json(silent=True)

    # Confirm that the request contains an "analysis" JSON object.
    if not data or not isinstance(data.get("analysis"), dict):
        return error_response(
            "MISSING_ANALYSIS", "Video analysis data is required.", 400
        )

    analysis = data["analysis"]

    # Get specific destinations detected by Gemini.
    #
    # Example:
    # ["Bali", "Ubud"]
    destination_terms = list(analysis.get("detected_destinations") or [])

    # Add the broader country or region as another possible search term.
    #
    # Example final list:
    # ["Bali", "Ubud", "Indonesia"]
    if analysis.get("destination_region"):
        destination_terms.append(analysis["destination_region"])

    # Get the travel styles detected by Gemini.
    #
    # Example:
    # ["adventure", "wellness"]
    vibe_terms = list(analysis.get("travel_style") or [])

    try:
        # Search the SQLite package database using destinations and styles.
        packages = fetch_matching_packages(destination_terms, vibe_terms)

    except Exception:
        # Save the technical exception in the backend logs.
        current_app.logger.exception("Package matching failed")

        # Return a safe error message to the frontend.
        return error_response(
            "MATCHING_FAILED",
            "Packages could not be matched. Please try again.",
            500,
        )

    # Return all matching packages and their total number.
    return jsonify({
        "success": True,
        "packages": packages,
        "total_matches": len(packages),
    }), 200

@api.post("/quote")
def create_quote():
    """
    Placeholder endpoint for generating the final trip summary.

    How it will eventually be used:
        The frontend will send the customer profile, Gemini analysis and
        selected package as JSON.

    Planned request body:
        {
            "customer": {
                "name": "Alex",
                "travellers": 2,
                "travel_window": "December 2026",
                "budget_max_aud": 5000
            },
            "analysis": {
                "detected_destinations": ["Bali"],
                "travel_style": ["wellness", "adventure"]
            },
            "selected_package_id": "package-001"
        }

    Planned result:
        The endpoint will combine the customer information and selected
        package to generate a final trip recommendation summary.

    Current result:
        It only confirms that the endpoint exists. Quote generation has
        not been implemented yet.
    """
    return jsonify({
        "success": True,
        "message": "Quote generation is not implemented yet.",
    }), 200