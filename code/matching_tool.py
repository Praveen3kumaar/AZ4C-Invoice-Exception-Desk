
from asyncio import exceptions

from invoice_tool import (
    get_invoice,
    get_purchase_order,
    get_invoice_lines,
    get_po_lines,
    get_goods_receipts,
    get_grn_lines,
)
from agreement_tool import get_applicable_revision


def check_three_way_match(invoice_id):
    invoice = get_invoice(invoice_id)

    if invoice is None:
        return {"status": "ERROR", "reason": "Invoice not found"}

    po = get_purchase_order(invoice["po_id"])

    if po is None:
        return {"status": "HOLD", "reason": "Purchase order not found"}

    invoice_lines = get_invoice_lines(invoice_id)
    po_lines = get_po_lines(invoice["po_id"])
    receipts = get_goods_receipts(invoice["po_id"])

    received_lines = []
    for receipt in receipts:
        received_lines.extend(get_grn_lines(receipt["grn_id"]))

    exceptions = []

    if not receipts:
        exceptions.append(
            f"MISSING_GRN: No goods receipt found for PO {invoice['po_id']}"
        )

    if invoice["vendor_id"] != po["vendor_id"]:
        exceptions.append("Vendor mismatch")

    for line in invoice_lines:
        matching_po = next(
            (p for p in po_lines if p["line_no"] == line["po_line_no"]),
            None
        )

        if matching_po is None:
            exceptions.append(f"PO line missing for {line['item_code']}")
            continue

        if line["item_code"] != matching_po["item_code"]:
            exceptions.append(f"Item mismatch for {line['item_code']}")




        po_price = matching_po["unit_price"]
        invoice_price = line["unit_price"]

        # Check for a signed, effective price revision
        revision = get_applicable_revision(
            invoice["vendor_id"],
            line["item_code"],
            invoice["invoice_date"]
        )

        if revision:
            expected_price = revision["revised_price"]
        else:
            expected_price = po_price

        # AP Policy: 2% price tolerance
        allowed_difference = abs(expected_price) * 0.02

        if abs(invoice_price - expected_price) > allowed_difference:
            exceptions.append(
                f"PRICE_VARIANCE for {line['item_code']}: "
                f"expected price={expected_price}, "
                f"invoice price={invoice_price}"
            )


        received_qty = sum(
            r["qty_received"]
            for r in received_lines
            if r["po_line_no"] == line["po_line_no"]
            and r["item_code"] == line["item_code"]
        )

        if receipts and line["qty"] > received_qty:
            exceptions.append(
                f"QTY_SHORT for {line['item_code']}: "
                f"invoiced {line['qty']}, received {received_qty}")

    return {
        "invoice_id": invoice_id,
        "status": "MATCH" if not exceptions else "HOLD",
        "exceptions": exceptions
    }


if __name__ == "__main__":
    for invoice_id in ["INV-29304", "INV-29305", "INV-29306"]:
        result = check_three_way_match(invoice_id)
        print(result)
