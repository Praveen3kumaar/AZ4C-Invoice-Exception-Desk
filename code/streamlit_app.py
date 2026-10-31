
import json
import re
import uuid

import streamlit as st

from invoice_tool import get_invoice
from result_builder import build_result


st.set_page_config(
    page_title="AI Invoice Exception Desk",
    page_icon="📄",
    layout="wide"
)

st.title("📄 AI Invoice Exception Desk")
st.caption(
    "Kestrel Auto Components | AI-Powered AP Investigation"
)

st.info(
    "Enter an invoice number from the configured SQLite database. "
    "This interface generates an investigation recommendation only. "
    "It does not execute payments."
)


# -------------------------------
# Invoice input
# -------------------------------

with st.form("invoice_search"):
    invoice_id = st.text_input(
        "Enter Invoice Number",
        placeholder="Example: INV-20041"
    )

    submitted = st.form_submit_button(
        "🔍 Analyze Invoice",
        type="primary",
        use_container_width=True
    )


# -------------------------------
# Run investigation on submission
# -------------------------------

if submitted:
    invoice_id = invoice_id.strip().upper()

    if not invoice_id:
        st.warning("Please enter an invoice number.")

    elif not re.fullmatch(r"INV-[A-Z0-9_-]+", invoice_id):
        st.error("Please enter a valid invoice number.")

    elif get_invoice(invoice_id) is None:
        st.error(
            f"Invoice {invoice_id} was not found in the database."
        )

    else:
        case_id = f"WEB-{uuid.uuid4().hex[:8].upper()}"

        try:
            with st.spinner(
                "AI agents are investigating the invoice..."
            ):
                result = build_result(
                    case_id=case_id,
                    invoice_id=invoice_id
                )

            st.session_state["last_result"] = result
            st.session_state["last_invoice_id"] = invoice_id

        except Exception:
            st.session_state.pop("last_result", None)
            st.session_state.pop("last_invoice_id", None)

            st.error(
                "The investigation could not be completed. "
                "No payment has been authorized."
            )


# -------------------------------
# Display investigation result
# -------------------------------

if "last_result" in st.session_state:

    result = st.session_state["last_result"]
    decision = result["decision"].upper()

    st.divider()
    st.subheader("Investigation Result")

    if decision == "PAY":
        st.success("Decision: PAY — recommended")
    elif decision == "HOLD":
        st.warning("Decision: HOLD")
    else:
        st.error("Decision: ESCALATE")

    invoice_amount = result.get("amount")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Invoice Amount",
        f"₹{invoice_amount:,.2f}"
        if invoice_amount is not None
        else "Unknown"
    )

    col2.metric(
        "Reason Code",
        result["reason_code"]
    )

    col3.metric(
        "Human Review",
        "Required" if result["needs_human"] else "Not Required"
    )

    other_reasons = result.get("other_reasons", [])

    if other_reasons:
        st.subheader("Additional Exceptions")
        for reason in other_reasons:
            st.write(f"• {reason}")

    st.subheader("AI Specialist Agent Results")

    for agent in result.get("agent_results", []):
        with st.expander(
            f"{agent['agent'].title()} Agent "
            f"— {agent['recommendation']}"
        ):
            st.write(agent.get("reason", ""))

    st.subheader("Evidence Citations")

    for citation in result.get("citations", []):
        st.write(f"• {citation}")

    if result.get("evidence_errors"):
        st.error(
            "Evidence validation issues were detected. "
            "The investigation requires human attention."
        )
        st.json(result["evidence_errors"])

    st.caption(
        f"Case ID: {result['case_id']} | "
        f"Trace ID: {result['trace_id']}"
    )

    st.download_button(
        "Download Investigation JSON",
        data=json.dumps(result, indent=2),
        file_name=(
            f"{st.session_state['last_invoice_id']}_result.json"
        ),
        mime="application/json"
    )

    with st.expander("View Complete JSON Result"):
        st.json(result)
