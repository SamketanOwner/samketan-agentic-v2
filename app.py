import streamlit as st
import time
import google.generativeai as genai
from pypdf import PdfReader
from architect import get_architect_plan
from hunter import execute_step

st.set_page_config(page_title="Samketan V3: Hybrid Agent", page_icon="🧠")

st.title("Samketan V3: Universal Agent 🌍")
st.caption("Auto-Switching: Web Search ↔️ Document Reading")

# --- SIDEBAR: SETTINGS ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("✅ API Key Loaded")
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# --- SIDEBAR: DOC READER ---
st.sidebar.markdown("---")
st.sidebar.header("📂 Document Intelligence")
uploaded_file = st.sidebar.file_uploader("Upload PDF (Tender/Invoice/Report)", type="pdf")

pdf_context = ""
if uploaded_file is not None:
    try:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            pdf_context += page.extract_text()
        st.sidebar.success(f"✅ Loaded {len(reader.pages)} pages.")
    except Exception as e:
        st.sidebar.error(f"Error reading PDF: {e}")

# --- INTERNAL BRAIN FUNCTION ---
def ask_the_brain(task, context, key):
    """Uses Gemini to analyze the PDF directly instead of searching Google."""
    genai.configure(api_key=key)
    # Smart Model Selection
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
    prompt = f"""
    DOCUMENT CONTENT:
    {context[:20000]} 
    
    TASK: {task}
    
    INSTRUCTION: Provide a clear, direct answer based ONLY on the document above.
    """
    try:
        response = model.generate_content(prompt)
        return f"✅ **ANALYSIS COMPLETE:**\n\n{response.text}"
    except Exception as e:
        return f"❌ Analysis Failed: {str(e)}"

# --- MAIN APP ---
if 'plan' not in st.session_state:
    st.session_state['plan'] = None

user_goal = st.text_area("Enter your Goal:", 
                          "Summarize this project report and list all the costs.")

# 1. GENERATE PLAN
if st.button("1. Generate Plan"):
    if not api_key:
        st.error("Need API Key!")
    else:
        # Combine PDF context with user goal for the Architect
        full_query = user_goal
        if pdf_context:
            full_query = f"CONTEXT FROM PDF:\n{pdf_context[:10000]}\n\nUSER GOAL: {user_goal}"
            
        with st.spinner("Architect is planning..."):
            plan = get_architect_plan(full_query, api_key)
            if "error" in plan:
                st.error(plan['error'])
            else:
                st.session_state['plan'] = plan
                st.success("Plan Created!")

# 2. EXECUTE PLAN
if st.session_state['plan']:
    plan = st.session_state['plan']
    
    st.subheader("📋 The Strategy")
    for step in plan.get('steps', []):
        st.write(f"**Step {step['step']} ({step['action']}):** {step.get('query') or step.get('target')}")
    
    st.markdown("---")
    
    if st.button("2. Execute Mission"):
        st.write("🚀 **Starting Hybrid Execution...**")
        progress_bar = st.progress(0)
        steps = plan.get('steps', [])
        
        for i, step in enumerate(steps):
            action_type = step.get('action', '').lower()
            query = step.get('query') or step.get('target')
            
            with st.chat_message("assistant"):
                st.write(f"**Step {step['step']}: {action_type.upper()}**")
                
                # --- THE SMART SWITCH ---
                # If action is 'search', use Hunter (Google).
                # If action is 'analyze', 'summarize', 'extract', use Brain (PDF).
                if "search" in action_type and not pdf_context:
                    # No PDF? Must search web.
                    result = execute_step(step)
                elif "search" in action_type and "google" in query.lower():
                    # Explicitly asked to search? Use Hunter.
                    result = execute_step(step)
                else:
                    # Default: If we have a PDF, assume it's an analysis task
                    if pdf_context:
                        result = ask_the_brain(query, pdf_context, api_key)
                    else:
                        # Fallback to search if no PDF exists
                        result = execute_step(step)
                
                st.markdown(result)
            
            progress_bar.progress((i + 1) / len(steps))
            time.sleep(1)
            
        st.success("Mission Complete!")
