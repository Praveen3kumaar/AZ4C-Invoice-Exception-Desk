# Invoice Exception Desk — Architecture

The runtime uses hybrid dynamic routing: mandatory deterministic checks establish evidence, while a Groq LLM proposes relevant specialist AI agents. Python routing safety rules prevent critical exception areas from being skipped.

```mermaid
flowchart TD
    U[User: Streamlit or CLI case] --> RB[Result Builder]
    RB --> OR[Orchestrator]
    OR --> IT[Invoice Tool]
    IT --> DB[(SQLite: ap.sqlite)]
    OR --> PC[Mandatory Python prechecks]
    PC --> MT[Matching Tool]
    PC --> DT[Duplicate Tool]
    PC --> RT[Risk Tool]
    MT --> AT[Agreement Tool]
    MT --> DB
    DT --> DB
    RT --> DB
    AT --> DOC[Signed price agreements]
    PC --> RL[Groq: routing proposal]
    RL --> G[Python routing safety guard]
    PC --> G
    G --> MA[Matching Agent, if selected]
    G --> DA[Duplicate Agent, if selected]
    G --> RA[Risk Agent, if selected]
    MA --> MT
    DA --> DT
    RA --> RT
    MA --> LLM[Groq model for specialist explanations]
    DA --> LLM
    RA --> LLM
    MA --> V[Validate agent evidence and apply AP policy]
    DA --> V
    RA --> V
    PC --> V
    V --> RB
    RB --> JSON[Structured JSON result]
    JSON --> UI[Streamlit displays result]
    JSON --> CLI[CLI run: save result]
    CLI --> ERP[Local mock ERP and draft hold notice]
```

The Mermaid diagram is rendered in GitHub Markdown. All three Python prechecks execute on each valid invoice; the specialist LLM agents execute only when selected. The mock ERP and notice output are local simulations, not real financial actions.
