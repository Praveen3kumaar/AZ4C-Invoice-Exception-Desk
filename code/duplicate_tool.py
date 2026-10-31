
import sqlite3
import re
from datetime import date

from invoice_tool import DB_PATH, get_invoice


def normalize_invoice_number(number):
    return re.sub(r"[\s\-/]", "", number).upper()


def check_duplicates(invoice_id):
    invoice = get_invoice(invoice_id)

    if invoice is None:
        return {
            "invoice_id": invoice_id,
            "status": "ERROR",
            "duplicates": []
        }

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM invoices
        WHERE vendor_id = ?
          AND invoice_id != ?
          AND ABS(total - ?) <= 0.01
        """,
        (
            invoice["vendor_id"],
            invoice_id,
            invoice["total"]
        )
    )

    candidates = [dict(row) for row in cursor.fetchall()]
    conn.close()

    duplicates = []

    for candidate in candidates:
        same_number = (
            normalize_invoice_number(candidate["vendor_invoice_no"])
            == normalize_invoice_number(invoice["vendor_invoice_no"])
        )

        days_apart = abs(
            (
                date.fromisoformat(candidate["invoice_date"])
                - date.fromisoformat(invoice["invoice_date"])
            ).days
        )

        if same_number or days_apart <= 7:
            duplicates.append({
                "invoice_id": candidate["invoice_id"],
                "same_number": same_number,
                "days_apart": days_apart,
                "total": candidate["total"]
            })

    # Check if this invoice was already paid
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT payment_id, invoice_id, amount, status
        FROM payments
        WHERE invoice_id = ?
          AND LOWER(status) = 'paid'
        """,
        (invoice_id,)
    )

    payments = cursor.fetchall()
    conn.close()

    for payment in payments:
        duplicates.append({
            "invoice_id": invoice_id,
            "payment_id": payment["payment_id"],
            "total": payment["amount"],
            "reason": "Invoice already paid"
        })

    return {
        "invoice_id": invoice_id,
        "status": "DUPLICATE" if duplicates else "CLEAR",
        "duplicates": duplicates
    }


if __name__ == "__main__":
    result = check_duplicates("INV-29304")
    print(result)
