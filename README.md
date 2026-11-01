# AI Invoice Exception Desk

**AZ4C AI Agent Developer Assignment | Associate Engineer | Use Case 1**

An evidence-driven multi-agent prototype for the Accounts Payable (AP) team at **Kestrel Auto Components Pvt Ltd** (fictional company). It investigates a supplier invoice using purchasing records, goods receipts, payment history, vendor information, GST checks, and applicable signed price agreements, then returns a structured recommendation to **`pay`**, **`hold`**, or **`escalate`**.

The system uses **one Groq-powered Orchestrator and three specialist AI agents**, with deterministic Python checks acting as safeguards. A command-line run saves a decision to a **local mock ERP**. The Streamlit interface displays investigations but does not write mock ERP decisions.

> **Scope:** This is an Associate Engineer **Part A** prototype. It does **not** release real payments, send real emails, or implement an interactive approval/resume workflow.

## Set up and run

### Requirements

- Python **3.12** and Git
- A **Groq API key** with access to `openai/gpt-oss-120b`
- The **AZ4C Use Case 1 data pack**, obtained separately from the assignment invitation
- Internet access for Groq API calls

**Important:** The supplied data pack is deliberately **not committed** to this repository. Extract it to a local directory. That directory must contain `data/ap.sqlite`, `docs/ap_policy.md`, `docs/vendor_agreements/`, `samples/`, and `schema/result.schema.json`.

### 1. Clone and install (Windows PowerShell)

