"""Gmail integration — send personalised emails and detect replies."""

import base64
import os
import time
import uuid
import html as html_lib
import requests
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from modules.google_auth import get_credentials
from modules.ai import ask_openai

# Set TRACKING_BASE_URL in .env after deploying tracker/app.py
# e.g. TRACKING_BASE_URL=https://your-app.railway.app
TRACKING_BASE_URL: str | None = os.getenv("TRACKING_BASE_URL", "").strip() or None

# ── Business context injected into every email prompt ────────────────────────
BUSINESS_CONTEXT = """
Name        : Subhajit Mandal
Role        : AI Engineer & Python Developer
Website     : https://subhajitmandal.in
Book a call : https://subhajitmandal.in/book
Services    : Custom AI assistants, workflow automation, data pipelines,
              Python development, AI integration for businesses
""".strip()

# Delay between sends to avoid spam triggers (seconds)
SEND_DELAY_SECONDS = 8

_services:      dict[str, object] = {}
_sender_emails: dict[str, str]    = {}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_service(account: str = "default"):
    if account not in _services:
        creds = get_credentials(account)
        _services[account] = build("gmail", "v1", credentials=creds)
    return _services[account]


def get_sender_email(account: str = "default") -> str:
    """Auto-detect the authenticated Gmail address for the given account slot."""
    if account not in _sender_emails:
        profile = _get_service(account).users().getProfile(userId="me").execute()
        _sender_emails[account] = profile["emailAddress"]
    return _sender_emails[account]




# ── Email generation (GPT-4o) ─────────────────────────────────────────────────

def generate_subject(lead: dict) -> str:
    first_name = lead["name"].split()[0]
    prompt = (
        f"Write a short, natural cold-email subject line (max 8 words) "
        f"for reaching out to {first_name} at {lead['company'] or 'their company'}. "
        f"Context: Subhajit Mandal is an AI Engineer offering AI automation services. "
        f"Rules: no spam words (free, guaranteed, limited offer, act now, urgent, "
        f"discount, winner, congratulations), no ALL CAPS, no exclamation marks, "
        f"no generic phrases like 'Quick question' or 'Following up'. "
        f"Make it specific to their industry or role. "
        f"Return ONLY the subject line — no quotes, no explanation."
    )
    return (ask_openai(prompt) or "").strip().strip('"').strip("'").rstrip("!")


def generate_email_body(lead: dict) -> str:
    first_name = lead["name"].split()[0]
    notes_line = f"- Context    : {lead['notes']}" if lead.get("notes") else ""
    prompt = f"""
You are writing a personalised cold outreach email on behalf of Subhajit Mandal.

=== SENDER ===
{BUSINESS_CONTEXT}

=== RECIPIENT ===
- Name    : {lead['name']}
- Company : {lead['company'] or 'their company'}
{notes_line}

=== WRITING RULES (critical for inbox delivery) ===
1. Address them by first name ({first_name}) in the opening — no "Dear", no "Hi there".
2. Mention something specific about their company or role to show it's not a mass email.
3. Suggest 1 concrete way AI could help them based on their industry/role.
4. End with this exact call-to-action line (do not change the URL):
   "If you're open to it, you can grab a time here: https://subhajitmandal.in/book"
5. Sign off exactly like this (preserve both links):
   Best,
   Subhajit Mandal
   https://subhajitmandal.in

=== AVOID (spam triggers) ===
- No exclamation marks
- No words: free, guaranteed, limited time, act now, urgent, discount, offer, deal,
  investment, revenue, profit, make money, opportunity, solution, leverage
- No ALL CAPS words
- No phrases like "I hope this email finds you well"
- No bullet points or numbered lists in the email
- Keep it under 120 words — short emails have better inbox rates
- Write like a human, not a marketing email

Return ONLY the email body. No subject line.
""".strip()
    return ask_openai(prompt).strip()


# ── Sending ───────────────────────────────────────────────────────────────────

def _body_to_html(plain_body: str, tracking_uid: str | None = None) -> str:
    """Convert plain text body to minimal HTML + optional tracking pixel."""
    escaped = html_lib.escape(plain_body)
    paragraphs = "".join(
        f"<p style='margin:0 0 10px'>{line}</p>" if line.strip() else "<br>"
        for line in escaped.split("\n")
    )
    pixel = ""
    if tracking_uid and TRACKING_BASE_URL:
        pixel = (
            f'<img src="{TRACKING_BASE_URL}/pixel/{tracking_uid}.gif" '
            f'width="1" height="1" style="display:none" alt="">'
        )
    return (
        '<html><body style="font-family:Arial,sans-serif;font-size:14px;'
        f'color:#222;line-height:1.6">{paragraphs}{pixel}</body></html>'
    )


def _register_send(uid: str, lead: dict, sheet: str = "") -> None:
    """Tell the tracker server about this send so it can map uid → lead."""
    if not TRACKING_BASE_URL:
        return
    try:
        requests.post(
            f"{TRACKING_BASE_URL}/register",
            json={
                "uid":     uid,
                "email":   lead["email"],
                "name":    lead["name"],
                "company": lead.get("company", ""),
                "sheet":   sheet,
                "row_num": lead.get("row", 0),
            },
            timeout=5,
        )
    except Exception:
        pass  # tracker is optional — never block a send


def send_email(
    to_email: str,
    subject: str,
    body: str,
    delay: bool = True,
    tracking_uid: str | None = None,
    account: str = "default",
) -> None:
    """
    Send email. If TRACKING_BASE_URL is set, sends multipart/alternative with
    a tracking pixel in the HTML part. Otherwise sends plain-text only.
    """
    sender  = get_sender_email(account)
    msg_id  = f"<{uuid.uuid4()}@subhajitmandal.in>"
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    if TRACKING_BASE_URL and tracking_uid:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(_body_to_html(body, tracking_uid), "html", "utf-8"))
    else:
        msg = MIMEText(body, "plain", "utf-8")

    msg["To"]         = to_email
    msg["From"]       = sender
    msg["Reply-To"]   = sender
    msg["Subject"]    = subject
    msg["Message-ID"] = msg_id
    msg["Date"]       = now_rfc

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    _get_service(account).users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()

    if delay:
        time.sleep(SEND_DELAY_SECONDS)


def send_to_lead(
    lead: dict,
    delay: bool = True,
    sheet: str = "",
    account: str = "default",
) -> tuple[str, str]:
    """
    Generate + send a personalised email to a single lead.
    Returns (subject, body) so the caller can log or confirm.
    """
    subject = generate_subject(lead)
    body    = generate_email_body(lead)

    tracking_uid = str(uuid.uuid4()) if TRACKING_BASE_URL else None
    send_email(lead["email"], subject, body, delay=delay, tracking_uid=tracking_uid, account=account)

    if tracking_uid:
        _register_send(tracking_uid, lead, sheet=sheet)

    return subject, body


# ── Reply detection ───────────────────────────────────────────────────────────

def check_reply(email_address: str) -> bool:
    """
    Return True if the inbox contains any message FROM email_address.
    """
    svc      = _get_service()
    response = svc.users().messages().list(
        userId="me",
        q=f"from:{email_address}",
        maxResults=1,
    ).execute()
    return bool(response.get("messages"))


def check_all_replies(sent_leads: list[dict]) -> dict[str, bool]:
    """Check every sent lead for replies. Returns {email: replied_bool}."""
    return {lead["email"]: check_reply(lead["email"]) for lead in sent_leads}
