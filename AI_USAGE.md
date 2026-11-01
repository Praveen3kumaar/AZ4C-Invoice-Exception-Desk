# How I used AI coding tools

**Project:** AI Invoice Exception Desk — AZ4C Associate Engineer Assignment, Use Case 1

## AI development assistant used

I used **ChatGPT** as a coding and learning assistant while developing this project. It helped me:

- Understand the assignment requirements, invoice exception workflow and the supplied SQLite/data-pack structure.
- Plan the Orchestrator, three specialist agents, Python tools, evidence-validation checks, Streamlit interface and mock ERP integration.
- Draft and improve Python functions, Groq prompts, test utilities and project documentation.
- Debug environment setup, SQL/data access, API issues, dynamic agent routing, evaluation logic and incorrect specialist recommendations.
- Create additional local test cases and a focused unit test for specialist-agent retry behavior.

I used **ChatGPT for development assistance**, not as the runtime invoice decision engine.

## Runtime AI model and its role

The application calls **`openai/gpt-oss-120b` through the Groq API** for inference. The model is not hosted or trained locally.

- The **Orchestrator LLM** examines an invoice summary and Python precheck findings and proposes which specialists should investigate.
- The selected **Matching, Duplicate and Risk AI agents** interpret results from their Python evidence tools and return structured recommendations and explanations.
- **Python** determines mandatory specialist coverage, validates agent findings, applies AP policy priority, assembles output fields and prevents unsupported automatic payment recommendations.

The LLM does not connect directly to the SQLite database or authorize live payments. It receives relevant evidence assembled by the program.

## What I checked or changed myself

I ran the project locally and reviewed the actual tool outputs, agent selections, final JSON results and mock ERP files. In particular:

1. **Changed fixed routing to dynamic routing:** An early implementation called all three AI specialists for every invoice. I updated the design so the three **Python prechecks** always run, while the LLM calls only the specialist(s) relevant to the case. A Python routing guard still adds any specialists required by detected exceptions.
2. **Corrected the local evaluator:** The earlier scorer incorrectly assumed all three AI specialists must always execute. I updated it to evaluate the dynamically selected agents while retaining comparisons of decisions, reason codes, amounts, citations and human-review flags.
3. **Implemented and verified evidence-based specialist retries:** When a specialist's answer contradicts verified tool evidence, the Orchestrator retries that specialist **once**, validates its second answer, and safely escalates if it remains incorrect. I ran **two simulated unit tests**: one in which the second answer corrected the mistake and one in which both answers were wrong. **Both passed.**
4. **Reran the full test suite:** On **November 1, 2026**, after the retry change, `python -m app eval --cases tests/cases` passed **13/13 known local cases** with a **100.0% local score**; `python validate_schema.py` passed **13/13 outputs** with zero schema failures.
5. **Checked operational outputs:** I verified local model-call logging, confirmed log exclusion from Git, ran a HOLD scenario, inspected the draft correction notice, and inspected mock ERP records for PAY, HOLD and ESCALATE. I checked that unchanged repeat decisions are deliberately not appended twice.
6. **Reviewed repository safety:** I kept `.env`, API secrets, supplied data-pack files, local logs and generated mock outputs out of the committed source files.

## What the AI suggested versus what governs the decision

ChatGPT helped write and troubleshoot the code, but its suggestions were checked through local execution, expected-answer comparisons and JSON Schema validation. At runtime, Groq model recommendations are **not** treated as authoritative financial facts. Python tools establish evidence from the supplied dataset and signed agreements; the Orchestrator checks agent outputs against that evidence before the final decision.

The system uses **hybrid evidence-driven routing**: the LLM proposes a specialist plan, while deterministic Python safeguards ensure relevant exceptions are investigated. The retry mechanism re-calls a specialist with its existing prompt; it does **not** currently provide custom corrective feedback in a revised prompt.

## Logging and error handling

`llm_client.py` writes local model-call metadata to `code/llm_calls.jsonl`, including timestamp, model, status, token usage and duration. The file is **not committed**. It is intended for development troubleshooting and does not explicitly attribute calls to a named agent. Failed or malformed AI responses are handled through API/response logic and Orchestrator checks; unresolved specialist errors lead to escalation rather than unsupported payment.

## Testing boundaries and limitations

- The **13/13, 100%** figure is the project's **local** evaluation against known cases; it is **not** the company's hidden-test result or a guarantee of repeatability under all API conditions.
- The service depends on Groq API availability and rate limits; earlier development logs include failed calls.
- The application works with invoice IDs in the supplied dataset and does not extract arbitrary new scanned invoices or PDFs.
- Only the **CLI `run` path** writes mock ERP decisions. Streamlit is a display/review interface.
- The ERP records and hold notices are **local simulations**. No payment is released and no actual email is sent.
- Part B interactive approvals, restartable runs, concurrent agent execution, and Part C production features are **not implemented**.
- The supplied vendor covering-email collection is not claimed as a comprehensive automated email-processing workflow.

## Responsibility

ChatGPT assisted with code drafts, reasoning, test design and documentation. I reviewed and revised the implementation, executed tests locally, examined outputs, corrected the routing and retry logic, and take responsibility for understanding and explaining the submitted work and its limitations.
