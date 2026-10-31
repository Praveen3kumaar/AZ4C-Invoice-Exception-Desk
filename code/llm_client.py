
import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from groq import (
    Groq,
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
)


# -----------------------------------------
# Configuration
# -----------------------------------------

load_dotenv()

MODEL = "openai/gpt-oss-120b"

LOG_FILE = (
    Path(__file__).resolve().parent
    / "llm_calls.jsonl"
)

MAX_API_ATTEMPTS = 3
MAX_JSON_ATTEMPTS = 2

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Check code/.env."
    )

client = Groq(
    api_key=api_key,
    timeout=30.0,
    max_retries=0
)


# -----------------------------------------
# Helper: Write API audit logs
# -----------------------------------------

def write_log(record):
    """
    Record one API attempt.

    Never write API keys or full prompts to logs.
    """

    with LOG_FILE.open(
        "a",
        encoding="utf-8"
    ) as file:
        file.write(
            json.dumps(record, ensure_ascii=False)
            + "\n"
        )


# -----------------------------------------
# Helper: Decide whether to retry
# -----------------------------------------

def is_retryable_error(error):
    """
    Retry only temporary API failures.

    Do not retry authentication errors, invalid
    requests, or unavailable model errors.
    """

    if isinstance(
        error,
        (APIConnectionError, APITimeoutError)
    ):
        return True

    if isinstance(error, APIStatusError):
        return error.status_code in (
            408,
            409,
            429,
            500,
            502,
            503,
            504,
        )

    return False


# -----------------------------------------
# Main LLM function
# -----------------------------------------

def ask_ai(prompt):
    """
    Call Groq with retry support.

    Maximum: 3 API attempts.
    Each attempt is logged separately.
    """

    for attempt in range(
        1,
        MAX_API_ATTEMPTS + 1
    ):

        start = time.perf_counter()

        log = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "model": MODEL,
            "attempt": attempt,
            "status": "ERROR"
        }

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0
            )

            answer = response.choices[0].message.content

            if not isinstance(answer, str) or not answer.strip():
                raise ValueError(
                    "LLM returned an empty response"
                )

            log["status"] = "SUCCESS"
            log["tokens_used"] = (
                response.usage.total_tokens
                if response.usage
                else None
            )

            return answer

        except Exception as error:

            retryable = is_retryable_error(error)

            log["error_type"] = type(error).__name__
            log["retryable"] = retryable

            if isinstance(error, APIStatusError):
                log["http_status"] = error.status_code

            # Stop immediately if:
            # - Error is not temporary, OR
            # - All attempts have been exhausted
            if (
                not retryable
                or attempt == MAX_API_ATTEMPTS
            ):
                raise

            # Backoff: 1 second, then 2 seconds
            delay = 2 ** (attempt - 1)

            print(
                f"LLM temporary failure "
                f"({type(error).__name__}). "
                f"Retrying attempt "
                f"{attempt + 1}/{MAX_API_ATTEMPTS}..."
            )

        finally:
            log["duration_seconds"] = round(
                time.perf_counter() - start,
                3
            )

            write_log(log)

        # Only reached after a retryable failure
        time.sleep(delay)


# -----------------------------------------
# JSON response validation
# -----------------------------------------

def ask_ai_json(
    prompt,
    required_fields,
    allowed_values=None
):
    """
    Request JSON from the LLM.

    Retry an invalid JSON response once.

    API failures are handled by ask_ai().
    """

    current_prompt = prompt

    for attempt in range(
        1,
        MAX_JSON_ATTEMPTS + 1
    ):

        try:
            response = ask_ai(current_prompt)

            # Accept JSON wrapped in a Markdown fence
            cleaned = response.strip()

            if cleaned.startswith("```"):
                lines = cleaned.splitlines()

                if lines[0].strip().lower() in (
                    "```",
                    "```json"
                ):
                    lines = lines[1:]

                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]

                cleaned = "\n".join(lines).strip()

            result = json.loads(cleaned)

            if not isinstance(result, dict):
                raise ValueError(
                    "AI response must be a JSON object"
                )

            for field in required_fields:
                if field not in result:
                    raise ValueError(
                        f"Missing required field: {field}"
                    )

            if allowed_values:
                for field, valid_values in allowed_values.items():

                    if result.get(field) not in valid_values:
                        raise ValueError(
                            f"Invalid value for {field}: "
                            f"{result.get(field)}"
                        )

            return result

        except (
            json.JSONDecodeError,
            ValueError,
            TypeError
        ) as error:

            if attempt == MAX_JSON_ATTEMPTS:
                raise ValueError(
                    "LLM JSON validation failed after "
                    f"{MAX_JSON_ATTEMPTS} attempts: {error}"
                ) from error

            print(
                "LLM returned invalid JSON. "
                "Requesting a corrected response..."
            )

            current_prompt = (
                prompt
                + "\n\nYour previous answer was invalid."
                + f"\nValidation error: {error}"
                + "\nReturn ONLY one valid JSON object "
                "containing the required fields."
            )


# -----------------------------------------
# Manual test
# -----------------------------------------

if __name__ == "__main__":
    response = ask_ai_json(
        """
        Return ONLY valid JSON with:
        {"status": "OK", "message": "Connection working"}
        """,
        required_fields=[
            "status",
            "message"
        ],
        allowed_values={
            "status": ["OK"]
        }
    )

    print(
        json.dumps(
            response,
            indent=2
        )
    )
