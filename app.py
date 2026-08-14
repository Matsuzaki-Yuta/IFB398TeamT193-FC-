from flask import Flask, render_template
from dotenv import load_dotenv

from routes.api_routes import api


def create_app():
    """Create and configure the Flask application."""
    load_dotenv()
    app = Flask(__name__)
    app.register_blueprint(api)

    @app.get("/")
    def index():
        return render_template("index.html")

    return app


app = create_app()


if __name__ == "__main__":
    print("Travel Matcher running on http://localhost:5000")
    app.run(debug=True, port=5000)