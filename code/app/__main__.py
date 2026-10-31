
"""
AZ4C - Invoice Exception Desk

Run from the code/ directory:

python -m app run --case ../samples/UC1-S01.json --out out/UC1-S01.json

python -m app eval --cases tests/cases

python -m app approve <run_id> --action approve|reject|change
"""
import time
import argparse
import json
import os
import sys
from pathlib import Path


# --------------------------------------------------
# Project paths and environment setup
# --------------------------------------------------

CODE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = CODE_DIR.parent


def load_env_file(path: Path) -> None:
    """Load environment variables without overwriting existing ones."""

    if not path.is_file():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)

            os.environ.setdefault(
                key.strip(),
                value.strip().strip('"').strip("'")
            )


load_env_file(CODE_DIR / ".env")

DATA_DIR = Path(
    os.environ.get("DATA_DIR", str(REPO_DIR))
).resolve()


# --------------------------------------------------
# Step 1: Run an invoice case
# --------------------------------------------------

def run_case(case: dict, auto_approve: bool) -> dict:
    """
    Process an invoice using the AI orchestrator.

    Input example:
    {
        "case_id": "UC1-S01",
        "input": {
            "invoice_id": "INV-12345"
        }
    }
    """

    from result_builder import build_result

    case_id = case["case_id"]
    invoice_id = case["input"]["invoice_id"]

    result = build_result(
        case_id=case_id,
        invoice_id=invoice_id
    )

    # Part A returns an investigation recommendation.
    # auto_approve does not bypass safety or human review.
    # A genuine approval workflow belongs to Parts B/C.

    return result


# --------------------------------------------------
# Step 2: Human approval (Parts B and C)
# --------------------------------------------------

def approve(run_id: str, action: str) -> None:
    """
    Approval workflow is not implemented yet.

    Never treat an unimplemented approval as authorization
    to release a payment.
    """

    raise NotImplementedError(
        "Human approval and resume workflow is not "
        "implemented yet (Parts B/C). "
        f"Run ID: {run_id}, requested action: {action}"
    )


# --------------------------------------------------
# Step 3: Evaluate one result
# --------------------------------------------------

def score_case(result: dict, expected: dict) -> float:
    """
    Compare an actual result with an expected result.

    Returns a score between 0.0 and 1.0.

    This is a local evaluation metric, not the
    official evaluator's private scoring formula.
    """

    # Do not award full credit when agent execution
    # or evidence validation failed.

    if result.get("evidence_errors"):
        return 0.0

    agent_results = result.get("agent_results", [])

    if any(
        agent.get("recommendation") == "REVIEW"
        for agent in agent_results
    ):
        return 0.0

    # Dynamic routing: verify that every selected specialist
    # completed its investigation, without requiring all three.
    selected_agents = result.get("agents_used", [])
    completed_agents = [
        agent.get("agent") for agent in agent_results
    ]

    valid_agents = {"matching", "duplicate", "risk"}
    if (
        not isinstance(selected_agents, list)
        or not selected_agents
        or any(name not in valid_agents for name in selected_agents)
        or len(selected_agents) != len(set(selected_agents))
        or len(completed_agents) != len(set(completed_agents))
        or set(selected_agents) != set(completed_agents)
    ):
        return 0.0

    checks = []

    def add_check(passed, weight=1.0):
        checks.append((bool(passed), weight))

    # Check decision
    if "decision" in expected:
        actual_decision = str(
            result.get("decision", "")
        ).lower()

        expected_decision = str(
            expected["decision"]
        ).lower()

        add_check(
            actual_decision == expected_decision,
            weight=3.0
        )

    # Check reason code
    expected_reason = expected.get(
        "reason_code",
        expected.get("reason_codes")
    )

    if expected_reason is not None:
        actual_reasons = [
            result.get("reason_code")
        ] + result.get("other_reasons", [])

        actual_reasons = [
            str(reason).upper()
            for reason in actual_reasons
            if reason is not None
        ]

        if isinstance(expected_reason, list):
            accepted_reasons = [
                str(reason).upper()
                for reason in expected_reason
            ]
        else:
            accepted_reasons = [
                str(expected_reason).upper()
            ]

        add_check(
            any(
                reason in accepted_reasons
                for reason in actual_reasons
            ),
            weight=3.0
        )


    # Check invoice amount using the official tolerance format
    if "amount" in expected:
        expected_amount = expected["amount"]
        actual_amount = result.get("amount")

        if isinstance(expected_amount, dict):
            expected_value = expected_amount.get("value")
            tolerance = expected_amount.get("tolerance", 1.0)
        else:
            expected_value = expected_amount
            tolerance = 1.0

        if expected_value is None:
            amount_ok = actual_amount is None
        else:
            try:
                amount_ok = (
                    actual_amount is not None
                    and abs(
                        float(actual_amount) - float(expected_value)
                    ) <= float(tolerance)
                )
            except (TypeError, ValueError):
                amount_ok = False

        add_check(amount_ok, weight=2.0)


    # Check human-review requirement
    if "needs_human" in expected:
        add_check(
            result.get("needs_human")
            is expected["needs_human"],
            weight=2.0
        )

    # Check required citations
    must_cite = expected.get("must_cite", [])

    if isinstance(must_cite, str):
        must_cite = [must_cite]

    if must_cite:
        citations = [
            str(value)
            for value in result.get("citations", [])
        ]

        for required_citation in must_cite:
            add_check(
                any(
                    str(required_citation) in citation
                    for citation in citations
                ),
                weight=1.0
            )

    # Check key numbers when expected output supplies them
    expected_numbers = expected.get("key_numbers", {})

    if isinstance(expected_numbers, dict):
        actual_numbers = result.get("key_numbers", {})

        for key, expected_value in expected_numbers.items():
            actual_value = actual_numbers.get(key)

            try:
                numbers_match = (
                    actual_value is not None
                    and abs(
                        float(actual_value)
                        - float(expected_value)
                    ) <= 1.0
                )
            except (TypeError, ValueError):
                numbers_match = (
                    actual_value == expected_value
                )

            add_check(numbers_match, weight=1.0)

    # No applicable checks means no score
    if not checks:
        return 0.0

    earned = sum(
        weight for passed, weight in checks
        if passed
    )

    possible = sum(
        weight for _, weight in checks
    )

    return round(earned / possible, 4)


