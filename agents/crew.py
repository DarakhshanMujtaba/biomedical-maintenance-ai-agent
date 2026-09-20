import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from equipment_monitor_agent import equipment_needing_maintenance_tool
from prioritization_agent import equipment_priority_tool
from scheduling_agent import propose_schedule_tool
from reporting_agent import generate_report_tool
from notification_agent import draft_notification_tool

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

notification_agent = Agent(
    role="Notification Coordinator",
    goal="Draft a clear summary email for the biomedical team about scheduled maintenance and outstanding overdue equipment.",
    backstory=(
        "You keep the biomedical engineering team informed about maintenance "
        "activity. You always use the notification tool to draft the email — "
        "you never send anything yourself. A human must review and approve "
        "every draft before it goes out."
    ),
    tools=[draft_notification_tool],
    llm=llm,
    verbose=True,
)

reporting_agent = Agent(
    role="Maintenance Reporting Specialist",
    goal="Produce an accurate, up-to-date PDF report of all equipment maintenance status.",
    backstory=(
        "You prepare maintenance reports for the biomedical engineering "
        "department's records and compliance reviews. You always generate "
        "the report using the reporting tool, which pulls live data directly "
        "from the equipment database, so the report is always accurate."
    ),
    tools=[generate_report_tool],
    llm=llm,
    verbose=True,
)

monitor_task = Task(
    description=(
        "A user submitted this request: \"{request}\"\n\n"
        "Read the request and determine: (1) which ward to filter by, if a "
        "specific ward is mentioned (e.g. 'ICU', 'ER') — otherwise search all "
        "wards; (2) the maintenance time window in days — default to 30 days "
        "if the request doesn't specify one. Then use your tool to find all "
        "equipment needing maintenance within that window and ward filter."
    ),
    expected_output=(
        "A clear list of the matching equipment, including each device's name, "
        "type, ward, criticality, status, and next due date."
    ),
    agent=equipment_monitor_agent,
)

prioritize_task = Task(
    description=(
        "A user submitted this request: \"{request}\"\n\n"
        "Using the same ward and time window you infer from the request "
        "(default: all wards, 30 days), rank the equipment needing maintenance "
        "by priority. If the request specifies how many top items to focus on "
        "(e.g. 'top 5'), use that number; otherwise default to 5."
    ),
    expected_output=(
        "A ranked list (highest priority first) of the inferred number of "
        "equipment items, including each device's name, ward, criticality, "
        "status, next due date, and priority score."
    ),
    agent=prioritization_agent,
)

schedule_task = Task(
    description=(
        "A user submitted this request: \"{request}\"\n\n"
        "Infer from the request how many top-priority items to schedule "
        "(default 5 if not specified), which ward to filter by (default: all "
        "wards), and the time window in days (default 30). Use these values "
        "with your scheduling tool to propose an engineer and date for each "
        "top-priority item."
    ),
    expected_output=(
        "A list of each device scheduled, its assigned engineer, and proposed "
        "date. If any devices could not be scheduled, clearly list them and "
        "explain why."
    ),
    agent=scheduling_agent,
)

notify_task = Task(
    description=(
        "A user submitted this request: \"{request}\"\n\n"
        "Using the same reasoning about ward, time window, and number of "
        "items as the scheduling step, draft a notification email to the "
        "biomedical team summarizing what was scheduled and how many "
        "additional overdue items remain unscheduled."
    ),
    expected_output=(
        "The draft email's subject and full body text, ready for human review. "
        "Clearly state that this is a draft and has not been sent."
    ),
    agent=notification_agent,
)

report_task = Task(
    description=(
        "A user submitted this request: \"{request}\"\n\n"
        "Regardless of any specific ward mentioned in the request, generate "
        "this month's maintenance report covering ALL equipment hospital-wide "
        "— the report always reflects the full picture, not a filtered subset."
    ),
    expected_output=(
        "Confirmation that the report was generated, including the file path "
        "and a summary of how many devices are Overdue, Due, and OK."
    ),
    agent=reporting_agent,
)

crew = Crew(
    agents=[
        equipment_monitor_agent,
        prioritization_agent,
        scheduling_agent,
        notification_agent,
        reporting_agent,
    ],
    tasks=[monitor_task, prioritize_task, schedule_task, notify_task, report_task],
    process=Process.sequential,
    verbose=True,
)


if __name__ == "__main__":
    demo_request = (
        "Show me all ICU equipment that needs maintenance within the next "
        "30 days, prioritize it, schedule the top 5, notify the team, and "
        "generate this month's report."
    )
    result = crew.kickoff(inputs={"request": demo_request})
    print("\n=== FINAL RESULT ===")
    print(result)
