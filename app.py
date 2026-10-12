import os

from dotenv import load_dotenv

# Load .env before importing the routes. backend/models/database.py reads
# PACKAGES_DB_PATH when it is first imported, so loading .env any later would
# silently ignore that setting.
load_dotenv()

from flask import Flask  # noqa: E402

from backend.routes.api_routes import api  # noqa: E402
from backend.routes.page_routes import pages  # noqa: E402

from flask import jsonify
from werkzeug.exceptions import RequestEntityTooLarge

# app.py sits at the repo root, but the templates and design assets live
# under frontend/. These paths let Flask find them.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


def create_app():
    """Create and configure the Flask application."""

    # template_folder points Flask at frontend/templates instead of the
    # default templates/ folder beside this file.
    #
    # static_folder + static_url_path serve frontend/css, frontend/js,
    # frontend/images and frontend/media under the /static/ prefix, which is
    # the prefix the page markup already uses. For example:
    #   /static/css/base/theme.css  ->  frontend/css/base/theme.css
    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=FRONTEND_DIR,
        static_url_path="/static",
    )

    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

    # pages renders HTML, api returns JSON under /api.
    app.register_blueprint(pages)
    app.register_blueprint(api)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(error):
        return jsonify({
            "success": False,
            "error": {
                "code": "FILE_TOO_LARGE",
                "message": "Your video is too large. Please upload a video under 200 MB."
            }
        }), 413

    return app


app = create_app()


if __name__ == "__main__":
    # Debug mode shows code and allows code execution from the browser when an
    # error occurs, so it stays off unless FLASK_DEBUG=1 is set in .env.
    debug = os.environ.get("FLASK_DEBUG") == "1"
    print("Trip Bridge running on http://localhost:5000")
    app.run(debug=debug, port=5000)
