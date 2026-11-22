import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def build_workbook(variables: list[dict], results: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Ergebnisse"
    headers = ["Datei"] + [v["name"] for v in variables] + ["Status"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2F5597")
        cell.alignment = Alignment(vertical="center")

    for r in results:
        values = r.get("values") or {}
        row = [r.get("filename")]
        for v in variables:
            val = values.get(v["name"])
            if v.get("type") == "date" and isinstance(val, str):
                try:
                    val = date.fromisoformat(val)
                except ValueError:
                    pass
            if v.get("type") == "boolean" and isinstance(val, bool):
                val = "Ja" if val else "Nein"
            row.append(val)
        row.append(r.get("error") or "OK")
        ws.append(row)

    for idx, v in enumerate(variables, start=2):
        if v.get("type") == "date":
            for cell in ws.iter_cols(min_col=idx, max_col=idx, min_row=2):
                for c in cell:
                    c.number_format = "DD.MM.YYYY"

    for col in range(1, len(headers) + 1):
        letter = get_column_letter(col)
        width = max(len(str(c.value or "")) for c in ws[letter])
        ws.column_dimensions[letter].width = min(max(12, width + 2), 60)
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions

    # zweites Blatt: Variablendefinitionen zur Nachvollziehbarkeit
    ws2 = wb.create_sheet("Variablen")
    ws2.append(["Name", "Typ", "Beschreibung"])
    for cell in ws2[1]:
        cell.font = Font(bold=True)
    for v in variables:
        ws2.append([v["name"], v.get("type", "text"), v.get("description", "")])
    ws2.column_dimensions["A"].width = 25
    ws2.column_dimensions["C"].width = 80

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
