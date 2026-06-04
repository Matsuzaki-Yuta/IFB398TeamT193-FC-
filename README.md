# Travel Video Matcher

## Overview

Travel Video Matcher is a Flask-based web application that uses Google's Gemini AI to analyse travel videos and recommend matching Flight Centre travel packages.

Users upload a travel video through a web interface. Gemini analyses the video and extracts travel-related information such as destinations, landmarks, activities, and travel style. The extracted information is then matched against a curated travel package database stored in SQLite.

The application demonstrates how AI-powered travel inspiration can be connected directly to relevant travel products, supporting Flight Centre's goal of creating a more seamless digital-to-store customer journey.

---

## Features

* Upload travel videos through a web browser
* AI-powered video analysis using Gemini 2.5 Flash
* Automatic extraction of:

  * Destinations
  * Regions
  * Landmarks
  * Activities
  * Travel styles
* Matching against travel packages stored in SQLite
* Display package information including:

  * Price
  * Destination
  * Duration
  * Travel style tags
  * Matching reasons
* Simple and responsive web interface

---

## Technology Stack

### Backend

* Python 3.12
* Flask
* SQLite

### Frontend

* HTML
* CSS
* JavaScript

### AI

* Google Gemini API
* Gemini 2.5 Flash
* Google GenAI SDK

---

## Database

The application includes a SQLite database (`packages.db`) containing the travel package catalogue used for matching.

The database is included in the repository so the application can run immediately after cloning without requiring additional setup or seeding.

---

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd travel-video-matcher
```

### 2. Create Environment (Optional)

```bash
conda create -n flightcenter python=3.12
conda activate flightcenter
```

### 3. Install Dependencies (If not installed yet)

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (IMPORTANT!!)

Create a `.env` file in the project root:

```text
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

You can obtain a Gemini API key from Google AI Studio.

---

## Running the Application

Start the Flask server:

```bash
python app.py
```

Open the application in your browser:

```text
http://localhost:5000
```

---

## Application Workflow

1. User uploads a travel video.
2. Gemini analyses the uploaded video.
3. Gemini extracts travel information and returns structured JSON.
4. The application identifies destinations and travel styles.
5. Matching travel packages are retrieved from the SQLite database.
6. Matching packages are displayed to the user.

---

## Example Output

Gemini extracts information such as:

```json
{
  "detected_destinations": ["Shanghai", "Zhangjiajie"],
  "destination_region": "China",
  "travel_style": ["adventure", "cultural", "luxury"],
  "activities": ["hiking", "sightseeing"],
  "landmarks": ["Zhangjiajie National Forest Park"]
}
```

The application then recommends relevant travel packages from the package database.

---

## Security Notes

API keys are not stored in source code.

Create a local `.env` file and add your Gemini API key:

```text
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

The `.env` file is excluded from version control using `.gitignore`.
