"""
Send the fixed intro email to pending leads.
Status is set to 'intro' so the sales email can follow later.
Usage: python send_intro.py [sheet_name] [limit] [account]
  Defaults: Sheet2, 450, default
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

SHEET_NAME = sys.argv[1] if len(sys.argv) > 1 else "Sheet2"
LIMIT      = int(sys.argv[2]) if len(sys.argv) > 2 else 450
ACCOUNT    = sys.argv[3] if len(sys.argv) > 3 else "default"

from modules.sheets import (
    _get_service, _sheet_id, ensure_alia_columns,
    mark_intro_sent, _build_lead
)
from modules.gmail_integration import send_email, get_sender_email, TRACKING_BASE_URL, _register_send

import re as _re, uuid, time

SUBJECT = "A quick introduction from me"

INTRO_BODY = """{first_name},

I'm Subhajit Mandal, an AI Engineer and Python Developer focused on helping businesses improve efficiency and streamline operations. I build custom AI assistants, automate workflows, and develop data pipelines. One recent project was an AI Voice Agent that handled repetitive calls automatically — no human needed — saving the client significant time and overhead.

If you ever want to explore what that could look like for your business, my calendar is open: https://subhajitmandal.in/book

Subhajit Mandal
https://subhajitmandal.in"""


def is_valid_email(email):
    return bool(_re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def get_pending_leads_raw(sheet_name, limit):
    ensure_alia_columns(sheet_name)
    svc = _get_service()
    result = svc.spreadsheets().values().get(
        spreadsheetId=_sheet_id(),
        range=f"{sheet_name}!A2:AN10000",
    ).execute()
    rows  = result.get("values", [])
    leads = []
    for i, row in enumerate(rows):
        if len(leads) >= limit:
            break
        lead = _build_lead(row, i + 2)
        if lead and lead["status"] not in ("sent", "follow-up", "intro"):
            leads.append(lead)
    return leads


leads = get_pending_leads_raw(SHEET_NAME, LIMIT)

if not leads:
    print(f"No pending leads found in '{SHEET_NAME}'.")
    sys.exit(0)

print(f"Intro email | Sheet: '{SHEET_NAME}' | Limit: {LIMIT} | Account: '{ACCOUNT}'")
print(f"Found {len(leads)} lead(s) to process\n")

sent = invalid = 0

for lead in leads:
    if not is_valid_email(lead["email"]):
        print(f"  ✗  Skipping {lead['name']} — invalid email")
        invalid += 1
        continue

    first_name = lead["name"].split()[0]
    body = INTRO_BODY.replace("{first_name}", first_name)

    print(f"  ✉  {lead['name']} ({lead['email']})…", end=" ", flush=True)
    try:
        tracking_uid = str(uuid.uuid4()) if TRACKING_BASE_URL else None
        send_email(lead["email"], SUBJECT, body, delay=True,
                   tracking_uid=tracking_uid, account=ACCOUNT)
        if tracking_uid:
            _register_send(tracking_uid, lead, sheet=SHEET_NAME)
        mark_intro_sent(lead["row"], sheet_name=SHEET_NAME)
        print("✓ Sent!")
        sent += 1
    except Exception as e:
        print(f"✗ Failed: {e}")

print(f"\n{'='*50}")
print(f"  Sent: {sent} | Invalid: {invalid}")
print(f"  Sheet: '{SHEET_NAME}' | Account: '{ACCOUNT}'")
print(f"{'='*50}")
