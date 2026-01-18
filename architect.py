import google.generativeai as genai
import json

def get_architect_plan(user_query, api_key):
    # 1. Connect and Auto-Detect Model
    genai.configure(api_key=api_key)
    
    # Auto-find the best available model
    active_model = "gemini-pro"
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name:
                    active_model = m.name
                    break
                active_model = m.name
    except:
        pass

    model = genai.GenerativeModel(active_model)

    # 2. THE UNIVERSAL PROMPT (The "All-Rounder" Logic)
    system_instructions = """
    ROLE: Chief Strategist of Samketan AI.
    
    YOUR CAPABILITY:
    You are not just a researcher. You adapt to the DOMAIN of the user's request:
    
    1. IF "POLITICS/TRENDS":
       - Strategy: Focus on "Real-time" keywords. Search for 'Twitter trends', 'Latest news', 'Viral hashtags'.
       - Action: Look for 'Who is trending', 'Public sentiment', 'Controversies'.
       
    2. IF "BUSINESS/SURVEY":
       - Strategy: Focus on "Data" and "Competitors".
       - Action: Plan a survey structure or find market gaps.
       
    3. IF "JOBS/CAREER":
       - Strategy: Focus on "Skills" and "Openings".
       - Action: Search specific job portals (Naukri, LinkedIn) and skill requirements.

    OUTPUT FORMAT (Strict JSON):
    {
        "thought_process": "Identify the domain (Politics/Business/etc) and explain the strategy...",
        "steps": [
            {"step": 1, "action": "search", "query": "Specific search query"},
            {"step": 2, "action": "search", "query": "Another angle to search"},
            {"step": 3, "action": "analyze", "target": "What to conclude from the data"}
        ]
    }
    """

    # 3. Execute
    try:
        response = model.generate_content(
            f"{system_instructions}\n\nUSER QUERY: {user_query}",
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e), "thought_process": "Planning Failed", "steps": []}
