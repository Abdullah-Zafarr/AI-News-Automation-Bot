from __future__ import annotations

import os

from crewai import Agent, Crew, LLM, Process, Task

from .tools import DiscordBotTool, NewsFetcherTool, SheetsLoggerTool, SlackBotTool, SummarizerTool


def _agent_llm(provider: str | None = None) -> LLM:
    """Create a Gemini-first CrewAI LLM, or explicitly select the Groq fallback."""
    model = os.getenv("CREWAI_MODEL", "gemini/gemini-3-flash-preview")
    if provider != "groq" and os.getenv("GEMINI_API_KEY") and not model.startswith("groq/"):
        return LLM(model=model, api_key=os.environ["GEMINI_API_KEY"], temperature=0.1)

    groq_model = model.removeprefix("groq/") if model.startswith("groq/") else os.getenv(
        "GROQ_MODEL", "llama-3.1-8b-instant"
    )
    return LLM(
        model=f"openai/{groq_model}",
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
        temperature=0.1,
    )


def build_crew(provider: str | None = None) -> Crew:
    """Build the required sequential multi-agent CrewAI workflow."""
    llm = _agent_llm(provider)
    # CrewAI needs turns to choose a tool, consume its result, and return a
    # final task answer. Three is the smallest reliable cap for this workflow.
    agent_options = {"llm": llm, "allow_delegation": False, "verbose": False, "max_iter": 3}
    fetcher = Agent(
        role="News Researcher",
        goal="Find recent, relevant, and diverse news for the requested topics.",
        backstory="You are a careful researcher who preserves source links and avoids duplicates.",
        tools=[NewsFetcherTool()],
        **agent_options,
    )
    editor = Agent(
        role="News Editor",
        goal="Turn raw news search results into short, factual structured summaries.",
        backstory="You are a precise editor who never invents information not present in the input.",
        tools=[SummarizerTool()],
        **agent_options,
    )
    notification_provider = os.getenv("NOTIFICATION_PROVIDER", "slack").lower()
    publisher_tool = DiscordBotTool() if notification_provider == "discord" else SlackBotTool()
    publisher_name = "Discord Publisher" if notification_provider == "discord" else "Slack Publisher"
    publisher = Agent(
        role=publisher_name,
        goal="Publish every valid new summary clearly to the configured notification channel.",
        backstory="You format concise updates that are easy for a team to scan.",
        tools=[publisher_tool],
        **agent_options,
    )
    archivist = Agent(
        role="News Archive Manager",
        goal="Log successfully published news to Google Sheets without duplicates.",
        backstory="You maintain an accurate and auditable news archive.",
        tools=[SheetsLoggerTool()],
        **agent_options,
    )

    fetch_task = Task(
        description=(
            "Call Custom News Fetcher exactly once for these topics: {topics}. "
            "Use the default limit of {limit_per_topic} stories per topic. "
            "Return only the JSON result from the tool."
        ),
        expected_output="A JSON array of normalized article objects.",
        agent=fetcher,
    )
    summarize_task = Task(
        description=(
            "Call Intelligent News Summarizer exactly once using the previous task's JSON. "
            "Return only its JSON object and do not rewrite the summaries yourself."
        ),
        expected_output="A JSON object containing a summaries array.",
        agent=editor,
        context=[fetch_task],
    )
    publish_task = Task(
        description=(
            "Call the configured notification publisher exactly once using the previous task's JSON. "
            "Return only its JSON result with posted and failed arrays."
        ),
        expected_output="A JSON object containing posted and failed arrays.",
        agent=publisher,
        context=[summarize_task],
    )
    log_task = Task(
        description=(
            "Call Google Sheets News Logger exactly once using the previous task's JSON. "
            "Return only its JSON result with logged and skipped counts."
        ),
        expected_output="A JSON object containing logged and skipped values.",
        agent=archivist,
        context=[publish_task],
    )
    return Crew(
        agents=[fetcher, editor, publisher, archivist],
        tasks=[fetch_task, summarize_task, publish_task, log_task],
        process=Process.sequential,
        verbose=False,
    )
