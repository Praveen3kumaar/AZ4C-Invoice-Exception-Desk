# Invoice Exception Desk

**AZ4C AI Agent Developer Assignment — Associate Engineer | Use Case 1**

This project is an AI-powered invoice investigation system for the Accounts Payable team at Kestrel Auto Components. It examines supplier invoices using purchase orders, goods receipts, payment history, vendor details, GST records, and approved price agreements.

The system produces an evidence-backed recommendation to **PAY**, **HOLD**, or **ESCALATE** an invoice. It does not execute real payments.

## Set up and run

**Prerequisites:** Python 3.12, a Groq API key, and the supplied AZ4C Use Case 1 data pack.

Clone the repository and open the `code` directory.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

The dependency file must contain the tested versions of the project's packages, including Groq, python-dotenv, jsonschema, and Streamlit.

Create a `.env` file inside the `code` directory:

```env
GROQ_API_KEY=your_groq_api_key
DATA_DIR=D:/path/to/extracted/data-pack
```

`DATA_DIR` must point to the extracted data-pack root containing the SQLite database, policy documents, agreements, samples, and schema.

**Run one invoice case:**

```powershell
python -m app run --case D:/path/to/data-pack/samples/UC1-S01.json --out out/UC1-S01.json
```

**Run the Streamlit interface:**

```powershell
python -m streamlit run streamlit_app.py
```

**Evaluate test cases:**

```powershell
python -m app eval --cases tests/cases
```

**Validate JSON outputs:**

```powershell
python validate_schema.py
```

The CLI writes simulated ERP decisions, while Streamlit displays investigation results without updating the mock ERP.

The supplied data pack and actual API keys must not be committed to GitHub.

## Design

The system consists of one AI Orchestrator and three specialist AI agents.

**Orchestrator (`orchestrator.py`)**

The Orchestrator receives the invoice ID, retrieves invoice information, performs mandatory Python prechecks, chooses specialist investigations through Groq-assisted routing, validates the specialist findings, and applies company AP policy to determine the final decision.

**Matching Agent (`matching_agent.py`)**

Checks invoice quantities and prices against purchase orders and goods receipts. It also considers valid signed vendor price agreements.

**Duplicate Agent (`duplicate_agent.py`)**

Investigates potential duplicate invoices and existing payment records.

**Risk Agent (`risk_agent.py`)**

Investigates GST mismatches, blocked vendors, and recent vendor bank-account changes.

### Dynamic routing

The project uses hybrid, evidence-driven dynamic routing:

1. All three deterministic Python tools first check the invoice.
2. Their findings are sent to the Groq Orchestrator.
3. Groq proposes which AI specialist agents should investigate.
4. A Python safety guard ensures that no specialist required by detected exceptions is skipped.
5. Only the selected AI specialist agents execute.
6. Their recommendations are validated against Python evidence before applying the final AP policy.

For example:

| Invoice | AI agents executed | Decision |
|---|---|---|
| INV-20129 | Matching | PAY |
| INV-20041 | Matching | HOLD |
| INV-29304 | Duplicate | ESCALATE |
| INV-20339 | Duplicate + Risk | ESCALATE |
| INV-20541 | Duplicate + Risk | ESCALATE |

The architecture diagram is available in [docs/architecture.md](code/docs/architecture.md).

## Tools

The specialist agents use deterministic Python tools to retrieve and validate business data.

| Tool | Input | Output |
|---|---|---|
| `invoice_tool.py` | Invoice, PO, vendor, and other record IDs | SQLite business records |
| `matching_tool.py` | Invoice ID | Matching status and quantity/price exceptions |
| `duplicate_tool.py` | Invoice ID | Duplicate status and payment evidence |
| `risk_tool.py` | Invoice ID | GST and vendor-risk findings |
| `agreement_tool.py` | Vendor, item, and date | Applicable signed price revision |
| `llm_client.py` | Prompt and response requirements | Structured Groq response |

The main matching, duplicate, and risk tools return statuses and evidence. Tool results are checked by the Orchestrator before finalizing the decision.

If a tool fails or returns incomplete evidence, the system avoids issuing an unsupported payment recommendation.

## Models used and why

The application uses **`openai/gpt-oss-120b` through the Groq API**.

The same model is used by the Orchestrator and all three specialist AI agents.

It was selected to provide LLM-based routing, structured JSON recommendations, and explanations of verified invoice evidence without hosting a model locally.

The LLM supports interpretation and investigation planning. Deterministic Python tools remain responsible for factual checks, numerical comparisons, and financial policy enforcement.

Using a single model also simplifies integration and maintenance for this assignment prototype. The implementation has not been benchmarked against multiple models.

## Failure handling

The application includes several safeguards:

- **Rate limits:** Groq API calls use retries to handle temporary failures.
- **Invalid LLM responses:** JSON responses are checked for required fields and permitted values.
- **Incorrect AI recommendations:** The Orchestrator validates selected agents' recommendations against deterministic Python