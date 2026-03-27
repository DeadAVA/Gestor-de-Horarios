from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.exports.institutional_layout import (
    DAY_KEYS,
    INSTITUTIONAL_GRAY,
    INSTITUTIONAL_GREEN,
    TABLE_HEADERS,
    get_logo_path,
)
from app.exports.report_builder import ReportBuilder


class PdfExporter:
    @staticmethod
    def export_group_schedule(group_id: int) -> BytesIO:
        context = ReportBuilder.build_group_report_context(group_id)
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=landscape(letter),
            leftMargin=0.6 * cm,
            rightMargin=0.6 * cm,
            topMargin=3.8 * cm,
            bottomMargin=0.8 * cm,
        )

        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            "BodySmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=7.2,
            alignment=0,
        )
        centered_style = ParagraphStyle(
            "BodyCenter",
            parent=body_style,
            alignment=1,
        )
        header_style = ParagraphStyle(
            "HeaderCell",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.2,
            leading=7,
            textColor=colors.white,
            alignment=1,
        )

        table_data = [[Paragraph(header.replace("\n", "<br/>"), header_style) for header in TABLE_HEADERS]]
        for row in context["rows"]:
            table_data.append(
                [
                    Paragraph(_pdf_text(row["clave_control"]), body_style),
                    Paragraph(_pdf_text(row["descripcion_maestro"]), body_style),
                    Paragraph(_pdf_text(row["edificio"]), centered_style),
                    Paragraph(_pdf_text(row["salon"]), centered_style),
                    Paragraph(_pdf_text(str(row["cap_asg"])), centered_style),
                    Paragraph(_pdf_text(str(row["tpo_sgp"])), centered_style),
                    Paragraph(_pdf_text(row["lunes"]), centered_style),
                    Paragraph(_pdf_text(row["martes"]), centered_style),
                    Paragraph(_pdf_text(row["miercoles"]), centered_style),
                    Paragraph(_pdf_text(row["jueves"]), centered_style),
                    Paragraph(_pdf_text(row["viernes"]), centered_style),
                    Paragraph(_pdf_text(row["sabado"]), centered_style),
                    Paragraph(_pdf_text(row["domingo"]), centered_style),
                    Paragraph(_pdf_text(str(row["es"])), centered_style),
                ]
            )

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[2.2 * cm, 4.6 * cm, 1.1 * cm, 1.1 * cm, 0.9 * cm, 1.0 * cm, 1.4 * cm, 1.4 * cm, 1.5 * cm, 1.4 * cm, 1.4 * cm, 1.4 * cm, 1.4 * cm, 0.9 * cm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{INSTITUTIONAL_GREEN}")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7B7B7")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        story = [Spacer(1, 0.1 * cm), table]
        document.build(story, onFirstPage=lambda canvas, doc: _draw_header(canvas, doc, context), onLaterPages=lambda canvas, doc: _draw_header(canvas, doc, context))
        output.seek(0)
        return output



def _draw_header(canvas, doc, context: dict) -> None:
    canvas.saveState()
    width, height = landscape(letter)

    canvas.setFont("Helvetica", 8)
    canvas.drawString(16, height - 18, context["generated_time"])
    canvas.drawRightString(width - 16, height - 18, context["generated_date"])
    canvas.drawString(16, height - 38, context["report_code"])
    canvas.drawRightString(width - 16, height - 38, f"PAG. {canvas.getPageNumber()}")

    logo_path = get_logo_path()
    if logo_path is not None:
        canvas.drawImage(str(logo_path), 150, height - 78, width=42, height=48, preserveAspectRatio=True, mask="auto")
    else:
        canvas.setStrokeColor(colors.HexColor(f"#{INSTITUTIONAL_GREEN}"))
        canvas.rect(150, height - 78, 42, 48)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(171, height - 53, "LOGO")

    canvas.setFillColor(colors.HexColor(f"#{INSTITUTIONAL_GREEN}"))
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(width / 2, height - 18, context["institution_name"])
    canvas.setFillColor(colors.HexColor(f"#{INSTITUTIONAL_GRAY}"))
    canvas.setFont("Helvetica", 10)
    canvas.drawCentredString(width / 2, height - 33, context["coordination_name"])
    canvas.drawCentredString(width / 2, height - 47, context["report_title"])
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(width / 2, height - 60, f"Periodo: {context['period']}")

    canvas.setFillColor(colors.black)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(16, height - 82, "UNIDAD ACADÉMICA:")
    canvas.drawString(16, height - 95, "CARRERA:")
    canvas.drawString(16, height - 108, "PLAN DE ESTUDIOS:")
    canvas.drawRightString(width - 120, height - 82, "GRUPO:")
    canvas.drawRightString(width - 120, height - 95, "TIPO:")

    canvas.setFont("Helvetica", 8)
    canvas.drawString(100, height - 82, context["unit_code"])
    canvas.drawString(136, height - 82, context["unit_name"])
    canvas.drawString(100, height - 95, context["career_code"])
    canvas.drawString(136, height - 95, context["career_name"])
    canvas.drawString(100, height - 108, context["plan_key"])
    canvas.drawString(width - 112, height - 82, str(context["group_number"]))
    canvas.drawString(width - 112, height - 95, str(context["group_type_label"]))

    canvas.restoreState()



def _pdf_text(value: str) -> str:
    return value.replace("\n\n", "<br/><br/>").replace("\n", "<br/>")
