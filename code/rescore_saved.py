
import json
from pathlib import Path

from app.__main__ import score_case

BASE = Path(__file__).resolve().parent
CASES = BASE / "tests" / "cases"
EXPECTED = BASE / "tests" / "expected"
OUTPUTS = BASE / "out"

per_case = []

for case_file in sorted(CASES.glob("*.json")):
    case = json.loads(case_file.read_text(encoding="utf-8"))
    result_file = OUTPUTS / case_file.name
    expected_file = EXPECTED / case_file.name

    try:
        result = json.loads(result_file.read_text(encoding="utf-8"))
        expected = json.loads(expected_file.read_text(encoding="utf-8"))

        score = score_case(result, expected)

    except Exception as error:
        print(f"{case['case_id']}: ERROR - {error}")
        score = 0.0

    per_case.append({
        "case_id": case["case_id"],
        "score": score
    })

    print(f"{case['case_id']}: {score:.2f}")

total = round(
    100 * sum(item["score"] for item in per_case) / len(per_case),
    1
) if per_case else 0.0

report = {
    "cases": len(per_case),
    "score": total,
    "per_case": per_case
}

report_path = BASE / "tests" / "score.json"
report_path.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print(f"\nSaved-output score: {total}%")
print(f"Report updated: {report_path}")
