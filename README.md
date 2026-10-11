# Trip Bridge

Trip Bridge is the in-store Travel Planning Studio built by QUT IFB399 Team T193
with Flight Centre Travel Group (project: Phy-gital Journey).

A consultant enters a young customer's details, the customer uploads a travel
video, Google Gemini reads the destinations and travel style from it, the app
matches those against a catalogue of 194 public Flight Centre packages, and the
customer is emailed a priced quote with a PDF attached.

It is a prototype: it runs on one computer, uses a snapshot of package data
(prices are indicative) and has no booking or consultant sign-in.

## Journey

| Step | URL | Page |
| ---- | --- | ---- |
| 1 Welcome | `/landing` | Showreel and Try it now |
| 2 Customer | `/customer` | Name, email, age range, travellers, dates, budget |
| 3 Inspiration | `/match` | Upload an MP4 or MOV (up to 50 MB); Gemini analyses it |
| 4 Build package | `/packages` | Matched packages, best match first |
| 5 Final quote | `/finalquote` | Server-priced quote, emailed with a PDF |

"Start a new trip" clears the previous customer's details. Social media links
are not connected yet; the page says so if one is pasted.

## Run it

Needs Python 3.12 or newer.

**Windows:** run `install.bat` once, copy `.env.example` to `.env` and fill it in,
then run `start.bat`. It opens http://localhost:5000.

**macOS:**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add GEMINI_API_KEY and SMTP_PASSWORD
python app.py               # open http://localhost:5000
```

`packages.db` ships in the project root, so no database setup is needed.
To rebuild it from `flight_centre_packages.json`, run `python seed_db.py`.

## Configuration (.env)

`.env` is gitignored and must never be committed. `.env.example` lists every key.

| Key | Value |
| --- | ----- |
| `GEMINI_API_KEY` | Key from Google AI Studio. Needed for video analysis |
| `SMTP_*`, `MAIL_*` | Gmail account and 16-character App Password for sending quotes |
| `PACKAGES_DB_PATH` | Optional. Use a different package database |
| `FLASK_DEBUG` | Optional. `1` turns on debug mode; developer machines only |

Check the setup at http://localhost:5000/api/email/status. `"configured": true`
means email is ready. The password is never returned.

## Tests

```bash
python -m pytest -q
```

The tests need no keys and no network. GitHub Actions runs them on every push
and pull request to `main`.

## Project layout

```
app.py                     creates the Flask app
backend/routes/            page routes and the /api endpoints
backend/services/          Gemini, matching, quote pricing, PDF and email
backend/models/database.py opens packages.db
frontend/                  templates, CSS, JavaScript, images and showreel media
tests/                     automated tests
tools/preview_email.py     renders a sample quote email and PDF without sending
```

## API

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/health` | Process is up |
| POST | `/api/analyse` | Send a video to Gemini; returns destinations and styles |
| POST | `/api/packages/match` | Match an analysis against the catalogue |
| POST | `/api/quote` | Price a package. Sends nothing |
| POST | `/api/quote/send` | Price and email the quote with a PDF |
| GET | `/api/email/status` | Whether email is configured |

Errors share one shape: `{ "success": false, "error": { "code": "...", "message": "..." } }`.

## Known limits

* 83 packages have no destination and never match; a Bali video returns nothing.
  Japan, Vietnam and Europe footage works well for demonstrations.
* Matching uses destination and travel style only, not budget or dates.
* Quotes are emailed but not stored.
* No offline demo mode: analysis needs Gemini to be reachable.

Full documentation is in the handover pack: Start Here, Technical Documentation,
User Guide, and Test Plan and Results.

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
agent can watch it change, but that number is never used for the email. The
request carries only the package id, and every figure is rebuilt from the
database. Anything the browser sends is something a customer could edit first.

### Setup

1. Copy `.env.example` to `.env` (it is gitignored: never commit it).
2. Turn on 2-Step Verification for the sending Google account.
3. Create an App Password at https://myaccount.google.com/apppasswords and put
   the 16 characters in `SMTP_PASSWORD`. This is **not** the account password;
   Google rejects the account password over SMTP.
4. Install the dependencies again; `reportlab` is needed for the PDF:

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
`TOO_MANY_SENDS` (429), `EMAIL_FAILED` (502, or 500 if unexpected),
`EMAIL_NOT_CONFIGURED` (503).

### Previewing the email without sending anything

```bash
python tools/preview_email.py
```

Builds a sample quote from a real package in `packages.db`, writes the HTML,
plain text and PDF into `preview/`, and opens the HTML in your browser. No
SMTP settings and no App Password needed. Use this while working on the wording
or the layout.

It cannot show you how Gmail or Outlook will render it, because they apply their own
rules to email markup, so send one to yourself once the wording is settled.

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
skipped automatically for a server on localhost, and only for localhost. A
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
