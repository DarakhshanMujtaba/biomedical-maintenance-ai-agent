from pathlib import Path
from datetime import date

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from sql_tool import get_all_equipment_with_status

REPORTS_DIR = Path(__file__).parent.parent / "reports"

STATUS_ORDER = {"Overdue": 0, "Due": 1, "OK": 2}

COLUMNS = ["Name", "Type", "Ward", "Criticality", "Status", "Next Due"]


def build_maintenance_report():
    equipment = get_all_equipment_with_status()
    equipment.sort(key=lambda row: STATUS_ORDER[row["status"]])

    counts = {"Overdue": 0, "Due": 0, "OK": 0}
    for row in equipment:
        counts[row["status"]] += 1

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, text="Monthly Maintenance Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, text=f"Generated: {date.today().isoformat()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(
        0, 8,
        text=f"Summary: {counts['Overdue']} Overdue, {counts['Due']} Due, {counts['OK']} OK",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    with pdf.table(col_widths=(35, 28, 25, 22, 22, 25)) as table:
        header = table.row()
        for col in COLUMNS:
            header.cell(col)

        for item in equipment:
            row = table.row()
            row.cell(item["name"])
            row.cell(item["type"])
            row.cell(item["ward"])
            row.cell(item["criticality"])
            row.cell(item["status"])
            row.cell(item["next_due_date"])

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"maintenance_report_{date.today().strftime('%Y-%m')}.pdf"
    output_path = REPORTS_DIR / filename
    pdf.output(str(output_path))

    print(f"Report saved to: {output_path}")
    return {"output_path": str(output_path), "counts": counts}


if __name__ == "__main__":
    build_maintenance_report()
