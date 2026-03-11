"""Google Sheets integration — reads leads, creates/updates Status columns."""

import os
from datetime import datetime
from googleapiclient.discovery import build
from modules.google_auth import get_credentials

# ── Column layout (0-based index) — mapped to the actual sheet ───────────────
# Read-only lead data columns (existing in the sheet)
COL_NAME         = 24  # Y  — full_name
COL_FIRST_NAME   = 23  # X  — first_name
COL_EMAIL        = 22  # W  — email
COL_PERSONAL_EMAIL = 33 # AH — personal_email (fallback)
COL_COMPANY      = 11  # L  — company_name
COL_JOB_TITLE    = 28  # AC — job_title
COL_HEADLINE     = 26  # AA — headline
COL_INDUSTRY     = 27  # AB — industry

# Alia-managed tracking columns — appended AFTER the last data column (AJ=35)
COL_STATUS       = 36  # AK — pending / sent / follow-up
COL_SENT_DATE    = 37  # AL — date email was sent
COL_REPLY_STATUS = 38  # AM — replied / no reply
COL_LAST_CHECKED = 39  # AN — last time reply was checked

MANAGED_HEADERS = ["Status", "Sent Date", "Reply Status", "Last Checked"]
MANAGED_START   = COL_STATUS   # first managed column index

_service = None


def _get_service():
    global _service
    if _service is None:
        creds = get_credentials()
        _service = build("sheets", "v4", credentials=creds)
    return _service


def _sheet_id() -> str:
    sid = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if not sid:
        raise ValueError(
            "GOOGLE_SHEET_ID is not set in .env — "
            "add GOOGLE_SHEET_ID=<your_sheet_id> to your .env file."
        )
    return sid


def _col_letter(index: int) -> str:
    """Convert 0-based column index to spreadsheet letter (0→A, 4→E …)."""
    result = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def ensure_alia_columns(sheet_name: str = "Sheet1") -> None:
    """
    Make sure Alia tracking columns (Status, Sent Date, Reply Status, Last Checked)
    exist after the last data column. Expands the sheet grid if needed.
    """
    svc = _get_service()

    # ── 1. Get current sheet grid size and expand columns if needed ───────────
    meta = svc.spreadsheets().get(spreadsheetId=_sheet_id()).execute()
    sheet_meta = next(
        (s for s in meta["sheets"] if s["properties"]["title"] == sheet_name),
        meta["sheets"][0]
    )
    current_cols = sheet_meta["properties"]["gridProperties"]["columnCount"]
    needed_cols  = COL_LAST_CHECKED + 1  # 40

    if current_cols < needed_cols:
        sheet_id_int = sheet_meta["properties"]["sheetId"]
        svc.spreadsheets().batchUpdate(
            spreadsheetId=_sheet_id(),
            body={"requests": [{
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id_int,
                        "gridProperties": {"columnCount": needed_cols},
                    },
                    "fields": "gridProperties.columnCount",
                }
            }]},
        ).execute()

    # ── 2. Write header labels for any missing managed columns ────────────────
    result = svc.spreadsheets().values().get(
        spreadsheetId=_sheet_id(),
        range=f"{sheet_name}!1:1",
    ).execute()
    existing = result.get("values", [[]])[0] if result.get("values") else []

    updates = []
    for i, header in enumerate(MANAGED_HEADERS):
        col_idx = MANAGED_START + i
        while len(existing) <= col_idx:
            existing.append("")
        if existing[col_idx] != header:
            updates.append({
                "range": f"{sheet_name}!{_col_letter(col_idx)}1",
                "values": [[header]],
            })

    if updates:
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=_sheet_id(),
            body={"valueInputOption": "RAW", "data": updates},
        ).execute()


def _build_lead(row: list, row_num: int) -> dict | None:
    """Build a lead dict from a raw sheet row. Returns None if name/email missing."""
    while len(row) < COL_LAST_CHECKED + 1:
        row.append("")

    name  = row[COL_NAME].strip() or row[COL_FIRST_NAME].strip()
    email = row[COL_EMAIL].strip() or row[COL_PERSONAL_EMAIL].strip()
    if not name or not email:
        return None

    # Compose rich notes from available context columns
    notes_parts = []
    if row[COL_JOB_TITLE].strip():
        notes_parts.append(f"Job title: {row[COL_JOB_TITLE].strip()}")
    if row[COL_INDUSTRY].strip():
        notes_parts.append(f"Industry: {row[COL_INDUSTRY].strip()}")
    if row[COL_HEADLINE].strip():
        notes_parts.append(f"Headline: {row[COL_HEADLINE].strip()}")

    return {
        "row":     row_num,
        "name":    name,
        "email":   email,
        "company": row[COL_COMPANY].strip(),
        "notes":   " | ".join(notes_parts),
        "status":  row[COL_STATUS].strip().lower(),
    }


