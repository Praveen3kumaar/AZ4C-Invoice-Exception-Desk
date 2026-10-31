from datetime import date
from invoice_tool import get_invoice, get_invoice_lines, get_item, get_vendor


def check_invoice_risk(invoice_id):
    invoice = get_invoice(invoice_id)

    if invoice is None:
        return {
            "invoice_id": invoice_id,
            "status": "ERROR",
            "risks": ["Invoice not found"]
        }

    lines = get_invoice_lines(invoice_id)
    risks = []


    # Vendor checks - AP Policy Section 5
    vendor = get_vendor(invoice["vendor_id"])

    if vendor is None:
        risks.append("Vendor record missing")

    else:
        # Section 5.2: Blocked vendor
        if vendor["status"].lower() == "blocked":
            risks.append("VENDOR_BLOCKED")

        # Section 5.1: Recent bank account change
        changed_on = vendor["bank_account_changed_on"]

        if changed_on and invoice["total"] > 500000:
            invoice_date = date.fromisoformat(invoice["invoice_date"])
            bank_change_date = date.fromisoformat(changed_on)

            days_difference = (invoice_date - bank_change_date).days

            if 0 <= days_difference <= 30:
                risks.append("BANK_CHANGE_RISK")


    # Check each invoice line against the item master
    for line in lines:
        item = get_item(line["item_code"])

        if item is None:
            risks.append(
                f"Missing item-master record for {line['item_code']}"
            )
            continue

        if line["gst_rate"] != item["gst_rate"]:
            risks.append(
                f"GST_MISMATCH for {line['item_code']}: "
                f"invoice GST rate={line['gst_rate']}%, "
                f"item master GST rate={item['gst_rate']}%"
            )


    calculated_subtotal = round(
        sum(line["qty"] * line["unit_price"] for line in lines), 2
    )

    calculated_gst = round(
        sum(line["gst_amount"] for line in lines), 2
    )

    calculated_total = round(calculated_subtotal + calculated_gst, 2)

    if not lines:
        risks.append("Invoice has no line items")

    if abs(invoice["subtotal"] - calculated_subtotal) > 0.01:
        risks.append("Invoice subtotal mismatch")

    if abs(invoice["gst_amount"] - calculated_gst) > 1.00:
        risks.append("GST amount mismatch")

    if abs(invoice["total"] - calculated_total) > 0.01:
        risks.append("Invoice total mismatch")

    return {
        "invoice_id": invoice_id,
        "status": "CLEAR" if not risks else "RISK",
        "risks": risks,
        "calculated_total": calculated_total
    }


if __name__ == "__main__":
    result = check_invoice_risk("INV-29304")
    print(result)
