"""
Send follow-up emails in batches with a wait between each batch.
Usage: python send_followup_batched.py [sheet_name] [account]
  sheet_name : Sheet tab name (default: Sheet2)
  account    : OAuth account slot (default: account2)

Batch config: 20 emails → wait 20 min → 20 emails → ... (5 batches = 100 total)
"""
import os, sys, re, time
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

SHEET_NAME   = sys.argv[1] if len(sys.argv) > 1 else "Sheet2"
ACCOUNT      = sys.argv[2] if len(sys.argv) > 2 else "account2"
BATCH_SIZE   = 20
BATCH_COUNT  = 5
WAIT_MINUTES = 20
STOP_FLAG    = os.path.join(os.path.dirname(__file__), "stop.flag")

from modules.sheets import get_sent_leads, mark_follow_up
from modules.gmail_integration import send_email
from modules.ai import ask_openai

SEND_DELAY_SECONDS = 8

# ── 5 email variations ────────────────────────────────────────────────────────

VARIATIONS = [
"""Hey {first_name},

Just following up on my last note.

I'm an AI Engineer who builds custom AI agents for businesses. One thing I've been building for clients recently is AI Voice Agents that handle inbound and outbound calls automatically. Appointment bookings, customer inquiries, sales calls, and follow-ups without any human involvement.

For example, I built a Voice AI system for a dental clinic that was drowning in manual phone calls. It now handles all scheduling and patient queries entirely on autopilot using OpenAI Whisper and 11 Labs.

For a founder like you, this means your team stops answering repetitive calls and focuses on work that actually grows the business.

Worth a quick 15-min chat? Grab a time here: https://subhajitmandal.in/book

Best,
Subhajit Mandal
https://subhajitmandal.in""",

"""Hey {first_name},

Wanted to bump this up in case it got buried.

I build custom AI agents for businesses. One system I've been deploying for clients is an AI Voice Agent that picks up inbound calls and makes outbound ones automatically. Scheduling, customer questions, sales follow-ups — all handled without a single human touch.

I recently built one for a dental clinic using OpenAI Whisper and 11 Labs. Their staff no longer handles appointment calls at all.

If your team is spending time on repetitive calls, this could free them up completely.

Happy to show you how it works in 15 mins: https://subhajitmandal.in/book

Best,
Subhajit Mandal
https://subhajitmandal.in""",

"""Hey {first_name},

Just circling back on my previous message.

I'm an AI Engineer specializing in custom AI agents for businesses. Lately I've been building AI Voice Agents that fully automate phone communication for companies. Inbound calls, outbound follow-ups, bookings and inquiries — running 24/7 without staff involvement.

Built one recently for a dental clinic using OpenAI Whisper and 11 Labs. It replaced their entire manual call handling process.

For a business like yours, this kind of system can save hours every week and scale without hiring.

Open to a quick 15-min chat? Here's my calendar: https://subhajitmandal.in/book

Best,
Subhajit Mandal
https://subhajitmandal.in""",

"""Hey {first_name},

Following up in case my last email slipped through the cracks.

I build AI systems for businesses and one area I've been focused on is Voice AI. I create agents that handle both inbound and outbound calls automatically — no staff needed for bookings, inquiries, or follow-ups.

A recent example: a dental clinic using OpenAI Whisper and 11 Labs that now runs its entire appointment and patient query process on autopilot.

This kind of system works especially well for teams spending too much time on repetitive phone work.

Worth 15 minutes? Grab a slot here: https://subhajitmandal.in/book

Best,
Subhajit Mandal
https://subhajitmandal.in""",

"""Hey {first_name},

Just reaching back out one more time.

I'm an AI Engineer who builds custom voice and automation systems for businesses. One thing that's been getting a lot of traction with my clients is AI Voice Agents — systems that handle calls, bookings, and follow-ups around the clock without any manual effort.

I recently deployed one for a dental clinic powered by OpenAI Whisper and 11 Labs. It completely eliminated their manual call handling.

If phone communication is eating into your team's time, this is exactly the kind of thing I build.

Would love to show you a quick demo: https://subhajitmandal.in/book

Best,
Subhajit Mandal
https://subhajitmandal.in""",
]


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
        f"Write a short reply-style subject line (max 6 words) for a follow-up cold email "
        f"to {first_name} at {lead['company'] or 'their company'}. "
        f"It should feel like a natural reply thread continuation, not a new email. "
        f"No spam words, no exclamation marks, no ALL CAPS. "
        f"Return ONLY the subject line, no quotes, no explanation."
    )
    return (ask_openai(prompt) or f"Re: AI for {lead['company'] or 'your team'}").strip().strip('"').strip("'")


# ── Load leads ────────────────────────────────────────────────────────────────

all_leads = get_sent_leads(SHEET_NAME)
leads = [l for l in all_leads if is_valid_email(l["email"])][:BATCH_SIZE * BATCH_COUNT]

if not leads:
    print(f"No no-reply leads found in '{SHEET_NAME}'.")
    sys.exit(0)

total = len(leads)
print(f"\nAccount  : {ACCOUNT}")
print(f"Sheet    : {SHEET_NAME}")
print(f"Total    : {total} leads")
print(f"Batches  : {BATCH_COUNT} x {BATCH_SIZE} emails with {WAIT_MINUTES} min wait\n")

sent = 0

for batch_num in range(BATCH_COUNT):
    batch = leads[batch_num * BATCH_SIZE : (batch_num + 1) * BATCH_SIZE]
    if not batch:
        break

    template = VARIATIONS[batch_num]
    print(f"{'='*50}")
    print(f"  Batch {batch_num + 1}/{BATCH_COUNT} — {len(batch)} emails (Variation {batch_num + 1})")
    print(f"{'='*50}\n")

    for lead in batch:
        check_stop()

        first_name = lead["name"].split()[0]
        body = template.format(first_name=first_name)

        print(f"  Sending to {lead['name']} ({lead['email']})...")
        try:
            subject = generate_subject(lead)
            send_email(lead["email"], subject, body, delay=True, account=ACCOUNT)
            mark_follow_up(lead["row"], sheet_name=SHEET_NAME)
            print(f"  Sent — Subject: {subject}")
            sent += 1
        except Exception as e:
            print(f"  Failed for {lead['name']}: {e}")

    print(f"\n  Batch {batch_num + 1} done. Sent so far: {sent}/{total}")

    if batch_num < BATCH_COUNT - 1:
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
