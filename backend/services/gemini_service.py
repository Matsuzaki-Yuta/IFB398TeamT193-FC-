import json
import os
import tempfile
import time

from google import genai


PROMPT = """Analyze this travel video and extract key travel information.
Return ONLY a valid JSON object (no markdown, no explanation) with these fields:
{
  "detected_destinations": ["list of countries, cities, or regions visible"],
  "destination_region": "broad region e.g. Europe, Asia, South America, Africa, etc.",
  "travel_style": ["pick from: adventure, budget, city, cruise, cultural, family, food, luxury, nightlife, relaxation, romance, wellness"],
  "estimated_duration_days": null,
  "activities": ["list of activities shown"],
  "landmarks": ["list of specific landmarks or attractions"],
  "confidence": "high/medium/low"
}"""


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key is not configured.")
    return genai.Client(api_key=api_key)


def analyze_video_with_gemini(video_bytes, mime_type):
    suffix = ".mov" if mime_type == "video/quicktime" else ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(video_bytes)
        temp_path = temp_file.name

    client = get_client()
    try:
        video_file = client.files.upload(file=temp_path)

        #Large videos might not be ready immediately. The code checks every two seconds until Gemini finishes processing the file.
        while (getattr(video_file, "state", None) and video_file.state.name == "PROCESSING"):
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)

        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[video_file, PROMPT]
        )
        raw_response = response.text.strip()
        if raw_response.startswith("```"):
            raw_response = raw_response.replace("```json", "")
            raw_response = raw_response.replace("```", "").strip()
        return json.loads(raw_response)

    # finally runs whether Gemini succeeds or fails. Therefore, the customer’s uploaded video is not left on the server.
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)