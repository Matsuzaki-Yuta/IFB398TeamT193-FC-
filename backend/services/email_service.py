"""
The SMTP transport. Nothing in here knows what a quote is.

Every setting comes from the .env file, so switching from a Gmail account to a
Flight Centre relay later is a configuration change and not a code change.
Written against smtplib from the standard library — no extra dependency.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr


class EmailConfigurationError(Exception):
    """The .env file is missing or incomplete. The operator can fix this."""


class EmailSendError(Exception):
    """The relay refused or could not be reached. The operator cannot fix this."""


def _is_local(host):
    """True for a mail server running on this machine."""
    return host.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0")


def load_settings():
    """
    Reads the SMTP settings from the environment.

    load_dotenv() has already run in create_app(), so a .env file in the project
    root is enough. Raises EmailConfigurationError listing every missing key at
    once, rather than failing on the first one and hiding the rest.
    """
    settings = {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": os.getenv("SMTP_PORT", "587").strip(),
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_email": os.getenv("MAIL_FROM_EMAIL", "").strip(),
        "from_name": os.getenv("MAIL_FROM_NAME", "Flight Centre Trip Bridge").strip(),
        "reply_to": os.getenv("MAIL_REPLY_TO", "").strip(),
        "timeout": os.getenv("SMTP_TIMEOUT", "20").strip(),
        # starttls (the default, and what port 587 expects), ssl (port 465), or
        # none. "none" exists only so the team can test against a local debug
        # SMTP server, which speaks no TLS at all; send_message refuses it for
        # any host that is not on this machine.
        "security": os.getenv("SMTP_SECURITY", "").strip().lower(),
    }

    missing = [
        key.upper() for key in ("host", "username", "password")
        if not settings[key]
    ]
    if not settings["from_email"]:
        missing.append("MAIL_FROM_EMAIL")
    if missing:
        raise EmailConfigurationError(
            "Email is not configured. Add these to your .env file: "
            + ", ".join("SMTP_" + key if key in ("HOST", "USERNAME", "PASSWORD")
                        else key for key in missing)
        )

    try:
        settings["port"] = int(settings["port"])
        settings["timeout"] = int(settings["timeout"])
    except ValueError:
        raise EmailConfigurationError("SMTP_PORT and SMTP_TIMEOUT must be numbers.")

    if not settings["security"]:
        settings["security"] = "ssl" if settings["port"] == 465 else "starttls"
    if settings["security"] not in ("starttls", "ssl", "none"):
        raise EmailConfigurationError(
            "SMTP_SECURITY must be starttls, ssl or none."
        )

    # Gmail rewrites the From header to the account that authenticated, so an
    # address that is not the SMTP username is silently replaced and the quote
    # appears to come from somewhere the customer does not recognise. Catching
    # it here turns a confusing demo into a clear setup error.
    if "@" in settings["username"]:
        authenticated = settings["username"].lower()
        declared = parseaddr(settings["from_email"])[1].lower()
        if declared and declared != authenticated:
            settings["from_mismatch"] = (authenticated, declared)

    return settings


def build_message(to_email, subject, text_body, html_body, attachments=None,
                  settings=None):
    """
    Assembles the message.

    Sends both a plain-text and an HTML version. Every mail client can show one
    of the two, and a message with no text part is a well-known spam signal.

    Parameters:
        attachments: list of (filename, mime_type, bytes) tuples, or None.
    """
    settings = settings or load_settings()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings["from_name"], settings["from_email"]))
    message["To"] = to_email
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    if settings.get("reply_to"):
        message["Reply-To"] = settings["reply_to"]

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    for filename, mime_type, content in (attachments or []):
        main_type, _, sub_type = mime_type.partition("/")
        message.add_attachment(
            content, maintype=main_type, subtype=sub_type or "octet-stream",
            filename=filename,
        )

    return message


def send_message(message, settings=None):
    """
    Opens the connection, authenticates and sends.

    SMTP_SECURITY decides how the connection is protected, and defaults from the
    port: 465 means implicit TLS (encrypted from the first byte), anything else
    means STARTTLS, which is what port 587 expects. Gmail accepts either.

    If STARTTLS was expected but the server does not offer it, the send is
    refused rather than falling back to plain text — otherwise a typo in
    SMTP_HOST would put the app password on the wire in the clear. The single
    exception is a server on this machine, which is how the team tests offline.

    Raises EmailConfigurationError for problems the operator can fix — a wrong
    app password, most commonly — and EmailSendError for everything else.
    """
    settings = settings or load_settings()
    context = ssl.create_default_context()
    security = settings["security"]
    host = settings["host"]

    # SMTP_SECURITY=none exists for the local debug server and nothing else.
    # Allowing it against a real host would mean sending the app password
    # unencrypted across the network.
    if security == "none" and not _is_local(host):
        raise EmailConfigurationError(
            f"SMTP_SECURITY=none is only allowed for a mail server on this "
            f"machine, and {host} is not one. Use starttls (port 587) or ssl "
            f"(port 465)."
        )

    try:
        if security == "ssl":
            server = smtplib.SMTP_SSL(
                host, settings["port"],
                timeout=settings["timeout"], context=context,
            )
        else:
            server = smtplib.SMTP(host, settings["port"], timeout=settings["timeout"])

        with server:
            server.ehlo()

            if security == "starttls":
                if server.has_extn("starttls"):
                    server.starttls(context=context)
                    server.ehlo()
                elif _is_local(host):
                    # A local debug SMTP server (python -m aiosmtpd) speaks no
                    # TLS. Nothing leaves the machine, so this is safe and it is
                    # what makes offline testing possible.
                    pass
                else:
                    raise EmailConfigurationError(
                        f"{host} does not offer STARTTLS, so the password would "
                        "be sent unencrypted. Check SMTP_HOST and SMTP_PORT — "
                        "Gmail uses smtp.gmail.com on port 587."
                    )

            # A local debug server usually has no accounts at all, so signing in
            # would fail against a server that never asked for a sign-in.
            if server.has_extn("auth") or not _is_local(host):
                server.login(settings["username"], settings["password"])

            server.send_message(message)

    except smtplib.SMTPAuthenticationError:
        # Deliberately says nothing about the credentials themselves. The
        # password must never reach a log file or an HTTP response.
        raise EmailConfigurationError(
            "The mail server rejected the sign-in. Check SMTP_USERNAME and "
            "SMTP_PASSWORD in your .env file — Gmail needs a 16-character app "
            "password, not your normal account password."
        )
    except smtplib.SMTPRecipientsRefused:
        raise EmailSendError("The mail server would not accept that address.")
    except (smtplib.SMTPException, OSError) as error:
        raise EmailSendError(f"The mail server could not be reached: {error}")


def send_email(to_email, subject, text_body, html_body, attachments=None):
    """Convenience wrapper: build and send in one call. Returns the Message-ID."""
    settings = load_settings()
    message = build_message(
        to_email, subject, text_body, html_body, attachments, settings
    )
    send_message(message, settings)
    return message["Message-ID"]
