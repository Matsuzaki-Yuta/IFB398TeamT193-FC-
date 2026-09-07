import time
from collections import defaultdict, deque
from threading import Lock

from flask import Blueprint, current_app, jsonify, request

from backend.routes.page_routes import analysis
from backend.services.email_service import (
    EmailConfigurationError, EmailSendError, load_settings,
)
from backend.services.gemini_service import analyze_video_with_gemini
from backend.services.matching_service import fetch_matching_packages
from backend.services.pdf_service import PDF_AVAILABLE
from backend.services.quote_mail import send_quote_email
from backend.services.quote_service import QuoteValidationError, build_quote


ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
}

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


# ── send throttle ───────────────────────────────────────────────────────────────
# /api/quote/send needs no login and will email any address it is given, which
# makes it the one endpoint in this app that could be used to spam someone. This
# keeps a short history of send times per caller and refuses anything past the
# limit.
#
# Known limits, worth stating rather than hiding: the history lives in memory,
# so it resets when Flask restarts and is not shared if the app is ever run with
# more than one worker. For an in-store kiosk demo that is enough. A production
# deployment would use Flask-Limiter backed by Redis.
SEND_LIMIT = 5              # sends ...
SEND_WINDOW_SECONDS = 600   # ... per caller per 10 minutes

_send_history = defaultdict(deque)
_send_history_lock = Lock()


def _caller_key():
    """
    Identifies the caller for throttling.

    X-Forwarded-For is only consulted when the app is knowingly behind a proxy,
    because the header is trivially forged and would otherwise let a caller
    reset their own limit at will.
    """
    if current_app.config.get("TRUST_PROXY_HEADERS"):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _send_allowed(caller):
    now = time.monotonic()
    with _send_history_lock:
        history = _send_history[caller]
        while history and now - history[0] > SEND_WINDOW_SECONDS:
            history.popleft()
        if len(history) >= SEND_LIMIT:
            return False
        history.append(now)
        return True

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

    # Check that the uploaded file is a supported video type.
    if video_file.mimetype not in ALLOWED_VIDEO_MIME_TYPES:
        return error_response(
        "UNSUPPORTED_FILE_TYPE",
        "Only MP4 and MOV video files are supported.",
        415
    )
    
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

    detected_destinations = analysis.get("detected_destinations")
    travel_style = analysis.get("travel_style")

    if detected_destinations is not None and not isinstance(detected_destinations, list):
        return error_response(
            "INVALID_DESTINATIONS",
            "detected_destinations must be a list.",
            400
        )

    if travel_style is not None and not isinstance(travel_style, list):
        return error_response(
            "INVALID_TRAVEL_STYLE",
            "travel_style must be a list.",
            400
        )

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
def preview_quote():
    """
    Builds the quote and returns it, without sending anything.

    This exists so the quote can be checked without an inbox in the loop. It is
    the endpoint to use when testing the pricing rules, and the one to call from
    a browser console when the numbers on the page look wrong.

    How to use:
        POST /api/quote with the same JSON body as /api/quote/send.

    Example request body:
        {
            "customer": {"name": "Jordan", "email": "jordan@example.com",
                         "travellers": 2},
            "quote": {"departure": "2026-12-01", "valid_days": 14,
                      "message": "Optional note from the consultant."},
            "selected_package_id": "product-24766397"
        }

    Success response:
        {
            "success": true,
            "quote": { ... reference, totals, package, dates ... }
        }
    """
    try:
        quote = build_quote(request.get_json(silent=True))
    except QuoteValidationError as error:
        return error_response(error.code, error.message, 400)
    except FileNotFoundError as error:
        current_app.logger.error("Package database missing: %s", error)
        return error_response(
            "DATABASE_MISSING",
            "The package database could not be opened.",
            503,
        )

    return jsonify({"success": True, "quote": quote}), 200


