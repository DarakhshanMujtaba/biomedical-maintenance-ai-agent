import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent / "tools"))

from sql_tool import get_equipment_needing_maintenance

from crewai.tools import tool


@tool("Get equipment needing maintenance")
def equipment_needing_maintenance_tool(ward: Optional[str] = None, within_days: int = 30) -> str:
    """
    Returns equipment that needs maintenance within a given number of days,
    optionally filtered to a specific ward (e.g. 'ICU'). Each result includes
    the equipment name, type, ward, criticality, status, and next due date.
    """
    results = get_equipment_needing_maintenance(ward=ward, within_days=within_days)
    if not results:
        return "No equipment found matching that criteria."
    return str(results)


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

    equipment_monitor_agent = Agent(
        role="Equipment Monitor",
        goal="Find biomedical equipment that needs maintenance, filtered by ward and time window.",
        backstory=(
            "You work in a hospital's biomedical engineering department. "
            "You are meticulous about tracking which equipment needs servicing, "
            "and you always use the equipment database to get accurate, up-to-date answers "
            "instead of guessing."
        ),
        tools=[equipment_needing_maintenance_tool],
        llm=llm,
        verbose=True,
    )

    find_equipment_task = Task(
        description="Show all ICU equipment that needs maintenance within the next 30 days.",
        expected_output=(
            "A clear list of the matching equipment, including each device's name, "
            "type, ward, criticality, status, and next due date."
        ),
        agent=equipment_monitor_agent,
    )

    crew = Crew(
        agents=[equipment_monitor_agent],
        tasks=[find_equipment_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    print("\n=== FINAL RESULT ===")
    print(result)
