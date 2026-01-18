import streamlit as st
from architect import get_architect_plan

# Page Setup
st.set_page_config(page_title="Samketan V2: Agentic", page_icon="🧠")

st.title("Samketan V2: The Architect Agent")
st.caption("Experimental Autonomous Planning System")

# API Key Input (Sidebar)
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
st.sidebar.info("Get your free key at: aistudio.google.com")

# User Input
user_query = st.text_area("Enter a complex goal for the agent:", 
                          "Find the best cement suppliers in Kalaburagi for 2026 and compare prices.")

if st.button("Generate Plan"):
    if not api_key:
        st.error("Please enter an API Key in the sidebar.")
    else:
        with st.spinner("The Architect is thinking..."):
            plan = get_architect_plan(user_query, api_key)

            if "error" in plan:
                st.error(f"Error: {plan['error']}")
            else:
                st.subheader("🧠 The Reasoning")
                st.info(plan.get('thought_process'))

                st.subheader("📋 The Execution Plan")
                for step in plan.get('steps', []):
                    st.write(f"**Step {step['step']} ({step['action']}):** {step.get('query') or step.get('target')}")

                st.success("Plan Ready! (Next update will auto-execute these steps).")
