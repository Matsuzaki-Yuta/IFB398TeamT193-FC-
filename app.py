import os

from flask import Flask
from dotenv import load_dotenv

from backend.routes.api_routes import api
from backend.routes.page_routes import pages

# app.py sits at the repo root, but the templates and design assets live
# under frontend/. These paths let Flask find them.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


def create_app():
    """Create and configure the Flask application."""
    load_dotenv()

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

    # pages renders HTML, api returns JSON under /api.
    app.register_blueprint(pages)
    app.register_blueprint(api)

    return app


app = create_app()


if __name__ == "__main__":
    print("Travel Matcher running on http://localhost:5000")
    app.run(debug=True, port=5000)