# --------------------------------------------------
# Step 4: CLI - Run one case
# --------------------------------------------------

def cmd_run(args) -> None:

    case_path = Path(args.case)
    output_path = Path(args.out)

    if not case_path.is_file():
        raise FileNotFoundError(
            f"Case file not found: {case_path}"
        )

    case = json.loads(
        case_path.read_text(encoding="utf-8")
    )

    result = run_case(
        case,
        auto_approve=args.auto_approve
    )

    from mock_erp import save_mock_decision

    invoice_id = case["input"]["invoice_id"]

    save_mock_decision(invoice_id, result)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(f"Case completed: {case['case_id']}")
    print(f"Decision: {result['decision']}")
    print(f"Reason: {result['reason_code']}")
    print(f"Output saved: {output_path}")


# --------------------------------------------------
# Step 5: CLI - Evaluate multiple cases
# --------------------------------------------------

def cmd_eval(args) -> None:

    cases_dir = Path(args.cases).resolve()

    if not cases_dir.is_dir():
        raise FileNotFoundError(
            f"Cases folder not found: {cases_dir}"
        )

    expected_dir = cases_dir / "expected"

    if not expected_dir.is_dir():
        expected_dir = cases_dir.parent / "expected"

    if not expected_dir.is_dir():
        raise FileNotFoundError(
            f"Expected results folder not found: {expected_dir}"
        )

    per_case = []

    case_files = sorted(
        cases_dir.glob("*.json")
    )

    for case_file in case_files:

        case = json.loads(
            case_file.read_text(encoding="utf-8")
        )

        case_id = case["case_id"]

        try:
            expected_file = expected_dir / case_file.name

            expected = json.loads(
                expected_file.read_text(
                    encoding="utf-8"
                )
            )

            # Execute the AI system
            result = run_case(
                case,
                auto_approve=True
            )

            # Save actual result
            output_path = CODE_DIR / "out" / case_file.name

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            output_path.write_text(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            # Calculate accuracy
            score = score_case(
                result,
                expected
            )

        except Exception as error:
            print(
                f"{case_id}: "
                f"{type(error).__name__}: {error}",
                file=sys.stderr
            )

            score = 0.0

        per_case.append({
            "case_id": case_id,
            "score": score
        })

        print(f"{case_id}: {score:.2f}")
        # Pace evaluation requests to reduce Groq TPM rate limits.
        # Do not pause after the final test case.
        if case_file != case_files[-1]:
            time.sleep(20)

    total_cases = len(per_case)

    if total_cases:
        total_score = round(
            100 * sum(
                item["score"]
                for item in per_case
            ) / total_cases,
            1
        )
    else:
        total_score = 0.0

    report = {
        "cases": total_cases,
        "score": total_score,
        "per_case": per_case
    }

    print()
    print(f"Cases evaluated: {total_cases}")
    print(f"Final score: {total_score}%")

    # Save score.json for assignment evaluation
    tests_dir = CODE_DIR / "tests"

    if cases_dir.is_relative_to(tests_dir):
        tests_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        score_path = tests_dir / "score.json"

        score_path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        print(f"Score report saved: {score_path}")


# --------------------------------------------------
# Step 6: CLI - Approval command
# --------------------------------------------------

def cmd_approve(args) -> None:
    approve(
        args.run_id,
        args.action
    )


# --------------------------------------------------
# Step 7: Command-line arguments
# --------------------------------------------------

def main() -> None:

    parser = argparse.ArgumentParser(
        prog="python -m app",
        description="AZ4C Invoice Exception Desk"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True
    )

    # Run command
    run_parser = sub.add_parser(
        "run",
        help="Process one invoice case"
    )

    run_parser.add_argument(
        "--case",
        required=True,
        help="Input case JSON file"
    )

    run_parser.add_argument(
        "--out",
        required=True,
        help="Output result JSON file"
    )

    run_parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Compatibility option for automated testing"
    )

    run_parser.set_defaults(
        func=cmd_run
    )

    # Eval command
    eval_parser = sub.add_parser(
        "eval",
        help="Evaluate invoice test cases"
    )

    eval_parser.add_argument(
        "--cases",
        required=True,
        help="Folder containing case JSON files"
    )

    eval_parser.set_defaults(
        func=cmd_eval
    )

    # Approval command
    approve_parser = sub.add_parser(
        "approve",
        help="Human approval workflow (Parts B/C)"
    )

    approve_parser.add_argument(
        "run_id"
    )

    approve_parser.add_argument(
        "--action",
        required=True,
        choices=[
            "approve",
            "reject",
            "change"
        ]
    )

    approve_parser.set_defaults(
        func=cmd_approve
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
