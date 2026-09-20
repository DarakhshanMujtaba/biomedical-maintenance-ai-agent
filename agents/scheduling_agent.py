import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent / "tools"))

from scheduling_tool import propose_maintenance_schedule

from crewai.tools import tool


@tool("Propose a maintenance schedule for top-priority equipment")
def propose_schedule_tool(top_n: int = 5, ward: Optional[str] = None, within_days: int = 30) -> str:
    """
    Finds the top N highest-priority equipment items needing maintenance
    (optionally filtered by ward, within a given number of days), assigns
    each to an available engineer whose specialty matches the equipment
    type, proposes a distinct date for each, and writes a draft .ics
    calendar file (never a real calendar event — only a draft for human
    review). Returns which devices were successfully scheduled and to
    whom, and flags any devices that could not be scheduled because no
    matching engineer was available.
    """
    result = propose_maintenance_schedule(top_n=top_n, ward=ward, within_days=within_days)
    if not result["scheduled"] and not result["unassigned"]:
        return "No equipment found matching that criteria."
    return str(result)


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

    scheduling_agent = Agent(
        role="Scheduling Coordinator",
        goal="Propose maintenance appointments for the most urgent equipment, matching each device to a qualified, available engineer.",
        backstory=(
            "You coordinate maintenance scheduling for a hospital's biomedical "
            "engineering team. You never invent an engineer assignment yourself — "
            "you always use the scheduling tool, which enforces real specialty "
            "and availability constraints. You clearly report anything that "
            "could not be scheduled, since that needs human follow-up."
        ),
        tools=[propose_schedule_tool],
        llm=llm,
        verbose=True,
    )

    schedule_task = Task(
        description=(
            "Schedule the top 5 highest-priority ICU equipment items needing "
            "maintenance within the next 30 days. Propose an engineer and date "
            "for each."
        ),
        expected_output=(
            "A list of each device scheduled, its assigned engineer, and proposed "
            "date. If any devices could not be scheduled, clearly list them and "
            "explain why."
        ),
        agent=scheduling_agent,
    )

    crew = Crew(
        agents=[scheduling_agent],
        tasks=[schedule_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    print("\n=== FINAL RESULT ===")
    print(result)
