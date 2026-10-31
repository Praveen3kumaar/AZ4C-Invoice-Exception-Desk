# AI Usage Disclosure

**Project:** AI Invoice Exception Desk — AZ4C Associate Engineer Assignment (Use Case 1)

## 1. AI coding assistant used

I used **ChatGPT** as an AI coding and learning assistant while developing this project. I used it to:

- Understand the Accounts Payable invoice-matching workflow, dataset and assignment requirements.
- Plan the Orchestrator, specialist-agent, Python-tool and SQLite architecture.
- Draft and revise Python functions, Groq prompts, structured outputs and the Streamlit interface.
- Troubleshoot Python/PowerShell execution, API rate limits, routing logic and evaluation issues.
- Develop additional database-backed test scenarios and compare results against expected answers.
- Review documentation and prepare explanations of the system's operation and limitations.

The submitted code was run and debugged locally. AI-generated suggestions were reviewed against the supplied data, actual program output and the assignment requirements. ChatGPT assisted with implementation; it was **not** used as a substitute for the runtime invoice database or as an authority for final invoice decisions.

## 2. LLM used at runtime

The application uses **`openai/gpt-oss-120b` through the Groq API**. The model is accessed remotely; no model training, fine-tuning or local model hosting is performed.

The runtime model supports two roles:

1. **Orchestrator routing:** receives an invoice summary and verified Python precheck findings, then proposes which specialist AI agents should investigate.
2. **Specialist interpretation:** selected Matching, Duplicate and/or Risk Agents receive tool-generated findings and produce structured recommendations and human-readable explanations.

The Groq integration is centralized in `llm_client.py`, which handles structured JSON-oriented requests, response checking, retries and model-call logging.

## 3. How routing and decisions are controlled

The system uses **hybrid, evidence-driven dynamic routing**:

1. Python retrieves the invoice and runs all three deterministic prechecks: matching, duplicate and risk.
2. The Groq Orchestrator proposes a specialist-agent plan using the verified findings.
3. A Python routing guard includes every specialist required by detected exceptions. The LLM may suggest an additional specialist but cannot suppress a mandatory one.
4. Only the selected specialist LLM agents execute. A clean invoice generally uses one review specialist rather than calling all three.
5. Selected agents' recommendations are checked against fresh deterministic tool evidence.
6. Python applies the Accounts Payable policy, exception priority and human-review rules to determine the final `pay`, `hold` or `escalate` recommendation.

**The LLM does not independently calculate authoritative invoice amounts, modify purchasing records, or authorize payments.** Deterministic checks and policy rules remain the source of truth for financial decisions.

## 4. Evidence sources and tools

Python tools read the supplied SQLite database and local company documents, including AP policy and signed vendor price agreements. The tools assess:

- Invoice, purchase-order and goods-receipt matching
- Quantity shortages and price tolerance
- Effective signed vendor price revisions
- Duplicate invoices and recorded payments
- GST rates and invoice tax totals
- Blocked-vendor and recent bank-change risks

The model receives relevant tool evidence as prompt context; it does not directly query or alter the SQLite database.

## 5. Validation and testing

I tested the application on **13 locally available cases**: five supplied examples and eight additional database-backed cases. The additional cases cover individual exceptions, duplicate payments and combinations of exceptions that test company-policy reason priority.

After implementing dynamic routing, a fresh local evaluation on **October 31, 2026** produced:

- **13/13 local cases passing**
- **100.0% local evaluation score**, recorded in `code/tests/score.json`
- **13/13 JSON outputs passing schema validation**, with no failures

These results reflect the project's local scoring logic and known cases. They do **not** represent results from AZ4C's hidden evaluator or guarantee identical performance under different API conditions.

## 6. Debugging and reliability measures

During development, ChatGPT helped identify and correct an important design issue: the original Orchestrator called all three LLM specialists for every invoice, even when it claimed to select them dynamically. This was changed so all three **Python safety checks** remain mandatory, but only the needed **LLM agents** execute.

The local evaluator also initially required all three agent outputs and therefore returned zero for the dynamically routed runs. The evaluator was updated to validate the agents actually selected and preserve the existing business-decision, amount, citation and human-review comparisons. The revised application was then rerun and validated.

API retries, structured-response validation, call logging, explicit evidence checks and fail-safe escalation reduce the chance that a bad LLM response becomes an unsupported payment recommendation.

## 7. Boundaries and limitations

- AI routing and wording may vary between model calls.
- All required Python evidence checks run regardless of LLM routing.
- Groq API availability and rate limits can affect execution.
- The app investigates invoices present in the supplied dataset; it does not ingest arbitrary new invoice PDFs.
- Streamlit is a review interface; CLI-side ERP status updates and correction notices are **mock outputs**.
- A real interactive human approval/pause/resume mechanism (Parts B/C) is not implemented.
- No live payment execution or real vendor email transmission is performed.

## 8. Disclosure and responsibility

ChatGPT was used for code drafting, debugging, reasoning and documentation. I reviewed the implementation by running it locally, examining evidence and outputs, updating tests, and validating the resulting JSON. I take responsibility for the submitted project and for explaining its design, safeguards and limitations.
