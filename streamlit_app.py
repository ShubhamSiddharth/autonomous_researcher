import asyncio
import time
import streamlit as st
import inngest
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
st.set_page_config(page_title="Autonomous Researcher", page_icon="🕵️", layout="wide")

API_BASE = os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="research_agent", is_production=False)


# --- HELPER FUNCTIONS ---
async def start_research(topic: str) -> str:
    """Sends the research task to Inngest and returns the Event ID."""
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="agent/start_research",
            data={"topic": topic}
        )
    )
    return result[0]  # Return the Event IDs


def get_run_status(event_id: str):
    """Polls Inngest to check if the agent is done."""
    url = f"{API_BASE}/events/{event_id}/runs"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        runs = data.get("data", [])

        if not runs:
            return "waiting", None

        run = runs[0]
        status = run.get("status")
        output = run.get("output")

        return status, output
    except Exception as e:
        return "error", str(e)


# --- THE UI ---
st.title("🕵️ Autonomous Deep Researcher")
st.caption("Powered by Gemini 1.5 & Tavily Search")

with st.sidebar:
    st.header("Instructions")
    st.info(
        "1. Enter a complex topic (e.g., 'Future of solid state batteries').\n"
        "2. The Agent will plan a strategy.\n"
        "3. It will search the web for multiple angles.\n"
        "4. It will read the content and write a report."
    )
    st.warning("⚠️ This process takes 30-60 seconds because the Agent is doing real work!")

# Input Form
with st.form("research_form"):
    topic = st.text_input("What do you want to research?",
                          placeholder="e.g. Latest advancements in nuclear fusion 2024")
    submitted = st.form_submit_button("Start Research")

if submitted and topic:
    st.success(f"Task received! Agent is starting research on: '{topic}'")

    # 1. Trigger the Agent
    event_id = asyncio.run(start_research(topic))

    # 2. Polling Loop with Progress Bar
    progress_bar = st.progress(0, text="Agent is planning...")
    status_text = st.empty()

    start_time = time.time()

    while True:
        status, output = get_run_status(event_id)

        # Update UI based on status
        if status in ["Running", "InProgress"]:
            # Fake progress update just to show activity
            elapsed = time.time() - start_time
            # Slowly fill bar up to 80% while waiting
            fake_progress = min(0.8, elapsed / 60)
            progress_bar.progress(fake_progress, text=f"Agent is working... (Status: {status})")

        elif status == "Completed":
            progress_bar.progress(1.0, text="Research Completed!")

            # Display the Result
            st.divider()
            st.subheader(f"📄 Report: {output.get('topic')}")

            # The Report (Markdown)
            st.markdown(output.get("final_report", "No report generated."))

            # Metadata
            st.caption(f"Sources Analyzed: {output.get('sources_used')}")
            break

        elif status in ["Failed", "Cancelled"]:
            st.error(f"Agent failed. Status: {status}")
            break

        time.sleep(1)  # Poll every second