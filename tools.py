import os
from dotenv import load_dotenv
from tavily import TavilyClient
from custom_types import SearchResponse, SearchResultItem

# Load the API keys from .env
load_dotenv()

# Initialize the Tavily Client (The Search Engine)
# It automatically looks for "TAVILY_API_KEY" in your environment variables
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def perform_web_search(query: str, max_results: int = 3) -> SearchResponse:
    """
    Searches the web for a specific query and returns structured data.
    """
    print(f"🔎 TOOLS: Searching the web for: '{query}'...")

    try:
        # 1. Call the API
        # search_depth="advanced" means it reads the content, not just the title.
        raw_response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_raw_content=False  # We just want the clean text
        )

        # 2. Parse the messy JSON into our clean "Blueprints"
        clean_results = []

        # The API returns a dict with a key 'results' which is a list
        for item in raw_response.get("results", []):
            clean_results.append(
                SearchResultItem(
                    title=item.get("title", "No Title"),
                    url=item.get("url", ""),
                    content=item.get("content", "")[:1000],  # Limit to 1k chars to save tokens
                    score=item.get("score", 0.0)
                )
            )

        # 3. Return the structured object
        return SearchResponse(results=clean_results, query=query)

    except Exception as e:
        print(f"⚠️ TOOLS ERROR: {e}")
        # Return an empty response so the Agent doesn't crash
        return SearchResponse(results=[], query=query)


# --- QUICK TEST BLOCK ---
# If you run this file directly (python tools.py), it will test the search.
if __name__ == "__main__":
    print("Testing Search Tool...")
    test_result = perform_web_search("Latest advancements in Solid State Batteries 2024")

    for res in test_result.results:
        print(f"\n--- {res.title} ---")
        print(f"URL: {res.url}")
        print(f"Snippet: {res.content[:150]}...")