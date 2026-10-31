
import json
from pathlib import Path

from invoice_tool import get_invoice, get_invoice_lines


CASES = [
    {
        "case_id": "UC1-T01",
        "invoice_id": "INV-20129",
        "decision": "pay",
        "reason": "CLEAN_MATCH",
        "citation": "PO-7889",
    },
    {
        "case_id": "UC1-T02",
        "invoice_id": "INV-20041",
        "decision": "hold",
        "reason": "QTY_SHORT",
        "item_code": "IT-2094",
    },
    {
        "case_id": "UC1-T03",
        "invoice_id": "INV-20007",
        "decision": "escalate",
        "reason": "DUPLICATE",
        "citation": "PAY-9222",
    },
    {
        "case_id": "UC1-T04",
        "invoice_id": "INV-20306",
        "decision": "hold",
        "reason": "MISSING_GRN",
        "citation": "PO-7420",
    },
    {
        "case_id": "UC1-T05",
        "invoice_id": "INV-20495",
        "decision": "hold",
        "reason": "PRICE_VARIANCE",
        "item_code": "IT-2141",
    },
    {
        "case_id": "UC1-T06",
        "invoice_id": "INV-20339",
        "decision": "escalate",
        "reason": "DUPLICATE",
        "citation": "PAY-9608",
        "other_reasons": ["VENDOR_BLOCKED"],
    },
    {
        "case_id": "UC1-T07",
        "invoice_id": "INV-20541",
        "decision": "escalate",
        "reason": "DUPLICATE",
        "citation": "PAY-9291",
        "other_reasons": ["BANK_CHANGE_RISK"],
    },
    {
        "case_id": "UC1-T08",
        "invoice_id": "INV-20634",
        "decision": "escalate",
        "reason": "DUPLICATE",
        "citation": "PAY-9446",
        "other_reasons": ["GST_MISMATCH"],
    },
]


def main():
    cases_dir = Path("tests/cases")
    expected_dir = Path("tests/expected")

    cases_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)

    for test in CASES:
        case_id = test["case_id"]
        invoice_id = test["invoice_id"]

        invoice = get_invoice(invoice_id)

        if invoice is None:
            raise ValueError(f"Invoice not found: {invoice_id}")

        # Build input case
        case_input = {
            "case_id": case_id,
            "input": {
                "invoice_id": invoice_id
            }
        }

        citations = [invoice_id]

        if "citation" in test:
            citations.append(test["citation"])

        # For line-level exceptions, cite the affected line
        if "item_code" in test:
            matching_lines = [
                line["line_id"]
                for line in get_invoice_lines(invoice_id)
                if line["item_code"] == test["item_code"]
            ]

            if not matching_lines:
                raise ValueError(
                    f"No line for {test['item_code']} "
                    f"in {invoice_id}"
                )

            citations.extend(matching_lines)

        # These expectations are based on our inspected
        # database evidence, not AI-generated predictions.
        expected = {
            "case_id": case_id,
            "decision": test["decision"],
            "reason_code": [test["reason"]],
            "amount": {
                "value": invoice["total"],
                "tolerance": 1.0
            },
            "must_cite": citations,
            "needs_human": (
                test["decision"] != "pay"
                or invoice["total"] > 500000
            )
        }

        # Record secondary exceptions for manual checking.
        # Our current score_case does not score this field.
        if "other_reasons" in test:
            expected["other_reasons"] = test["other_reasons"]

        (cases_dir / f"{case_id}.json").write_text(
            json.dumps(case_input, indent=2),
            encoding="utf-8"
        )

        (expected_dir / f"{case_id}.json").write_text(
            json.dumps(expected, indent=2),
            encoding="utf-8"
        )

        print(
            f"Created {case_id}: "
            f"{invoice_id} -> "
            f"{test['decision']} / {test['reason']}"
        )

    print("\nTotal new cases:", len(CASES))
    print("Total suite cases:", len(list(cases_dir.glob("*.json"))))


if __name__ == "__main__":
    main()
