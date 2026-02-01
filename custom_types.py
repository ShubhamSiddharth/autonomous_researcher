import pydantic
from typing import List, Optional

# --- 1. The Input (What the user wants) ---
class ResearchRequest(pydantic.BaseModel):
    topic: str
    depth: int = 3  # How many websites to read (default 3)

# --- 2. The Tool Output (What Tavily gives us) ---
class SearchResultItem(pydantic.BaseModel):
    title: str
    url: str
    content: str  # The actual text content of the website
    score: float  # How relevant is this result?

class SearchResponse(pydantic.BaseModel):
    results: List[SearchResultItem]
    query: str

# --- 3. The Agent's State (Memory) ---
# As the agent works, it needs to keep notes.
class AgentState(pydantic.BaseModel):
    topic: str
    search_queries: List[str] = []
    gathered_facts: List[str] = []
    status: str = "started" # "searching", "reading", "writing", "completed"

# --- 4. The Final Product (The Report) ---
class ResearchReport(pydantic.BaseModel):
    topic: str
    summary: str
    key_findings: List[str]
    references: List[str] # List of URLs used
    full_report_markdown: str # The pretty report