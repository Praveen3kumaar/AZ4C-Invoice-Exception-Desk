import json
import uuid

from orchestrator import run_orchestrator
from invoice_tool import (
    get_invoice,
    get_purchase_order,
    get_goods_receipts,
    get_invoice_lines
)
from duplicate_tool import check_duplicates
from agreement_tool import get_applicable_revision


POLICY_SECTIONS = {
    "CLEAN_MATCH": "AP-POL Section 3.1",
    "QTY_SHORT": "AP-POL Section 3.2",
    "PRICE_VARIANCE": "AP-POL Section 3.3",
    "GST_MISMATCH": "AP-POL Section 3.5",
    "DUPLICATE": "AP-POL Section 4.1",
    "BANK_CHANGE_RISK": "AP-POL Section 5.1",
    "VENDOR_BLOCKED": "AP-POL Section 5.2",
    "MISSING_GRN": "AP-POL Section 6.1",
    "UNKNOWN_PO": "AP-POL Section 6.2"
}


def build_result(case_id, invoice_id):
    # Run the AI orchestrator
    result = run_orchestrator(invoice_id)

    # Retrieve the invoice
    invoice = get_invoice(invoice_id)

    if invoice is None:
        raise ValueError(
            f"Invoice {invoice_id} not found; "
            "cannot build a verified result"
        )

    # Get policy reasons from the orchestrator
    policy_reasons = result.get("policy_reasons", [])

    # Determine the main reason code
    if policy_reasons:
        reason_code = policy_reasons[0]
    elif result["decision"] == "PAY":
        reason_code = "CLEAN_MATCH"
    else:
        raise ValueError(
            "Investigation incomplete.\n"
            f"Invoice: {invoice_id}\n"
            f"Decision: {result.get('decision')}\n"
            f"Agents used: {result.get('agents_used')}\n"
            f"Agent results: {json.dumps(result.get('agent_results', []))}\n"
            f"Evidence errors: {result.get('evidence_errors')}")

    # Collect evidence citations
    citations = [invoice_id]

    po = get_purchase_order(invoice["po_id"])
    if po is not None:
        citations.append(po["po_id"])

        receipts = get_goods_receipts(po["po_id"])
        for receipt in receipts:
            citations.append(receipt["grn_id"])

    # Add duplicate invoice and payment evidence
    if "DUPLICATE" in policy_reasons:
        duplicate_result = check_duplicates(invoice_id)

        for duplicate in duplicate_result["duplicates"]:
            if duplicate.get("payment_id"):
                citations.append(duplicate["payment_id"])

            if duplicate.get("invoice_id"):
                citations.append(duplicate["invoice_id"])

    # Cite individual invoice lines and applicable signed agreements
    invoice_lines = get_invoice_lines(invoice_id)

    for line in invoice_lines:
        # Cite the exact invoice line used during matching
        if line.get("line_id"):
            citations.append(line["line_id"])

        # Cite a signed price revision only when it applies
        revision = get_applicable_revision(
            invoice["vendor_id"],
            line["item_code"],
            invoice["invoice_date"]
        )

        if revision is not None:
            agreement_id = revision.get("agreement_id")

            if agreement_id:
                citations.append(agreement_id)

    # Cite the applicable policy section
    citations.append(POLICY_SECTIONS[reason_code])

    # Remove repeated citations
    citations = list(dict.fromkeys(citations))

    decision = result["decision"].lower()
    amount = invoice["total"]

    needs_human = (
        decision in ("hold", "escalate")
        or amount > 500000
    )

    return {
        "case_id": case_id,
        "decision": decision,
        "reason_code": reason_code,
        "amount": amount,
        "citations": citations,
        "needs_human": needs_human,
        "trace_id": str(uuid.uuid4()),
        "other_reasons": policy_reasons[1:],
        "agents_used": result.get("agents_used", []),
        "agent_results": result.get("agent_results", []),
        "evidence_errors": result.get("evidence_errors", [])
    }


if __name__ == "__main__":
    output = build_result(
        "UC1-DEMO",
        "INV-29304"
    )

    print(json.dumps(output, indent=2))
