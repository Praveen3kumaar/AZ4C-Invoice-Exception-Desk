
import json
from pathlib import Path

from jsonschema import Draft202012Validator


CODE_DIR = Path(__file__).resolve().parent

SCHEMA_PATH = CODE_DIR.parent / "schema" / "result.schema.json"
RESULTS_DIR = CODE_DIR / "out"
CASES_DIR = CODE_DIR / "tests" / "cases"


def main():
    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    validator = Draft202012Validator(schema)

    passed = 0
    failed = 0

    for case_file in sorted(CASES_DIR.glob("*.json")):
        result_path = RESULTS_DIR / case_file.name

        if not result_path.exists():
            print(f"FAIL {case_file.stem}: Output missing")
            failed += 1
            continue

        result = json.loads(
            result_path.read_text(encoding="utf-8")
        )

        errors = list(validator.iter_errors(result))

        if errors:
            print(f"FAIL {case_file.stem}")

            for error in errors:
                location = ".".join(
                    str(part) for part in error.path
                )

                print(f"  {location}: {error.message}")

            failed += 1

        else:
            print(f"PASS {case_file.stem}")
            passed += 1

    print()
    print(f"Schema validation: {passed} passed, {failed} failed")


if __name__ == "__main__":
    main()
