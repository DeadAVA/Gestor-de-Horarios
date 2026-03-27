from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from flask import send_file
from pypdf import PdfWriter
from sqlalchemy import select

from app.extensions import db
from app.exports.excel_exporter import ExcelExporter
from app.exports.historial_exporter import (
    HistorialExcelExporter,
    HistorialPdfExporter,
    HistorialWordExporter,
)
from app.exports.pdf_exporter import PdfExporter
from app.exports.word_exporter import WordExporter
from app.models import Docente, Grupo
from app.services.historial_service import HistorialService


def _group_type_file_label(group_type: str) -> str:
    return "semiescolarizado" if group_type == "semi" else "escolarizado"


class ExportService:
    # ──── Group schedules (existing) ──────────────────────────────────────

    @staticmethod
    def export_group_schedule_excel(group_id: int):
        filename = f"horario_grupo_{group_id}.xlsx"
        output = ExcelExporter.export_group_schedule(group_id)
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @staticmethod
    def export_group_schedule_word(group_id: int):
        filename = f"horario_grupo_{group_id}.docx"
        output = WordExporter.export_group_schedule(group_id)
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @staticmethod
    def export_group_schedule_pdf(group_id: int):
        filename = f"horario_grupo_{group_id}.pdf"
        output = PdfExporter.export_group_schedule(group_id)
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )

    @staticmethod
    def export_all_group_schedules(format_name: str):
        exporters = {
            "excel": (ExcelExporter.export_group_schedule, "xlsx"),
            "word": (WordExporter.export_group_schedule, "docx"),
            "pdf": (PdfExporter.export_group_schedule, "pdf"),
        }
        exporter_info = exporters.get(format_name)
        if exporter_info is None:
            raise ValueError("Formato de exportacion no soportado")

        export_fn, extension = exporter_info
        groups = db.session.scalars(select(Grupo).order_by(Grupo.numero_grupo.asc())).all()

        if format_name == "pdf":
            merged_pdf = BytesIO()
            writer = PdfWriter()
            for group in groups:
                file_buffer = export_fn(group.id)
                writer.append(file_buffer)

            writer.write(merged_pdf)
            merged_pdf.seek(0)
            return send_file(
                merged_pdf,
                as_attachment=True,
                download_name=f"horarios_todos_{_group_type_suffix(groups)}.pdf",
                mimetype="application/pdf",
            )

        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
            for group in groups:
                file_buffer = export_fn(group.id)
                zip_file.writestr(
                    f"horario_grupo_{group.numero_grupo}_{_group_type_file_label(group.tipo_grupo)}.{extension}",
                    file_buffer.getvalue(),
                )

        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"horarios_todos_{format_name}.zip",
            mimetype="application/zip",
        )

    # ──── Historial de docentes ───────────────────────────────────────────

    @staticmethod
    def export_historial_excel(teacher_id: int | None = None):
        if teacher_id:
            teacher = db.session.get(Docente, teacher_id)
            nombre = teacher.nombre.replace(" ", "_") if teacher else str(teacher_id)
            rows = HistorialService.get_historial_by_teacher(teacher_id)
            title = f"Historial de {teacher.nombre if teacher else teacher_id}"
            filename = f"historial_docente_{nombre}.xlsx"
        else:
            rows = HistorialService.get_historial_all()
            title = "Historial General de Docentes"
            filename = "historial_docentes.xlsx"
        output = HistorialExcelExporter.export(rows, title)
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @staticmethod
    def export_historial_word(teacher_id: int | None = None):
        if teacher_id:
            teacher = db.session.get(Docente, teacher_id)
            nombre = teacher.nombre.replace(" ", "_") if teacher else str(teacher_id)
            rows = HistorialService.get_historial_by_teacher(teacher_id)
            title = f"Historial de {teacher.nombre if teacher else teacher_id}"
            filename = f"historial_docente_{nombre}.docx"
        else:
            rows = HistorialService.get_historial_all()
            title = "Historial General de Docentes"
            filename = "historial_docentes.docx"
        output = HistorialWordExporter.export(rows, title)
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @staticmethod
    def export_historial_pdf(teacher_id: int | None = None):
        if teacher_id:
            teacher = db.session.get(Docente, teacher_id)
            nombre = teacher.nombre.replace(" ", "_") if teacher else str(teacher_id)
            rows = HistorialService.get_historial_by_teacher(teacher_id)
            title = f"Historial de {teacher.nombre if teacher else teacher_id}"
            filename = f"historial_docente_{nombre}.pdf"
        else:
            rows = HistorialService.get_historial_all()
            title = "Historial General de Docentes"
            filename = "historial_docentes.pdf"
        output = HistorialPdfExporter.export(rows, title)
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )


def _group_type_suffix(groups: list[Grupo]) -> str:
    has_escolarizado = any(group.tipo_grupo == "normal" for group in groups)
    has_semiescolarizado = any(group.tipo_grupo == "semi" for group in groups)
    if has_escolarizado and has_semiescolarizado:
        return "escolarizados_y_semiescolarizados"
    if has_semiescolarizado:
        return "semiescolarizados"
    return "escolarizados"
