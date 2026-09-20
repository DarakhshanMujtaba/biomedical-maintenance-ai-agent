import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "tools"))

from pdf_tool import build_maintenance_report

from crewai.tools import tool


@tool("Generate monthly maintenance report")
def generate_report_tool(confirm: bool = True) -> str:
    """
    Generates the monthly maintenance report as a PDF covering all equipment,
    sorted by urgency (Overdue first, then Due, then OK). Saves it to the
    reports folder and returns the file path along with a summary count of
    how many devices are Overdue, Due, and OK.

    Args:
        confirm: Unused. This tool takes no real input, but CrewAI's schema
            generator produces an invalid (empty) schema for zero-argument
            tools, so this dummy parameter works around that bug.
    """
    result = build_maintenance_report()
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

    report_task = Task(
        description="Generate this month's maintenance report covering all equipment.",
        expected_output=(
            "Confirmation that the report was generated, including the file path "
            "and a summary of how many devices are Overdue, Due, and OK."
        ),
        agent=reporting_agent,
    )

    crew = Crew(
        agents=[reporting_agent],
        tasks=[report_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    print("\n=== FINAL RESULT ===")
    print(result)
