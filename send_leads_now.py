"""
Send personalised emails to ALL leads in the sheet (regardless of status).
Updates the sheet after each send.
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from modules.sheets import (
    _get_service, _sheet_id, ensure_alia_columns, mark_email_sent,
    _build_lead
)
from modules.gmail_integration import send_to_lead

def is_valid_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

def get_all_leads_raw():
    ensure_alia_columns()
    svc = _get_service()
    result = svc.spreadsheets().values().get(
        spreadsheetId=_sheet_id(),
        range="Sheet1!A2:AN5000",
    ).execute()
    rows = result.get("values", [])
    leads = []
    for i, row in enumerate(rows):
        lead = _build_lead(row, i + 2)
        if lead:
            leads.append(lead)
    return leads

leads = get_all_leads_raw()

if not leads:
    print("No leads with Name + Email found in the sheet.")
    sys.exit(0)

print(f"Found {len(leads)} lead(s):\n")
for l in leads:
    valid = "✓" if is_valid_email(l['email']) else "✗ INVALID EMAIL"
    print(f"  {valid}  {l['name']} | {l['email']} | {l['company'] or '—'} | status={l['status'] or 'blank'}")

print()

sent = 0
skipped = 0
invalid = 0

for lead in leads:
    if lead["status"] in ("sent", "follow-up"):
        print(f"  ⏭  Skipping {lead['name']} — already marked '{lead['status']}'")
        skipped += 1
        continue

    if not is_valid_email(lead["email"]):
        print(f"\n  ✗  Skipping {lead['name']} — invalid email: '{lead['email']}'")
        print(f"     Fix column W in your sheet (must contain name@domain.com)")
        invalid += 1
        continue

    print(f"\n  ✉  Generating personalised email for {lead['name']} ({lead['email']})…")
    try:
        subject, body = send_to_lead(lead, sheet="Sheet1")
        mark_email_sent(lead["row"])
        print(f"  ✓  Sent!")
        print(f"     Subject : {subject}")
        print(f"\n     Preview :\n")
        for line in body.split("\n"):
            print(f"     {line}")
        sent += 1
    except Exception as e:
        print(f"  ✗  Failed for {lead['name']}: {e}")

print(f"\n{'='*50}")
print(f"  Sent: {sent} | Skipped: {skipped} | Invalid email: {invalid}")
print(f"{'='*50}")
