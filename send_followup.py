"""
Send a fixed follow-up email to all no-reply leads in a given sheet tab.
Usage: python send_followup.py [sheet_name] [limit] [account]
  sheet_name : Sheet tab name (default: Sheet1)
  limit      : Max emails to send (default: 200)
  account    : OAuth account slot (default: "default")
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

STOP_FLAG = os.path.join(os.path.dirname(__file__), "stop.flag")

def check_stop():
    if os.path.exists(STOP_FLAG):
        os.remove(STOP_FLAG)
        print("\n  🛑  STOP flag detected — halting all email sends.")
        sys.exit(0)

SHEET_NAME = sys.argv[1] if len(sys.argv) > 1 else "Sheet1"
LIMIT      = int(sys.argv[2]) if len(sys.argv) > 2 else 200
ACCOUNT    = sys.argv[3] if len(sys.argv) > 3 else "default"

from modules.sheets import get_sent_leads, mark_follow_up
from modules.gmail_integration import send_email, get_sender_email
from modules.ai import ask_openai
import time

SEND_DELAY_SECONDS = 8

FOLLOWUP_TEMPLATE = """Hey {first_name},

Just following up on my last note.

I'm an AI Engineer who builds custom AI agents for businesses. One thing I've been building for clients recently is AI Voice Agents that handle inbound and outbound calls automatically. Appointment bookings, customer inquiries, sales calls, and follow-ups without any human involvement.

For example, I built a Voice AI system for a dental clinic that was drowning in manual phone calls. It now handles all scheduling and patient queries entirely on autopilot using Vapi and 11 Labs.

For a founder like you, this means your team stops answering repetitive calls and focuses on work that actually grows the business.

Worth a quick 15-min chat? Grab a time here: https://subhajitmandal.in/book

Best,
Subhajit Mandal
https://subhajitmandal.in"""


def is_valid_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def generate_followup_subject(lead: dict) -> str:
    first_name = lead["name"].split()[0]
    prompt = (
        f"Write a short reply-style subject line (max 6 words) for a follow-up cold email "
        f"to {first_name} at {lead['company'] or 'their company'}. "
        f"It should feel like a natural reply thread continuation, not a new email. "
        f"No spam words, no exclamation marks, no ALL CAPS. "
        f"Return ONLY the subject line, no quotes, no explanation."
    )
    return (ask_openai(prompt) or f"Re: AI for {lead['company'] or 'your team'}").strip().strip('"').strip("'")


leads = get_sent_leads(SHEET_NAME)[:LIMIT]

if not leads:
    print(f"No no-reply leads found in '{SHEET_NAME}'.")
    sys.exit(0)

print(f"Targeting sheet: '{SHEET_NAME}' — sending follow-ups to {len(leads)} no-reply leads — account: '{ACCOUNT}'")
print(f"\nLeads to follow up:\n")
for l in leads:
    valid = "✓" if is_valid_email(l['email']) else "✗ INVALID EMAIL"
    print(f"  {valid}  {l['name']} | {l['email']} | {l['company'] or 'N/A'}")

print()

sent = skipped = invalid = 0

for lead in leads:
    check_stop()
    if not is_valid_email(lead["email"]):
        print(f"\n  ✗  Skipping {lead['name']} — invalid email: '{lead['email']}'")
        invalid += 1
        continue

    first_name = lead["name"].split()[0]
    body = FOLLOWUP_TEMPLATE.format(first_name=first_name)

    print(f"\n  ✉  Sending follow-up to {lead['name']} ({lead['email']})...")
    try:
        subject = generate_followup_subject(lead)
        send_email(lead["email"], subject, body, delay=True, account=ACCOUNT)
        mark_follow_up(lead["row"], sheet_name=SHEET_NAME)
        print(f"  ✓  Sent!")
        print(f"     Subject : {subject}")
        sent += 1
    except Exception as e:
        print(f"  ✗  Failed for {lead['name']}: {e}")

print(f"\n{'='*50}")
print(f"  Sent: {sent} | Skipped: {skipped} | Invalid: {invalid}")
print(f"  Sheet: '{SHEET_NAME}' | Limit: {LIMIT}")
print(f"{'='*50}")
