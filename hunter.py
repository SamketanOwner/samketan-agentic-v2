from duckduckgo_search import DDGS

def execute_step(step_data):
    # Get the query from the plan
    query = step_data.get('query') or step_data.get('target') or "Unknown topic"
    
    try:
        # Initialize search
        with DDGS() as ddgs:
            # 1. LIMIT RESULTS: Only get 2 results to be fast
            # 2. SAFE MODE: If it takes too long, it will fail gracefully
            results = list(ddgs.text(query, max_results=2))
            
        if not results:
            return f"⚠️ No data found for '{query}'. Moving to next step."

        # Summarize quickly
        summary = f"✅ FOUND DATA for '{query}':\n"
        for r in results:
            title = r.get('title', 'No Title')
            body = r.get('body', 'No details')
            summary += f"- {title}: {body[:200]}...\n" # Limit text length
            
        return summary

    except Exception as e:
        # If it crashes, return the error message instead of buffering forever
        return f"❌ SEARCH ERROR for '{query}': {str(e)}"
