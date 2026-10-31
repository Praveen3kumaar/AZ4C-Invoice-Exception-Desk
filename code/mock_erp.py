
import json
import re
from datetime import datetime, timezone

from invoice_tool import DATA_DIR
from matching_tool import check_three_way_match


MOCK_DIR = DATA_DIR / "mock_system"
ERP_FILE = MOCK_DIR / "erp_payment_status.jsonl"
OUTBOX_DIR = MOCK_DIR / "outbox"


def save_mock_decision(invoice_id, result):
    """
    Record a decision in the mock ERP.

    This does not execute a real payment or send an email.
    """

    decision = result["decision"]
    reason_code = result["reason_code"]
    needs_human = result["needs_human"]

    if decision not in ("pay", "hold", "escalate"):
        raise ValueError(f"Invalid decision: {decision}")

    # Translate the AI decision into a mock ERP status
    if decision == "pay":
        status = (
            "PENDING_HUMAN_APPROVAL"
            if needs_human
            else "READY_FOR_PAYMENT"
        )
    elif decision == "hold":
        status = "ON_HOLD"
    else:
        status = "ESCALATED"

    MOCK_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "invoice_id": invoice_id,
        "status": status,
        "decision": decision,
        "reason_code": reason_code,
        "needs_human": needs_human,
        "trace_id": result["trace_id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Avoid duplicate ERP records for an unchanged decision.
    # A changed decision or reason still creates a new audit event.
    if ERP_FILE.exists():
        previous_record = None

        with ERP_FILE.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                previous = json.loads(line)

                if previous.get("invoice_id") == invoice_id:
                    previous_record = previous

        if previous_record is not None:
            unchanged = all(
                previous_record.get(field) == record.get(field)
                for field in (
                    "status",
                    "decision",
                    "reason_code",
                    "needs_human"
                )
            )

            if unchanged:
                # Recreate the notice if it was deleted.
                if decision == "hold":
                    create_hold_notice(invoice_id, result)

                return previous_record

    # Append an audit record to the mock ERP file
    with ERP_FILE.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )

    # Generate a vendor correction draft for held invoices
    if decision == "hold":
        create_hold_notice(invoice_id, result)

    return record


def create_hold_notice(invoice_id, result):
    """
    Create a draft vendor correction notice.

    No email is actually sent.
    """

    if not re.fullmatch(r"[A-Za-z0-9_-]+", invoice_id):
        raise ValueError("Unsafe invoice ID for output filename")

    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

    matching = check_three_way_match(invoice_id)
    exceptions = matching.get("exceptions", [])

    details = "\n".join(
        f"- {exception}"
        for exception in exceptions
    )

    if not details:
        details = (
            "- An invoice exception requires clarification "
            "before payment can proceed."
        )

    notice = f"""# Draft Vendor Correction Notice

**Invoice:** {invoice_id}

**Status:** ON HOLD

**Reason code:** {result['reason_code']}

Dear Vendor,

During our invoice verification, we identified the
following issue(s):

{details}

Please review the invoice against the purchase order
and goods receipt, and provide the necessary correction
or supporting documentation.

Payment processing will remain on hold until the issue
has been reviewed and resolved.

Regards,
Accounts Payable Team
Kestrel Auto Components Pvt Ltd

---
Draft generated automatically. Not sent.
"""

    notice_path = OUTBOX_DIR / f"{invoice_id}.md"

    notice_path.write_text(
        notice,
        encoding="utf-8"
    )

    return notice_path