@api.post("/quote/send")
def send_quote():
    """
    Builds the quote and emails it to the customer.

    How to use:
        POST /api/quote/send with a JSON body, from the final quote page.

    Example frontend request:
        const response = await fetch("/api/quote/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

    Important: the price is NOT read from the request. Only the package id is,
    and the figures are rebuilt from packages.db, because anything the browser
    sends is something the customer could have edited first.

    Success response:
        {
            "success": true,
            "quote_reference": "FC-20260827-4F2A",
            "sent_to": "jordan@example.com",
            "attached_pdf": true,
            "total": "A$12,319",
            "valid_until": "10 Sep 2026"
        }

    Error responses use the same shape as every other endpoint here:
        400  INVALID_EMAIL / MISSING_PACKAGE / INVALID_NUMBER ... - fix the input
        429  TOO_MANY_SENDS                                      - slow down
        502  EMAIL_FAILED                                        - relay problem
        503  EMAIL_NOT_CONFIGURED                                - .env problem
    """
    # Validate before throttling, so a typo in an email address does not burn
    # one of the caller's five sends.
    try:
        quote = build_quote(request.get_json(silent=True))
    except QuoteValidationError as error:
        return error_response(error.code, error.message, 400)
    except FileNotFoundError as error:
        current_app.logger.error("Package database missing: %s", error)
        return error_response(
            "DATABASE_MISSING",
            "The package database could not be opened.",
            503,
        )

    if not _send_allowed(_caller_key()):
        return error_response(
            "TOO_MANY_SENDS",
            "Too many quotes have been sent from this device. "
            "Please wait a few minutes and try again.",
            429,
        )

    try:
        result = send_quote_email(quote)

    except EmailConfigurationError as error:
        # A setup problem the team can fix, so the message is shown as-is. It
        # never contains the password: see email_service.send_message.
        current_app.logger.error("Email configuration problem: %s", error)
        return error_response("EMAIL_NOT_CONFIGURED", str(error), 503)

    except EmailSendError as error:
        current_app.logger.error("Quote email failed to send: %s", error)
        return error_response(
            "EMAIL_FAILED",
            "The quote could not be sent right now. Please try again in a moment.",
            502,
        )

    except Exception:
        current_app.logger.exception("Unexpected failure while sending the quote")
        return error_response(
            "EMAIL_FAILED",
            "The quote could not be sent right now. Please try again in a moment.",
            500,
        )

    # A quote that was emailed but never recorded is invisible to the team, so
    # the reference and recipient go to the log. The body and the PDF do not.
    current_app.logger.info(
        "Quote %s emailed to %s (pdf=%s)",
        quote["reference"], quote["customer"]["email"], result["attached_pdf"],
    )

    return jsonify({
        "success": True,
        "quote_reference": quote["reference"],
        "sent_to": quote["customer"]["email"],
        "attached_pdf": result["attached_pdf"],
        "total": quote["money"]["total"],
        "valid_until": quote["valid_until_display"],
    }), 200


@api.get("/email/status")
def email_status():
    """
    Reports whether email is set up, without sending anything.

    Made for demo mornings: open /api/email/status and you know in one second
    whether the .env file is loaded, instead of finding out when the send button
    fails in front of the industry partner.

    Never returns the password, and returns the username only as its domain.

    Success response:
        {
            "success": true,
            "configured": true,
            "host": "smtp.gmail.com",
            "port": 587,
            "account_domain": "gmail.com",
            "pdf_attachments": true
        }
    """
    try:
        settings = load_settings()
    except EmailConfigurationError as error:
        return jsonify({
            "success": True,
            "configured": False,
            "detail": str(error),
            "pdf_attachments": PDF_AVAILABLE,
        }), 200

    username = settings["username"]
    return jsonify({
        "success": True,
        "configured": True,
        "host": settings["host"],
        "port": settings["port"],
        "account_domain": username.split("@")[-1] if "@" in username else None,
        "from_email": settings["from_email"],
        "from_mismatch": settings.get("from_mismatch") is not None,
        "pdf_attachments": PDF_AVAILABLE,
    }), 200