```powershell
git clone https://github.com/Praveen3kumaar/AZ4C-Invoice-Exception-Desk.git
cd AZ4C-Invoice-Exception-Desk\code
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation for the current terminal, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 2. Configure environment variables

Copy the checked-in template **`code/.env.example`** to **`code/.env`**:

```powershell
Copy-Item .env.example .env
```

Set at least these two values in `code/.env`:

```dotenv
GROQ_API_KEY=your_own_groq_api_key
DATA_DIR=D:/path/to/extracted/AZ4C-UC1-invoice-exception-desk
```

`DATA_DIR` must reference the **data-pack root folder**, **not** the `data/` subfolder or `ap.sqlite` file. On the developer's machine the source pack and code shared a project root; on a fresh clone the extracted data pack may live elsewhere. The application reads local SQLite tables and company documents via this setting.

**Never commit** `.env`, API keys, supplied data files, local LLM logs, generated results, or mock ERP outputs.

### 3. Run one invoice case

With your terminal in **`code/`**:

```powershell
python -m app run --case tests/cases/UC1-S01.json --out out/UC1-S01.json
```

Or run a sample directly from the separately extracted data pack by using its full path:

```powershell
python -m app run --case D:/path/to/extracted/AZ4C-UC1-invoice-exception-desk/samples/UC1-S01.json --out out/UC1-S01.json
```

The CLI writes the result JSON to the chosen `--out` path and invokes the mock ERP saver. The mock system is created under **`DATA_DIR/mock_system/`**:

- `erp_payment_status.jsonl`: simulated invoice decision/status records
- `outbox/<invoice_id>.md`: **draft**, unsent vendor correction notices for held invoices

**Repeated identical decisions are not appended again** to the mock ERP log: `mock_erp.py` checks the latest record for that invoice, avoids duplicates when status, decision, reason and human-review flag are unchanged, and regenerates the hold notice if applicable. Changed decisions are appended as new audit events.

### 4. Run the Streamlit interface (optional)

```powershell
python -m streamlit run streamlit_app.py
```

Enter an existing invoice ID to see the investigation, selected specialists, supporting evidence, decision and human-review flag. **Streamlit does not save a mock ERP decision**; use the CLI `run` command to demonstrate persistence.

### 5. Run the tests and schema validation

```powershell
python -m unittest discover -s tests -p "test_retry_behavior.py" -v
python -m app eval --cases tests/cases
python validate_schema.py
```

Evaluation invokes the Groq API and may be affected by rate limits. It writes test outputs under `code/out/` and the local score report at `code/tests/score.json`. The schema check validates generated JSON outputs against the **externally supplied** `schema/result.schema.json` via `DATA_DIR`.

The `approve` command is only a placeholder for optional Parts B/C. The `--auto-approve` CLI option does not implement approval or authorize payment.

## Design

### Agent architecture

The Orchestrator uses **hybrid dynamic routing**—not a fixed sequence of three LLM specialists:

1. **Collect evidence:** Fetch the invoice and always run three **deterministic Python prechecks**: matching, duplicate and risk.
2. **Plan:** Send the invoice and verified findings to Groq; the **Orchestrator LLM** proposes which specialists to use.
3. **Enforce safe routing:** A Python guard includes specialists required by detected exceptions. For clean invoices, one specialist still reviews the case. Only the selected **AI specialist agents** execute.
4. **Investigate:** Selected Matching, Duplicate and/or Risk Agents use Python tool evidence and Groq to produce structured findings.
5. **Validate and retry:** The Orchestrator compares each specialist's recommendation with **fresh Python evidence**. If an answer is invalid, inconsistent, or fails, it calls that specialist **one more time** (two attempts total), checking the response again. A second failure triggers **safe escalation** for human review. The retry re-invokes the specialist's existing prompt; it does not currently inject a custom correction message.
6. **Apply AP policy:** Python prioritizes exceptions and determines `pay`, `hold`, or `escalate`. The LLM does not authorize payments or override evidence.
7. **Return and save:** The Result Builder assembles a JSON response with citations and a trace ID. The CLI writes the result and simulated ERP status; Streamlit displays it.

[**Detailed architecture diagram and component explanation**](code/docs/architecture.md)

### Dynamic-routing examples observed in local tests

| Invoice | Verified issue | Selected LLM specialist(s) | Outcome |
|---|---|---|---|
| `INV-20129` | No exception | Matching | `pay` |
| `INV-20041` | Quantity shortage | Matching | `hold` |
| `INV-29304` | Duplicate / previously paid | Duplicate | `escalate` |
| `INV-20339` | Duplicate + blocked vendor | Duplicate, Risk | `escalate` |
| `INV-20541` | Duplicate + recent bank-change risk | Duplicate, Risk | `escalate` |

**All three Python prechecks execute on valid invoices; the table shows only the selected LLM specialists.**

### Business rules

The system checks invoice/PO/GRN quantities, purchase prices (including applicable signed vendor agreements), GST, duplicate payments, blocked suppliers and relevant bank-account changes. The implementation uses the supplied AP policy, including a **2% price tolerance** where applicable.

Final exception priority in the implementation:

`DUPLICATE` → `VENDOR_BLOCKED` → `BANK_CHANGE_RISK` → `UNKNOWN_PO` → `MISSING_GRN` → `QTY_SHORT` → `PRICE_VARIANCE` → `GST_MISMATCH`.

- **`pay`:** checks are clean (`CLEAN_MATCH`).
- **`hold`:** correctable issues such as missing GRN, quantity shortage, price variance or GST mismatch.
- **`escalate`:** duplicate invoices, blocked suppliers, bank-change risk, unknown POs or unresolved safety/validation failures.
- **`needs_human`:** true for every hold or escalation, or a payment recommendation **above ₹5 lakh**. This is a flag, **not** an implemented approval workflow.

### Components and tools

| File | Responsibility |
|---|---|
| `code/orchestrator.py` | LLM routing, mandatory prechecks, safety guard, selected agent execution, evidence validation and corrective retry, policy decision |
| `code/matching_agent.py` | Specialist for three-way match and price evidence |
| `code/duplicate_agent.py` | Specialist for duplicate/payment evidence |
| `code/risk_agent.py` | Specialist for GST/vendor risks |
| `code/matching_tool.py` | Deterministic invoice/PO/GRN comparison |
| `code/duplicate_tool.py` | Deterministic duplicate and payment checks |
| `code/risk_tool.py` | Deterministic tax and supplier-risk checks |
| `code/invoice_tool.py` | SQLite data-access helpers; resolves `DATA_DIR` |
| `code/agreement_tool.py` | Signed vendor price agreement lookup |
| `code/llm_client.py` | Groq requests, response handling, API retries and call metadata logging |
| `code/result_builder.py` | Final JSON assembly, citations and trace identifiers |
| `code/mock_erp.py` | Idempotent mock status persistence and draft hold notices |
| `code/streamlit_app.py` | Local browser investigation interface |
| `code/app/__main__.py` | `python -m app run` and `eval` CLI commands |

## Models used and why

- **Provider:** Groq API (remote inference)
- **Model:** `openai/gpt-oss-120b`
- **Usage:** LLM Orchestrator selects relevant specialists; selected agents produce structured investigations and explanations from **tool-supplied evidence**.
- **Reason:** A Groq-hosted model satisfies the assignment's permitted-provider requirement and avoids locally running an LLM. Python handles financial calculations and policy decisions for consistency.

No local model training or fine-tuning is performed. The Groq API processes invoice context and tool-derived findings; use only the supplied **synthetic assignment data** in this prototype. The same model is used for routing and specialist tasks, so API rate limits can affect evaluation speed.

## Failure handling

- **Mandatory tool checks:** Matching, duplicate and risk prechecks run before AI specialist routing; the LLM cannot suppress a required specialist.
- **Routing checks:** Invalid or unusable Orchestrator routing does not silently produce an automatic payment.
- **Agent-response validation:** Each selected specialist's invoice ID, identity and recommendation are checked against the deterministic tool output.
- **Agent-answer retry:** When a specialist response fails validation or the call raises an error, the Orchestrator retries that specialist **once** and validates again. If it still fails, the decision **escalates** instead of paying.
- **API handling:** `llm_client.py` performs its own structured-response/API handling and records model-call metadata; this is separate from the Orchestrator's evidence-based specialist retry.
- **Logging:** Local `code/llm_calls.jsonl` logs call metadata (timestamp, model, status, token use and duration). The file is ignored by Git. It records call outcomes but does not, by itself, identify which agent initiated each call.
- **Persistence:** The CLI writes the result JSON and mock ERP decision; unchanged status/reason combinations are not duplicated in the ERP log. Held invoices create or refresh a **draft** vendor notice.
- **Limitations:** LLM output may vary, Groq rate limits can occur, and the app does not ingest new invoice PDFs or send actual payments/emails. Interactive human approval and restartable workflows are out of scope for Part A.

## Tests and score

The repository contains **13 test cases** and their expected answers: five supplied scenarios (`UC1-S01`–`UC1-S05`) and eight additional database-backed cases (`UC1-T01`–`UC1-T08`). Scenarios include clean invoices, shortages, missing GRNs, price/GST mismatches, duplicates, and multiple simultaneous risk flags.

**Latest local verification (November 1, 2026, after implementing specialist retries):**

| Check | Observed result |
|---|---|
| Unit tests simulating an initially wrong then corrected AI answer, and two wrong answers | **2/2 passed** |
| `python -m app eval --cases tests/cases` | **13/13 cases, 100.0% local score** |
| `python validate_schema.py` | **13/13 valid outputs, 0 failures** |
| CLI HOLD / `QTY_SHORT` scenario | Correct decision and draft notice produced |
| Mock ERP | PAY, HOLD and ESCALATE records verified; identical reruns do not duplicate an unchanged decision |

The score is from the **project's local evaluator** and known cases; it is **not** a claim about AZ4C's hidden tests. Additional special-case reliability work and a fresh-clone run are not claimed as completed.

## Repository layout

```text
AZ4C-Invoice-Exception-Desk/
├── README.md
├── AI_USAGE.md
├── .gitignore
└── code/
    ├── .env.example          # template only; create ignored .env locally
    ├── requirements.txt
    ├── app/
    │   └── __main__.py      # CLI
    ├── orchestrator.py
    ├── matching_agent.py
    ├── duplicate_agent.py
    ├── risk_agent.py
    ├── matching_tool.py
    ├── duplicate_tool.py
    ├── risk_tool.py
    ├── invoice_tool.py
    ├── agreement_tool.py
    ├── llm_client.py
    ├── result_builder.py
    ├── mock_erp.py
    ├── streamlit_app.py
    ├── validate_schema.py
    ├── docs/
    │   └── architecture.md
    └── tests/
        ├── cases/
        ├── expected/
        ├── test_retry_behavior.py
        └── score.json
```

The required **assignment data pack is external**, not a subdirectory checked into this repository. This submission retains the starter's executable `code/` layout rather than moving working modules into `src/`.

## AI coding-tool disclosure

See [**AI_USAGE.md**](AI_USAGE.md) for how ChatGPT helped with implementation and debugging, what was checked and changed locally, and how the runtime Groq model differs from the coding assistant.
