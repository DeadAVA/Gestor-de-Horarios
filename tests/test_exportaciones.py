"""
Pruebas de humo para los endpoints de exportación institucional.
Verifica que cada formato devuelva 200, el MIME correcto y la firma de archivo esperada.
"""
import pytest

from app.models import Grupo


# ---------------------------------------------------------------------------
# Exportar a Excel (.xlsx)
# ---------------------------------------------------------------------------

def test_export_excel_devuelve_200(client, seed):
    resp = client.get(f"/api/exportaciones/grupos/{seed['grupo1_id']}/excel")
    assert resp.status_code == 200


def test_export_excel_mime_correcto(client, seed):
    resp = client.get(f"/api/exportaciones/grupos/{seed['grupo1_id']}/excel")
    assert "spreadsheetml" in resp.content_type


def test_export_excel_firma_zip(client, seed):
    """Los archivos .xlsx son ZIPs; los primeros bytes deben ser 'PK'."""
    resp = client.get(f"/api/exportaciones/grupos/{seed['grupo1_id']}/excel")
    assert resp.data[:2] == b"PK"


def test_export_excel_grupo_inexistente(client, db):
    resp = client.get("/api/exportaciones/grupos/99999/excel")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Exportar a Word (.docx)
# ---------------------------------------------------------------------------

def test_export_word_devuelve_200(client, seed):
    resp = client.get(f"/api/exportaciones/grupos/{seed['grupo1_id']}/word")
    assert resp.status_code == 200


def test_export_word_mime_correcto(client, seed):
    resp = client.get(f"/api/exportaciones/grupos/{seed['grupo1_id']}/word")
    assert "wordprocessingml" in resp.content_type


def test_export_word_firma_zip(client, seed):
    resp = client.get(f"/api/exportaciones/grupos/{seed['grupo1_id']}/word")
    assert resp.data[:2] == b"PK"


def test_export_word_grupo_inexistente(client, db):
    resp = client.get("/api/exportaciones/grupos/99999/word")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Exportar a PDF
# ---------------------------------------------------------------------------

def test_export_pdf_devuelve_200(client, seed):
    resp = client.get(f"/api/exportaciones/grupos/{seed['grupo1_id']}/pdf")
    assert resp.status_code == 200


def test_export_pdf_mime_correcto(client, seed):
    resp = client.get(f"/api/exportaciones/grupos/{seed['grupo1_id']}/pdf")
    assert resp.content_type == "application/pdf"


def test_export_pdf_firma_pdf(client, seed):
    resp = client.get(f"/api/exportaciones/grupos/{seed['grupo1_id']}/pdf")
    assert resp.data[:4] == b"%PDF"


def test_export_pdf_grupo_inexistente(client, db):
    resp = client.get("/api/exportaciones/grupos/99999/pdf")
    assert resp.status_code == 404


def test_export_todos_pdf_un_archivo_pdf(client, seed):
    resp = client.get("/api/exportaciones/grupos/todos/pdf")
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    assert resp.data[:4] == b"%PDF"
    assert "horarios_todos_escolarizados.pdf" in resp.headers.get("Content-Disposition", "")


def test_export_todos_pdf_nombre_incluye_semiescolarizados_si_aplica(client, db, seed):
    grupo_semi = Grupo(
        numero_grupo=503,
        semestre=1,
        plan_estudio_id=seed["plan1_id"],
        capacidad_alumnos=30,
        tipo_grupo="semi",
    )
    db.session.add(grupo_semi)
    db.session.commit()

    resp = client.get("/api/exportaciones/grupos/todos/pdf")
    assert resp.status_code == 200
    assert "horarios_todos_escolarizados_y_semiescolarizados.pdf" in resp.headers.get("Content-Disposition", "")
