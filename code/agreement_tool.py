import re
from datetime import datetime, date
from invoice_tool import DATA_DIR

AGREEMENTS_DIR = DATA_DIR / "docs" / "vendor_agreements"


def get_applicable_revision(vendor_id, item_code, invoice_date):
    agreement = get_vendor_agreement(vendor_id)

    if agreement is None:
        return None

    # Only signed agreements are valid
    if "Signed by both parties" not in agreement:
        return None

    invoice_day = date.fromisoformat(invoice_date)

    # Find the agreement ID
    agreement_match = re.search(r"AGR-\d+", agreement)
    agreement_id = (
        agreement_match.group()
        if agreement_match
        else None
    )

    # Find the item in the agreement table
    for line in agreement.splitlines():
        columns = [col.strip() for col in line.split("|")]

        if len(columns) < 6:
            continue

        if columns[1] != item_code:
            continue

        revised_price = float(
            columns[3].replace("₹", "").replace(",", "")
        )

        effective_date = datetime.strptime(
            columns[4], "%d %B %Y"
        ).date()

        # Revision applies only from its effective date
        if invoice_day < effective_date:
            return None

        # Extract the agreement expiry date
        expiry_match = re.search(
            r"fixed until (\d{1,2} \w+ \d{4})",
            agreement,
            re.IGNORECASE
        )

        if expiry_match:
            expiry_date = datetime.strptime(
                expiry_match.group(1), "%d %B %Y"
            ).date()

            if invoice_day > expiry_date:
                return None

        return {
            "agreement_id": agreement_id,
            "vendor_id": vendor_id,
            "item_code": item_code,
            "revised_price": revised_price,
            "effective_date": effective_date.isoformat()
        }

    return None


def get_vendor_agreement(vendor_id):
    file_path = AGREEMENTS_DIR / f"{vendor_id}.md"

    if not file_path.is_file():
        return None

    return file_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    for invoice_date in [
        "2026-09-10",
        "2026-09-20",
        "2027-04-01"
    ]:
        result = get_applicable_revision(
            "V-1001",
            "IT-2017",
            invoice_date
        )
        print(invoice_date, ":", result)
