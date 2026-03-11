"""
Quick integration test — runs WITHOUT the voice/GUI stack.
Tests: Google OAuth → Sheets read → Sheets column setup → Gmail sender detection.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

def separator(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)

# ── 1. OAuth ──────────────────────────────────────────────
separator("1. Google OAuth")
try:
    from modules.google_auth import get_credentials
    creds = get_credentials()
    print(f"  ✓  Credentials valid: {creds.valid}")
    print(f"  ✓  Token expiry     : {creds.expiry}")
except Exception as e:
    print(f"  ✗  OAuth failed: {e}")
    sys.exit(1)

# ── 2. Sheets — ensure Alia columns exist ────────────────
separator("2. Google Sheets — column setup")
try:
    from modules.sheets import ensure_alia_columns, get_all_leads_summary
    ensure_alia_columns()
    print("  ✓  Alia columns (E-H) verified / created")
except Exception as e:
    print(f"  ✗  Sheets column setup failed: {e}")

# ── 3. Sheets — read leads ───────────────────────────────
separator("3. Google Sheets — read leads")
try:
    from modules.sheets import get_pending_leads
    leads = get_pending_leads()
    print(f"  ✓  Pending leads found: {len(leads)}")
    for l in leads[:5]:
        print(f"       • {l['name']} | {l['email']} | {l['company'] or '—'}")
    if len(leads) > 5:
        print(f"       … and {len(leads)-5} more")
except Exception as e:
    print(f"  ✗  Sheets read failed: {e}")

# ── 4. Sheets — lead summary ─────────────────────────────
separator("4. Google Sheets — summary")
try:
    s = get_all_leads_summary()
    print(f"  ✓  Total   : {s['total']}")
    print(f"     Pending : {s['pending']}")
    print(f"     Sent    : {s['sent']}")
    print(f"     Replied : {s['replied']}")
    print(f"     No reply: {s['no reply']}")
except Exception as e:
    print(f"  ✗  Summary failed: {e}")

# ── 5. Gmail — detect sender address ────────────────────
separator("5. Gmail — sender email")
try:
    from modules.gmail_integration import get_sender_email
    sender = get_sender_email()
    print(f"  ✓  Sending as: {sender}")
except Exception as e:
    print(f"  ✗  Gmail auth failed: {e}")

# ── 6. Email generation (GPT) — dry run ─────────────────
separator("6. AI email generation — dry run (no send)")
try:
    from modules.gmail_integration import generate_subject, generate_email_body
    if leads:
        test_lead = leads[0]
        subject = generate_subject(test_lead)
        body    = generate_email_body(test_lead)
        print(f"  ✓  Lead   : {test_lead['name']} @ {test_lead['company'] or test_lead['email']}")
        print(f"  ✓  Subject: {subject}")
        print(f"\n--- Email preview ---\n{body}\n---------------------")
    else:
        print("  ⚠  No pending leads to generate a preview for.")
except Exception as e:
    print(f"  ✗  Email generation failed: {e}")

separator("All tests complete")
