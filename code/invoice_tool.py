
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = Path(
    os.getenv("DATA_DIR", str(PROJECT_ROOT))
).resolve()

DB_PATH = DATA_DIR / "data" / "ap.sqlite"

if not DB_PATH.is_file():
    raise FileNotFoundError(
        f"Database not found at: {DB_PATH}"
    )

def get_invoice(invoice_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM invoices WHERE invoice_id = ?",
        (invoice_id,)
    )

    invoice = cursor.fetchone()
    conn.close()

    if invoice is None:
        return None

    return dict(invoice)


def get_purchase_order(po_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM purchase_orders WHERE po_id = ?",
        (po_id,)
    )

    purchase_order = cursor.fetchone()
    conn.close()

    if purchase_order is None:
        return None

    return dict(purchase_order)


def get_invoice_lines(invoice_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM invoice_lines WHERE invoice_id = ?",
        (invoice_id,)
    )

    lines = cursor.fetchall()
    conn.close()

    return [dict(line) for line in lines]


def get_po_lines(po_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM po_lines WHERE po_id = ?",
        (po_id,)
    )

    lines = cursor.fetchall()
    conn.close()

    return [dict(line) for line in lines]

def get_goods_receipts(po_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM goods_receipts WHERE po_id = ?",
        (po_id,)
    )

    receipts = cursor.fetchall()
    conn.close()

    return [dict(receipt) for receipt in receipts]

def get_grn_lines(grn_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM grn_lines WHERE grn_id = ?",
        (grn_id,)
    )

    lines = cursor.fetchall()
    conn.close()

    return [dict(line) for line in lines]

def get_possible_duplicates(invoice_id):
    invoice = get_invoice(invoice_id)

    if invoice is None:
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM invoices
        WHERE vendor_id = ?
          AND vendor_invoice_no = ?
          AND invoice_id != ?
        """,
        (
            invoice["vendor_id"],
            invoice["vendor_invoice_no"],
            invoice_id
        )
    )

    duplicates = cursor.fetchall()
    conn.close()

    return [dict(row) for row in duplicates]


def get_item(item_code):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM items WHERE item_code = ?",
        (item_code,)
    )

    item = cursor.fetchone()
    conn.close()

    return dict(item) if item else None


def get_vendor(vendor_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM vendors WHERE vendor_id = ?",
        (vendor_id,)
    )

    vendor = cursor.fetchone()
    conn.close()

    return dict(vendor) if vendor else None



if __name__ == "__main__":
    po_lines = get_po_lines("PO-7014")

    print("\nPURCHASE ORDER LINE ITEMS:")
    for line in po_lines:
        print(line)

    receipts = get_goods_receipts("PO-7014")
    print("\nGOODS RECEIPTS:")
    for receipt in receipts:
        print(receipt)

    grn_lines = get_grn_lines("GRN-5005")
    print("\nGOODS RECEIPT LINE ITEMS:")
    for line in grn_lines:
        print(line)

    duplicates = get_possible_duplicates("INV-29304")
    print("\nPOSSIBLE DUPLICATES:")
    print(duplicates)



# Test our tool

if __name__ == "__main__":
    invoice = get_invoice("INV-29304")
    print("INVOICE:", invoice)

    po = get_purchase_order(invoice["po_id"])
    print("\nPURCHASE ORDER:", po)

    lines = get_invoice_lines(invoice["invoice_id"])
    print("\nINVOICE LINE ITEMS:")

    for line in lines:
        print(line)
