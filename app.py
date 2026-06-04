import os
import json
import time
import tempfile
import sqlite3
from flask import Flask, request, jsonify, send_from_directory, render_template
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".")

YOUR_KEY = os.getenv("GEMINI_API_KEY")
if not YOUR_KEY:
    raise ValueError("GEMINI_API_KEY not set in environment variables")

DB_PATH = os.path.join(os.path.dirname(__file__), "packages.db")

# ── Configure Gemini ──────────────────────────────────────────────────────────
client = genai.Client(api_key=YOUR_KEY)


# ── DB helpers ────────────────────────────────────────────────────────────────
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_matching_packages(destination_terms: list[str], vibe_terms: list[str]) -> list[dict]:
    """
    Fetch packages from SQLite where:
      - destination matches any of destination_terms (substring, case-insensitive)
      - AND vibe_tags contains at least one of vibe_terms
    Returns list of dicts with matched_destination and matched_vibes added.
    """
    if not destination_terms or not vibe_terms:
        return []

    conn = get_connection()
    cur = conn.cursor()

    # Build WHERE clause for destination: any term matches
    dest_conditions = " OR ".join(
        ["LOWER(destination) LIKE ?"] * len(destination_terms)
    )
    dest_params = [f"%{t.lower()}%" for t in destination_terms]

    rows = cur.execute(
        f"SELECT * FROM packages WHERE {dest_conditions}",
        dest_params
    ).fetchall()
    conn.close()

    vibe_set = set(v.lower() for v in vibe_terms)
    results = []

    for row in rows:
        pkg = dict(row)
        pkg_vibes = set(json.loads(pkg["vibe_tags"] or "[]"))
        overlap = vibe_set & pkg_vibes
        if not overlap:
            continue  # needs at least one vibe match

        # Deserialise JSON fields
        pkg["inclusions"] = json.loads(pkg["inclusions"] or "[]")
        pkg["highlights"] = json.loads(pkg["highlights"] or "[]")
        pkg["vibe_tags"] = list(pkg_vibes)
        pkg["matched_destination"] = next(
            (t for t in destination_terms if t.lower() in pkg["destination"].lower()), destination_terms[0]
        )
        pkg["matched_vibes"] = sorted(overlap)

        pkg["match_reasons"] = [
            f"Destination matched: {pkg['matched_destination']}"
        ]

        if pkg["matched_vibes"]:
            pkg["match_reasons"].append(
                f"Travel style matched: {', '.join(pkg['matched_vibes'])}"
            )

        pkg["match_score"] = len(pkg["matched_vibes"])
        
        results.append(pkg)

    return results


# ── Gemini video analysis ─────────────────────────────────────────────────────
def analyze_video_with_gemini(video_bytes: bytes, mime_type: str) -> dict:
    prompt = """Analyze this travel video and extract key travel information.
Return ONLY a valid JSON object (no markdown, no explanation) with these fields:
{
  "detected_destinations": ["list of countries, cities, or regions visible"],
  "destination_region": "broad region e.g. Europe, Asia, South America, Africa, etc.",
  "travel_style": ["pick from: adventure, budget, city, cruise, cultural, family, food, luxury, nightlife, relaxation, romance, wellness"],
  "estimated_duration_days": null or a number if evident,
  "activities": ["list of activities shown"],
  "landmarks": ["list of specific landmarks or attractions"],
  "confidence": "high/medium/low"
}"""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        video_file = client.files.upload(file=tmp_path)

        while( getattr(video_file, "state", None) and video_file.state.name == "PROCESSING"):
            time.sleep(2)

            video_file = client.files.get(name=video_file.name)
        
        repsonse = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                video_file,
                prompt
            ]
        )

        raw = repsonse.text.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "")
            raw = raw.replace("```", "")
            raw = raw.strip()

        return json.loads(raw)
    
    finally:
        os.unlink(tmp_path)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "video" not in request.files:
        return jsonify({"error": "No video file uploaded"}), 400

    video_file = request.files["video"]
    video_bytes = video_file.read()
    mime_type = video_file.mimetype or "video/mp4"

    try:
        video_info = analyze_video_with_gemini(video_bytes, mime_type)

        # Build search terms from Gemini output
        destination_terms = list(video_info.get("detected_destinations") or [])
        if video_info.get("destination_region"):
            destination_terms.append(video_info["destination_region"])

        vibe_terms = list(video_info.get("travel_style") or [])

        matched = fetch_matching_packages(destination_terms, vibe_terms)

        return jsonify({
            "video_analysis": video_info,
            "matched_packages": matched,
            "total_matches": len(matched)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
    conn.close()
    print(f"Travel Matcher — {count} packages loaded from {DB_PATH}")
    print("Running on http://localhost:5000")
    app.run(debug=True, port=5000)
