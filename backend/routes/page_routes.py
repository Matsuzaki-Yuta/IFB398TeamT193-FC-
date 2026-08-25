import os
from urllib.parse import quote

from flask import Blueprint, current_app, redirect, render_template, url_for

# Creates the group of routes that render HTML pages.
#
# This blueprint has no url_prefix, unlike the api blueprint, because these
# URLs are the ones typed into the address bar and written into the page
# markup. Keeping them separate from api_routes.py means the API file stays
# purely JSON, and every page lives in one predictable place.
pages = Blueprint("pages", __name__)

# File types treated as playable footage by the landing page hero.
VIDEO_EXTENSIONS = (".mp4", ".webm", ".ogv", ".m4v")

# Shared by every page that includes components/_process_nav.html.
#
# The url values must match the routes defined further down, otherwise the
# step navigation will link to pages that do not exist.
PROCESS_STEPS = [
    {"id": "welcome", "number": 1, "label": "Welcome", "url": "/landing"},
    {"id": "customer", "number": 2, "label": "Customer", "url": "/customer"},
    {"id": "inspiration", "number": 3, "label": "Inspiration", "url": "/match"},
    {"id": "insights", "number": 4, "label": "Insights", "url": "/analysis"},
    {"id": "build", "number": 5, "label": "Build Package", "url": "/packages"},
    {"id": "quote", "number": 6, "label": "Final Quote", "url": "/finalquote"},
]


def process_nav_context(current_id):
    """
    Builds the values the step navigation needs to highlight the right step.

    Parameters:
        current_id: The "id" of the step being shown, such as "customer".

    Every page route passes the result of this into render_template, so the
    navigation bar knows which of the six steps the user is currently on.
    """
    step_ids = [step["id"] for step in PROCESS_STEPS]

    return {
        "process_steps": PROCESS_STEPS,
        "process_current": current_id,
        "process_current_index": step_ids.index(current_id),
    }


def hero_videos():
    """
    Lists every video in frontend/media as a /static URL, in filename order.

    The landing page plays whatever it finds, so footage can be added or
    swapped by dropping files into the folder. An empty folder is fine: the
    hero falls back to its own background.
    """
    # static_folder is frontend/, configured in app.py.
    media_directory = os.path.join(current_app.static_folder, "media")

    if not os.path.isdir(media_directory):
        return []

    names = sorted(
        name for name in os.listdir(media_directory)
        if name.lower().endswith(VIDEO_EXTENSIONS)
    )

    # quote() so that spaces, "&", "#" or "?" in a filename cannot break the URL.
    return [f"/static/media/{quote(name)}" for name in names]


@pages.get("/")
def index():
    """
    Sends the site root to step 1.

    The navigation bar links to "/", so this keeps that link working while
    leaving the landing page on its own named URL.
    """
    return redirect(url_for("pages.landing"))


@pages.get("/landing")
def landing():
    """Step 1: the landing page."""
    return render_template(
        "pages/landing.html",
        hero_videos=hero_videos(),
        **process_nav_context("welcome"),
    )


@pages.get("/customer")
def customer():
    """Step 2: who is travelling, when, and on roughly what budget."""
    return render_template(
        "pages/customer.html",
        **process_nav_context("customer"),
    )


@pages.get("/match")
def match():
    """
    Step 3: choose a travel video and send it for analysis.

    The URL is /match but the template is upload.html. The page markup and
    JavaScript already link to /match, so the URL is kept as-is rather than
    editing every link.
    """
    return render_template(
        "pages/upload.html",
        **process_nav_context("inspiration"),
    )


@pages.get("/analysis")
def analysis():
    """Step 4: what Gemini read from the uploaded clip."""
    return render_template(
        "pages/analysis.html",
        **process_nav_context("insights"),
    )


@pages.get("/packages")
def packages():
    """
    Step 5: the matched packages, ranked and explained.

    As with /match, the URL is /packages while the template is results.html.
    """
    return render_template(
        "pages/results.html",
        **process_nav_context("build"),
    )


@pages.get("/finalquote")
def finalquote():
    """Step 6: confirm the chosen package and send the quote across."""
    return render_template(
        "pages/finalquote.html",
        **process_nav_context("quote"),
    )
