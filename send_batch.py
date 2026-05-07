"""
Send personalised emails to the first N pending leads in a given sheet tab.
Usage: python send_batch.py [sheet_name] [limit] [account]
  sheet_name : Sheet tab name (default: Sheet2)
  limit      : Max emails to send (default: 200)
  account    : OAuth account slot (default: "default", use "account2" for 2nd Gmail)
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

SHEET_NAME = sys.argv[1] if len(sys.argv) > 1 else "Sheet2"
LIMIT      = int(sys.argv[2]) if len(sys.argv) > 2 else 200
ACCOUNT    = sys.argv[3] if len(sys.argv) > 3 else "default"

from modules.sheets import (
    _get_service, _sheet_id, ensure_alia_columns,
    mark_email_sent, _build_lead
)
from modules.gmail_integration import send_to_lead

def is_valid_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

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
        if lead and lead["status"] not in ("sent", "follow-up"):
            leads.append(lead)
    return leads

leads = get_pending_leads_raw(SHEET_NAME, LIMIT)

if not leads:
    print(f"No pending leads found in '{SHEET_NAME}'.")
    sys.exit(0)

print(f"Targeting sheet: '{SHEET_NAME}' — sending to first {LIMIT} pending leads — account: '{ACCOUNT}'")
print(f"Found {len(leads)} lead(s) to process:\n")
for l in leads:
    valid = "✓" if is_valid_email(l['email']) else "✗ INVALID EMAIL"
    print(f"  {valid}  {l['name']} | {l['email']} | {l['company'] or '—'}")

print()

sent = skipped = invalid = 0

for lead in leads:
    if not is_valid_email(lead["email"]):
        print(f"\n  ✗  Skipping {lead['name']} — invalid email: '{lead['email']}'")
        invalid += 1
        continue

    print(f"\n  ✉  Generating email for {lead['name']} ({lead['email']})…")
    try:
        subject, body = send_to_lead(lead, sheet=SHEET_NAME, account=ACCOUNT)
        mark_email_sent(lead["row"], sheet_name=SHEET_NAME)
        print(f"  ✓  Sent!")
        print(f"     Subject : {subject}")
        print(f"\n     Preview :\n")
        for line in body.split("\n"):
            print(f"     {line}")
        sent += 1
    except Exception as e:
        print(f"  ✗  Failed for {lead['name']}: {e}")

print(f"\n{'='*50}")
print(f"  Sent: {sent} | Skipped: {skipped} | Invalid: {invalid}")
print(f"  Sheet: '{SHEET_NAME}' | Limit: {LIMIT}")
print(f"{'='*50}")
