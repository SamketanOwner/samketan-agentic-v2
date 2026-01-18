import google.generativeai as genai
import json

def get_architect_plan(user_query, api_key):
    # 1. Connect to the Brain
    # We use 'gemini-pro' here as it is the most stable model
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')

    # 2. The System Prompt
    system_instructions = """
    ROLE: You are the Chief Architect of Samketan AI.
    GOAL: You do NOT answer questions. You PLAN research.
    
    INSTRUCTIONS:
    Analyze the user's request. If it is complex, break it down into steps.
    
    OUTPUT FORMAT (Strict JSON):
    {
        "thought_process": "Explain why you are breaking this down...",
        "steps": [
            {"step": 1, "action": "search", "query": "The exact search query for Google"},
            {"step": 2, "action": "analyze", "target": "What to look for in the results"}
        ]
    }
    """

    # 3. Get the Plan
    try:
        response = model.generate_content(
            f"{system_instructions}\n\nUSER QUERY: {user_query}",
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        # If JSON fails, return a safe error structure
        return {"error": str(e), "thought_process": "Planning Failed", "steps": []}
