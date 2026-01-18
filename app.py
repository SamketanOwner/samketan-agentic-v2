import streamlit as st
import time
from pypdf import PdfReader
from architect import get_architect_plan
from hunter import execute_step

st.set_page_config(page_title="Samketan V3: Document Intelligence", page_icon="📂")

st.title("Samketan V3: Commercial Agent")
st.caption("Now with 'Document Eyes' + 'Web Search'")

# --- SIDEBAR: SETTINGS & TOOLS ---
st.sidebar.header("⚙️ Control Panel")

# 1. API Key Logic
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("✅ API Key Loaded")
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# 2. THE NEW FEATURE: Document Reader
st.sidebar.markdown("---")
st.sidebar.header("📂 Document Reader")
uploaded_file = st.sidebar.file_uploader("Upload Tender/Invoice (PDF)", type="pdf")

pdf_text = ""
if uploaded_file is not None:
    try:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            pdf_text += page.extract_text()
        st.sidebar.success(f"✅ Read {len(reader.pages)} pages successfully!")
    except Exception as e:
        st.sidebar.error(f"Error reading PDF: {e}")

# --- MAIN SCREEN ---

# Session State
if 'plan' not in st.session_state:
    st.session_state['plan'] = None

# User Input
base_query = st.text_area("Enter your Goal:", 
                          "Analyze this tender document and tell me the qualification criteria.")

# LOGIC: Combine User Goal + PDF Text (If available)
final_query = base_query
if pdf_text:
    final_query = f"""
    CONTEXT FROM UPLOADED DOCUMENT:
    {pdf_text[:15000]} 
    
    USER GOAL: 
    {base_query}
    """
    st.info(f"📎 Attached {len(pdf_text)} characters from your PDF to this query.")

# BUTTON 1: GENERATE PLAN
if st.button("1. Generate Plan"):
    if not api_key:
        st.error("Please enter an API Key in the sidebar.")
    else:
        with st.spinner("Architect is analyzing document & planning..."):
            plan = get_architect_plan(final_query, api_key)
            
            if "error" in plan:
                st.error(plan['error'])
            else:
                st.session_state['plan'] = plan
                st.success("Plan Ready! Review below.")

# DISPLAY PLAN & EXECUTE
if st.session_state['plan']:
    plan = st.session_state['plan']
    
    st.subheader("🧠 The Strategy")
    st.info(plan.get('thought_process'))
    
    st.subheader("📋 Execution Steps")
    for step in plan.get('steps', []):
        st.write(f"**Step {step['step']}:** {step.get('action')} -> *{step.get('query') or step.get('target')}*")

    st.markdown("---")
    
    # BUTTON 2: EXECUTE
    if st.button("2. Execute Mission"):
        st.write("🚀 **Starting Research...**")
        progress_bar = st.progress(0)
        
        all_steps = plan.get('steps', [])
        total_steps = len(all_steps)
        
        for index, step in enumerate(all_steps):
            with st.chat_message("assistant"):
                st.write(f"**Executing Step {step['step']}...**")
                result = execute_step(step)
                st.code(result)
            
            progress_bar.progress((index + 1) / total_steps)
            time.sleep(1)
            
        st.success("Mission Complete!")
