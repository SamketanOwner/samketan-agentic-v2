import google.generativeai as genai
import json

def get_architect_plan(user_query, api_key):
    # 1. Connect and Auto-Detect Model
    genai.configure(api_key=api_key)
    
    # SYSTEM: Find a model that actually exists for this user
    active_model = "models/gemini-1.5-flash" # Default fallback
    try:
        # List all models available to your specific API Key
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Prefer a Flash model if available (faster)
                if 'flash' in m.name:
                    active_model = m.name
                    break
                # Otherwise keep the first valid one found
                active_model = m.name
    except Exception as e:
        return {"error": f"API Key Error: {str(e)}", "steps": []}

    # 2. Configure the Brain with the found model
    model = genai.GenerativeModel(active_model)

    # 3. The Planner Prompt
    system_instructions = """
    ROLE: Chief Architect of Samketan AI.
    TASK: Break down this complex user query into a JSON execution plan.
    FORMAT: JSON only.
    
    OUTPUT STRUCTURE:
    {
        "thought_process": "Reasoning...",
        "steps": [
            {"step": 1, "action": "search", "query": "search term"},
            {"step": 2, "action": "analyze", "target": "specific data"}
        ]
    }
    """

    # 4. Execute
    try:
        response = model.generate_content(
            f"{system_instructions}\n\nUSER QUERY: {user_query}",
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"Model {active_model} failed: {str(e)}", "thought_process": "Error", "steps": []}