def get_pending_leads(sheet_name: str = "Sheet1") -> list[dict]:
    """
    Return all rows where Status is blank or 'pending'.
    Each dict has: row, name, email, company, notes, status
    """
    ensure_alia_columns(sheet_name)
    svc = _get_service()

    result = svc.spreadsheets().values().get(
        spreadsheetId=_sheet_id(),
        range=f"{sheet_name}!A2:AN5000",
    ).execute()

    rows = result.get("values", [])
    leads = []
    for i, row in enumerate(rows):
        lead = _build_lead(row, i + 2)
        if lead and lead["status"] in ("", "pending"):
            leads.append(lead)
    return leads


def get_sent_leads(sheet_name: str = "Sheet1") -> list[dict]:
    """
    Return leads whose Status is 'sent' and Reply Status is not 'replied'.
    Used when checking for replies.
    """
    svc = _get_service()
    result = svc.spreadsheets().values().get(
        spreadsheetId=_sheet_id(),
        range=f"{sheet_name}!A2:AN5000",
    ).execute()

    rows = result.get("values", [])
    leads = []
    for i, row in enumerate(rows):
        lead = _build_lead(row, i + 2)
        if not lead:
            continue
        reply_status = row[COL_REPLY_STATUS].strip().lower() if len(row) > COL_REPLY_STATUS else ""
        if lead["status"] in ("sent", "follow-up") and reply_status != "replied":
            lead["sent_date"] = row[COL_SENT_DATE].strip() if len(row) > COL_SENT_DATE else ""
            leads.append(lead)
    return leads


def get_all_leads_summary(sheet_name: str = "Sheet1") -> dict:
    """Return counts of leads by status for Alia to read aloud."""
    svc = _get_service()
    result = svc.spreadsheets().values().get(
        spreadsheetId=_sheet_id(),
        range=f"{sheet_name}!A2:AN5000",
    ).execute()

    rows = result.get("values", [])
    summary = {"pending": 0, "sent": 0, "follow-up": 0, "replied": 0, "no reply": 0, "total": 0}

    for row in rows:
        while len(row) < COL_LAST_CHECKED + 1:
            row.append("")
        email = row[COL_EMAIL].strip() or row[COL_PERSONAL_EMAIL].strip()
        if not email:
            continue
        summary["total"] += 1
        status       = row[COL_STATUS].strip().lower() if len(row) > COL_STATUS else ""
        reply_status = row[COL_REPLY_STATUS].strip().lower() if len(row) > COL_REPLY_STATUS else ""

        if status in ("", "pending"):
            summary["pending"] += 1
        elif status == "sent":
            summary["sent"] += 1
        elif status == "follow-up":
            summary["follow-up"] += 1

        if reply_status == "replied":
            summary["replied"] += 1
        elif reply_status == "no reply":
            summary["no reply"] += 1

    return summary


def mark_email_sent(row_num: int, sheet_name: str = "Sheet1") -> None:
    """Set Status=sent and record the current timestamp in Sent Date."""
    svc = _get_service()
    col_e = _col_letter(COL_STATUS)
    col_f = _col_letter(COL_SENT_DATE)
    svc.spreadsheets().values().update(
        spreadsheetId=_sheet_id(),
        range=f"{sheet_name}!{col_e}{row_num}:{col_f}{row_num}",
        valueInputOption="RAW",
        body={"values": [["sent", datetime.now().strftime("%Y-%m-%d %H:%M")]]},
    ).execute()


def mark_follow_up(row_num: int, sheet_name: str = "Sheet1") -> None:
    """Set Status=follow-up."""
    svc = _get_service()
    col_e = _col_letter(COL_STATUS)
    svc.spreadsheets().values().update(
        spreadsheetId=_sheet_id(),
        range=f"{sheet_name}!{col_e}{row_num}",
        valueInputOption="RAW",
        body={"values": [["follow-up"]]},
    ).execute()


def update_reply_status(row_num: int, replied: bool, sheet_name: str = "Sheet1") -> None:
    """Set Reply Status (replied / no reply) and update Last Checked timestamp."""
    svc = _get_service()
    col_g = _col_letter(COL_REPLY_STATUS)
    col_h = _col_letter(COL_LAST_CHECKED)
    status_text = "replied" if replied else "no reply"
    svc.spreadsheets().values().update(
        spreadsheetId=_sheet_id(),
        range=f"{sheet_name}!{col_g}{row_num}:{col_h}{row_num}",
        valueInputOption="RAW",
        body={"values": [[status_text, datetime.now().strftime("%Y-%m-%d %H:%M")]]},
    ).execute()
