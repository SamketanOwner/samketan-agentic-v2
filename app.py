import streamlit as st
import time
from architect import get_architect_plan
from hunter import execute_step

st.set_page_config(page_title="Samketan V2: Full Autonomy", page_icon="🤖")

st.title("Samketan V2: Autonomous Agent")
st.caption("Auto-Research System: Plan -> Search -> Result")

# CHECK FOR SECRET KEY FIRST
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("✅ API Key Loaded Securely")
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# Session State to hold the plan in memory
if 'plan' not in st.session_state:
    st.session_state['plan'] = None

user_query = st.text_area("Enter your Goal:", 
                          "Find top 3 warehouse competitors in North Karnataka and their 2026 pricing.")

# BUTTON 1: THE PLANNER
if st.button("1. Generate Plan"):
    if not api_key:
        st.error("Need API Key!")
    else:
        with st.spinner("Architect is thinking..."):
            plan = get_architect_plan(user_query, api_key)
            if "error" in plan:
                st.error(plan['error'])
            else:
                st.session_state['plan'] = plan
                st.success("Plan Created! Review below.")

# Display Plan if it exists
if st.session_state['plan']:
    plan = st.session_state['plan']
    st.subheader("🧠 The Strategy")
    st.info(plan.get('thought_process'))
    
    st.subheader("📋 Execution Steps")
    # Show steps in a clean list
    for step in plan.get('steps', []):
        st.write(f"**Step {step['step']}:** {step.get('action')} -> *{step.get('query')}*")

    st.markdown("---")
    
    # BUTTON 2: THE EXECUTOR
    if st.button("2. Execute Mission (Launch The Hunter)"):
        st.write("🚀 **Starting Autonomous Research...**")
        progress_bar = st.progress(0)
        
        all_steps = plan.get('steps', [])
        total_steps = len(all_steps)
        
        # THE LOOP (Future Tech)
        for index, step in enumerate(all_steps):
            with st.chat_message("assistant"):
                st.write(f"**Executing Step {step['step']}...**")
                
                # The Agent Acts
                result = execute_step(step)
                
                # Show Result
                st.code(result)
            
            # Update Progress
            progress_bar.progress((index + 1) / total_steps)
            time.sleep(1) # Tiny pause to be polite to the search engine
            
        st.success("Mission Complete. All data gathered.")
