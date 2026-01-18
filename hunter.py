from duckduckgo_search import DDGS

def execute_step(step_data):
    # 1. Setup the Search Tool
    results = []
    query = step_data.get('query') or step_data.get('target')
    
    # 2. Perform the Search (The "Action")
    try:
        with DDGS() as ddgs:
            # Search for top 3 results to save time
            search_results = list(ddgs.text(query, max_results=3))
            
        # 3. Summarize findings into a simple string
        summary = ""
        for result in search_results:
            summary += f"- {result['title']}: {result['body']}\n"
            
        return f"✅ RESEARCH COMPLETE for '{query}':\n{summary}"
        
    except Exception as e:
        return f"❌ SEARCH FAILED: {str(e)}"
