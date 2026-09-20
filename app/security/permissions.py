"""
Catálogo centralizado de permisos.

Cada permiso es una constante de tipo string con formato:
    'recurso.acción[.subtipo]'

Usar estas constantes en lugar de strings literales:
    ✅ Permission.STUDENT_VIEW_BASIC
    ❌ "student.view.basic"

Beneficios:
    - Autocompletado en el editor
    - Refactor seguro (rename global)
    - Detección temprana de errores tipográficos
"""


class Permission:
    """Catálogo de permisos del sistema."""

    # ---------------- Estudiantes: lectura ----------------
    STUDENT_VIEW_BASIC         = "student.view.basic"         # nombre, cédula, curso
    STUDENT_VIEW_FAMILY        = "student.view.family"        # grupo familiar
    STUDENT_VIEW_MEDICAL       = "student.view.medical"       # ficha médica completa
    STUDENT_VIEW_SOCIOECONOMIC = "student.view.socioeconomic" # estudio socioeconómico
    STUDENT_VIEW_ENROLLMENTS   = "student.view.enrollments"   # historial de inscripciones
    STUDENT_VIEW_HISTORY       = "student.view.history"       # historial académico

    # ---------------- Estudiantes: escritura ----------------
    STUDENT_CREATE             = "student.create"
    STUDENT_EDIT_BASIC         = "student.edit.basic"
    STUDENT_EDIT_FAMILY        = "student.edit.family"
    STUDENT_EDIT_MEDICAL       = "student.edit.medical"
    STUDENT_EDIT_SOCIOECONOMIC = "student.edit.socioeconomic"
    STUDENT_DELETE             = "student.delete"

    # ---------------- Evaluaciones ----------------
    EVALUATION_VIEW            = "evaluation.view"
    EVALUATION_CREATE          = "evaluation.create"
    EVALUATION_EDIT            = "evaluation.edit"
    EVALUATION_CONFIGURE       = "evaluation.configure"   # áreas y periodos

    # ---------------- Documentos ----------------
    DOCUMENT_ISSUE_CONSTANCIA   = "document.issue.constancia"
    DOCUMENT_ISSUE_CERTIFICACION = "document.issue.certificacion"

    # ---------------- Dashboard / Reportes ----------------
    DASHBOARD_VIEW             = "dashboard.view"
    REPORT_VIEW_GLOBAL         = "report.view.global"

    # ---------------- Estadística diaria ----------------
    DAILY_STATS_VIEW   = "daily_stats.view"     # ver resúmenes/histórico
    DAILY_STATS_CREATE = "daily_stats.create"   # reportar asistencia de un curso