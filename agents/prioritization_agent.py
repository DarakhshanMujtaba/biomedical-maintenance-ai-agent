import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent / "tools"))

from sql_tool import get_equipment_needing_maintenance
from prioritization_tool import rank_equipment_by_priority

from crewai.tools import tool


@tool("Get equipment ranked by maintenance priority")
def equipment_priority_tool(ward: Optional[str] = None, within_days: int = 30) -> str:
    """
    Finds equipment needing maintenance (optionally filtered by ward, within
    a given number of days), then ranks it by priority score — a formula
    combining how overdue it is, how critical the equipment type is, and how
    heavily it has been used. Returns the ranked list, highest priority first,
    with each item's computed priority_score included.
    """
    equipment = get_equipment_needing_maintenance(ward=ward, within_days=within_days)
    ranked = rank_equipment_by_priority(equipment)
    if not ranked:
        return "No equipment found matching that criteria."
    return str(ranked)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    from crewai import Agent, Task, Crew, Process, LLM

    llm = LLM(
        model="openai/gpt-oss-120b",
        provider="openai",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
    )

    prioritization_agent = Agent(
        role="Prioritization Specialist",
        goal="Rank biomedical equipment needing maintenance by real risk, so the most urgent devices are addressed first.",
        backstory=(
            "You are a senior biomedical engineer responsible for triage decisions. "
            "You never guess at priority by eye — you always use the priority ranking "
            "tool, which applies a consistent, auditable scoring formula, instead of "
            "judging by criticality or overdue-ness alone."
        ),
        tools=[equipment_priority_tool],
        llm=llm,
        verbose=True,
    )

    prioritize_task = Task(
        description=(
            "Find and rank, by priority, all ICU equipment needing maintenance "
            "within the next 30 days. List the top 5 highest priority items."
        ),
        expected_output=(
            "A ranked list (highest priority first) of up to 5 equipment items, "
            "including each device's name, ward, criticality, status, next due date, "
            "and priority score."
        ),
        agent=prioritization_agent,
    )

    crew = Crew(
        agents=[prioritization_agent],
        tasks=[prioritize_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    print("\n=== FINAL RESULT ===")
    print(result)
