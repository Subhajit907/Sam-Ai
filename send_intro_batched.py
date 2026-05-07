"""
Send intro emails in batches to pending leads (no email sent yet).
Usage: python send_intro_batched.py [sheet_name] [account]
  sheet_name : Sheet tab name (default: Sheet2)
  account    : OAuth account slot (default: account3)

Batch config: 20 emails -> wait 20 min -> repeat (5 batches = 100 total)
"""
import os, sys, re, time, random
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

SHEET_NAME   = sys.argv[1] if len(sys.argv) > 1 else "Sheet2"
ACCOUNT      = sys.argv[2] if len(sys.argv) > 2 else "account3"
TOTAL_LIMIT  = int(sys.argv[3]) if len(sys.argv) > 3 else 100
BATCH_SIZE   = 20
WAIT_MINUTES = 5
STOP_FLAG    = os.path.join(os.path.dirname(__file__), "stop.flag")

from modules.sheets import get_pending_leads, mark_email_sent
from modules.gmail_integration import send_email
from modules.ai import ask_openai

SEND_DELAY_SECONDS = 10

INTRO_TEMPLATE = """Hey {first_name},

I build custom AI systems for businesses — things like automating workflows, CRM data pipelines, and intelligent agents that handle repetitive tasks your team shouldn't be doing manually.

I've worked with founders across marketing, tech, and real estate to cut hours of manual work down to minutes using AI.

If that sounds useful, I'd love to show you what's possible in 15 mins: https://subhajitmandal.in/book

Best,
Subhajit Mandal
https://subhajitmandal.in"""


def is_valid_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def check_stop():
    if os.path.exists(STOP_FLAG):
        os.remove(STOP_FLAG)
        print("\n  STOP flag detected — halting all email sends.")
        sys.exit(0)


def generate_subject(lead: dict) -> str:
    first_name = lead["name"].split()[0]
    prompt = (
        f"Write a short, natural cold-email subject line (max 8 words) "
        f"for reaching out to {first_name} at {lead['company'] or 'their company'}. "
        f"Context: Subhajit Mandal is an AI Engineer offering custom AI agents and automation. "
        f"Rules: no spam words (free, guaranteed, limited offer, act now, urgent, discount), "
        f"no ALL CAPS, no exclamation marks, no generic phrases like 'Quick question'. "
        f"Make it specific to their industry or role. "
        f"Return ONLY the subject line, no quotes, no explanation."
    )
    return (ask_openai(prompt) or f"AI automation for {lead['company'] or 'your business'}").strip().strip('"').strip("'")


# ── Load pending leads ────────────────────────────────────────────────────────

all_leads = get_pending_leads(SHEET_NAME)
leads = [l for l in all_leads if is_valid_email(l["email"])][:TOTAL_LIMIT]

if not leads:
    print(f"No pending leads found in '{SHEET_NAME}'.")
    sys.exit(0)

total = len(leads)
batch_count = -(-total // BATCH_SIZE)  # ceiling division
print(f"\nAccount  : {ACCOUNT}")
print(f"Sheet    : {SHEET_NAME}")
print(f"Total    : {total} leads")
print(f"Batches  : {batch_count} x up to {BATCH_SIZE} emails with {WAIT_MINUTES} min wait\n")

sent = 0

for batch_num in range(batch_count):
    batch = leads[batch_num * BATCH_SIZE : (batch_num + 1) * BATCH_SIZE]
    if not batch:
        break

    print(f"{'='*50}")
    print(f"  Batch {batch_num + 1}/{batch_count} — {len(batch)} emails")
    print(f"{'='*50}\n")

    for lead in batch:
        check_stop()

        first_name = lead["name"].split()[0]
        body = INTRO_TEMPLATE.format(first_name=first_name)

        print(f"  Sending to {lead['name']} ({lead['email']})...")
        try:
            subject = generate_subject(lead)
            send_email(lead["email"], subject, body, delay=False, account=ACCOUNT)
            time.sleep(random.randint(8, 20))
            mark_email_sent(lead["row"], sheet_name=SHEET_NAME)
            print(f"  Sent — Subject: {subject}")
            sent += 1
        except Exception as e:
            print(f"  Failed for {lead['name']}: {e}")

    print(f"\n  Batch {batch_num + 1} done. Sent so far: {sent}/{total}")

    if batch_num < batch_count - 1:
        check_stop()
        print(f"\n  Waiting {WAIT_MINUTES} minutes before next batch...\n")
        for remaining in range(WAIT_MINUTES * 60, 0, -60):
            check_stop()
            print(f"  {remaining // 60} min remaining...")
            time.sleep(60)

print(f"\n{'='*50}")
print(f"  All done! Total sent: {sent}")
print(f"  Sheet: '{SHEET_NAME}' | Account: '{ACCOUNT}'")
print(f"{'='*50}")
