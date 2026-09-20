import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent / "tools"))

from notification_tool import draft_team_notification

from crewai.tools import tool


@tool("Draft team notification email")
def draft_notification_tool(top_n: int = 5, ward: Optional[str] = None, within_days: int = 30) -> str:
    """
    Schedules the top N highest-priority equipment items needing maintenance
    (optionally filtered by ward, within a given number of days), then drafts
    a summary notification email listing what was scheduled (device, ward,
    engineer, date) and how many additional overdue devices remain
    unscheduled this cycle. Returns the draft's subject and body — this
    tool never sends anything; a human must review and approve it first.
    """
    result = draft_team_notification(top_n=top_n, ward=ward, within_days=within_days)
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

    notify_task = Task(
        description=(
            "Draft a notification email to the biomedical team summarizing the "
            "maintenance scheduled for the top 5 priority ICU equipment items, "
            "including any additional overdue items that remain unscheduled."
        ),
        expected_output=(
            "The draft email's subject and full body text, ready for human review. "
            "Clearly state that this is a draft and has not been sent."
        ),
        agent=notification_agent,
    )

    crew = Crew(
        agents=[notification_agent],
        tasks=[notify_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    print("\n=== FINAL RESULT ===")
    print(result)
