import logging
import os
import json
from fastapi import FastAPI
import inngest
import inngest.fast_api
from dotenv import load_dotenv
from google import genai

# Import our custom tools and types
from tools import perform_web_search
from custom_types import ResearchRequest, ResearchReport, AgentState

load_dotenv()

# --- SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Inngest
inngest_client = inngest.Inngest(
    app_id="research_agent",
    logger=logger,
    is_production=False,
)


# --- THE AGENT WORKFLOW ---
@inngest_client.create_function(
    fn_id="agent-deep-research",
    trigger=inngest.TriggerEvent(event="agent/start_research"),
    # --- FIX: Use inngest.Cancel() instead of TriggerEvent ---
    cancel=[inngest.Cancel(event="agent/cancel_research")],
)
async def deep_research_workflow(ctx: inngest.Context):
    # 1. GET INPUT
    topic = ctx.event.data["topic"]
    logger.info(f"🤖 AGENT: Starting research on '{topic}'")

    # --- STEP 1: PLAN (Generate Search Queries) ---
    def _plan_research():
        prompt = (
            f"You are a Senior Research Assistant. Your goal is to research: '{topic}'.\n"
            "Generate 3 specific, distinct search queries to gather comprehensive facts.\n"
            "Return ONLY the 3 queries, separated by newlines. Do not add numbers or quotes."
        )

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        # Clean up the output (split by newlines and remove empty strings)
        queries = [q.strip() for q in response.text.split('\n') if q.strip()]
        return queries[:3]  # Ensure we only take top 3

    # Run Step 1
    search_queries = await ctx.step.run("plan-research", _plan_research)

    # --- STEP 2: ACT (Execute Searches) ---
    def _execute_search(query):
        # We use our tool from tools.py
        return perform_web_search(query).model_dump()

    collected_context = []

    # Loop through each query and search (Inngest handles the loop state!)
    for i, query in enumerate(search_queries):
        # We give each step a unique ID based on the loop index
        search_result = await ctx.step.run(f"search-step-{i}", lambda: _execute_search(query))

        # Format the result for the AI to read later
        for item in search_result["results"]:
            collected_context.append(
                f"Source: {item['title']}\nURL: {item['url']}\nContent: {item['content']}\n---"
            )

    # --- STEP 3: WRITE (Synthesize Report) ---
    def _write_report(context_list):
        context_block = "\n".join(context_list)

        prompt = (
            f"You are a professional technical writer. Write a deep-dive report on: '{topic}'.\n\n"
            f"Use the following gathered context to answer:\n{context_block}\n\n"
            "Requirements:\n"
            "1. Start with an Executive Summary.\n"
            "2. Use bullet points for Key Findings.\n"
            "3. Cite specific sources (URLs) where possible.\n"
            "4. Format in clean Markdown.\n"
            "5. If the context is empty, state that no information was found."
        )

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text

    final_report = await ctx.step.run("write-report", lambda: _write_report(collected_context))

    # Return the final structure
    return {
        "topic": topic,
        "final_report": final_report,
        "sources_used": len(collected_context)
    }


# --- SERVER SETUP ---
app = FastAPI()
inngest.fast_api.serve(app, inngest_client, [deep_research_workflow])