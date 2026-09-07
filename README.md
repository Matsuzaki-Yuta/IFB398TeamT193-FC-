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

You can obtain a Gemini API key from Google AI Studio. https://aistudio.google.com/app/api-keys?utm_source=chatgpt.com&project=gen-lang-client-0677881876 

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

The same applies to the Gmail App Password used for sending quotes. It lives in
`.env` beside the Gemini key, is never written to a log line, and is never
returned by any endpoint, including `/api/email/status`.

---

## Emailing the Final Quote

The Final Quote step sends the customer their quote by email, as a formatted
message with a one-page PDF attached.

### How it works

```
Final quote page                Flask backend                       Gmail
----------------                -------------                       -----
Send quote  ──POST──▶  /api/quote/send
                        1. validate the request
                        2. re-read the package from packages.db
                        3. rebuild every price server-side
                        4. render the email (HTML + plain text)
                        5. build the PDF                 ──SMTP──▶  customer
◀── "check your inbox" ── reference, total, valid-until
```

Step 3 is the important one. The page adds up the total in JavaScript so the
agent can watch it change, but that number is never used for the email — the
request carries only the package id, and every figure is rebuilt from the
database. Anything the browser sends is something a customer could edit first.

### Setup

1. Copy `.env.example` to `.env` (it is gitignored — never commit it).
2. Turn on 2-Step Verification for the sending Google account.
3. Create an App Password at https://myaccount.google.com/apppasswords and put
   the 16 characters in `SMTP_PASSWORD`. This is **not** the account password;
   Google rejects the account password over SMTP.
4. Install the dependencies again — `reportlab` is new:

```bash
pip install -r requirements.txt
```

5. Check the setup without sending anything:

```text
http://localhost:5000/api/email/status
```

`"configured": true` means the `.env` file was found and read. It never returns
the password.

### Endpoints

| Method | Path                | What it does                                    |
| ------ | ------------------- | ----------------------------------------------- |
| POST   | `/api/quote`        | Builds the quote and returns it. Sends nothing.  |
| POST   | `/api/quote/send`   | Builds the quote and emails it to the customer.  |
| GET    | `/api/email/status` | Reports whether email is configured.             |

Request body for both POST endpoints:

```json
{
  "customer": { "name": "Jordan Lee", "email": "jordan@example.com", "travellers": 2 },
  "quote": { "departure": "2026-12-01", "valid_days": 14, "message": "Optional note." },
  "selected_package_id": "product-24766397"
}
```

Error codes the frontend handles: `MISSING_EMAIL`, `INVALID_EMAIL`,
`INVALID_NUMBER`, `INVALID_DATE`, `MISSING_PACKAGE`, `UNKNOWN_PACKAGE` (400),
`TOO_MANY_SENDS` (429), `EMAIL_FAILED` (502), `EMAIL_NOT_CONFIGURED` (503).

### Previewing the email without sending anything

```bash
python tools/preview_email.py
```

Builds a sample quote from a real package in `packages.db`, writes the HTML,
plain text and PDF into `preview/`, and opens the HTML in your browser. No
SMTP settings and no App Password needed. Use this while working on the wording
or the layout.

It cannot show you how Gmail or Outlook will render it — they apply their own
rules to email markup — so send one to yourself once the wording is settled.

### Testing without emailing anyone

Run a throwaway SMTP server in a second terminal:

```bash
pip install aiosmtpd
python -m aiosmtpd -n -l localhost:1025
```

Then point `.env` at it:

```text
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=test@example.com
SMTP_PASSWORD=unused
MAIL_FROM_EMAIL=test@example.com
```

The message prints to that terminal and nothing leaves the machine. STARTTLS is
skipped automatically for a server on localhost, and only for localhost — a
remote host that does not offer STARTTLS is refused rather than having the
password sent in the clear.

The automated tests need none of this:

```bash
python -m pytest tests -q
```

### Sending limits

Gmail allows roughly 500 recipients a day from a personal account. The app also
throttles itself to 5 sends per device per 10 minutes, in
`backend/routes/api_routes.py`. That history is in memory, so it resets when
Flask restarts.

### Known limitations

* The send is synchronous: the request waits for Gmail, up to `SMTP_TIMEOUT`
  seconds. Fine for a kiosk, worth moving to a background thread for production.
* Quotes are emailed but not stored, so an agent cannot resend one later.
* Gmail rewrites the `From` header to the account that signed in, so the quote
  cannot appear to come from a `@flightcentre.com` address without Flight Centre
  providing a relay and a verified domain.
* Free-tier email from an unverified domain can land in spam. Check the spam
  folder before assuming the send failed, and rehearse this before the demo.
