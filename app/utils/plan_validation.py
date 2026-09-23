"""
Validación completa de un plan de aula antes de enviarlo a revisión.

Devuelve una lista de errores agrupados por sección para que el docente
sepa exactamente qué corregir.
"""

from __future__ import annotations

from datetime import date, datetime

from app.models.classroom_plan import ClassroomPlan
from app.models.plan_area import PlanArea
from app.models.plan_activity import PlanActivity


# ============================================================
# Helpers
# ============================================================
def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _parse_date(value):
    """Acepta date, datetime o string ISO. Devuelve date o None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_datetime(value):
    """Acepta datetime o string ISO. Devuelve datetime o None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


# ============================================================
# Validación de cabecera
# ============================================================
def _validate_header(plan: dict) -> list[str]:
    errors = []

    if _is_blank(plan.get('learning_project_title')):
        errors.append('El título del proyecto de aprendizaje es obligatorio.')

    start = _parse_date(plan.get('start_date'))
    end = _parse_date(plan.get('end_date'))

    if not start:
        errors.append('La fecha de inicio del plan es obligatoria.')
    if not end:
        errors.append('La fecha de finalización del plan es obligatoria.')

    if start and end:
        if end < start:
            errors.append('La fecha de fin del plan es anterior a la de inicio.')
        # Duración razonable
        duration_days = (end - start).days
        if duration_days > 200:
            errors.append(
                f'La duración del plan es excesiva ({duration_days} días). '
                f'Máximo permitido: 200 días.'
            )

    if _is_blank(plan.get('situational_diagnosis')):
        errors.append('El diagnóstico situacional es obligatorio.')

    if _is_blank(plan.get('purposes')):
        errors.append('Los propósitos del plan son obligatorios.')

    return errors


# ============================================================
# Validación de áreas
# ============================================================
def _validate_areas(plan_id: int) -> list[str]:
    errors = []
    areas = PlanArea.get_by_plan(plan_id)

    if not areas:
        errors.append('El plan debe tener al menos un área de formación.')
        return errors

    for idx, area in enumerate(areas, start=1):
        prefix = f'Área #{idx} ({area.get("formation_area") or "sin nombre"})'

        if _is_blank(area.get('formation_area')):
            errors.append(f'{prefix}: el nombre del área es obligatorio.')

        if _is_blank(area.get('contents')):
            errors.append(f'{prefix}: los contenidos son obligatorios.')

        if _is_blank(area.get('expected_learning')):
            errors.append(f'{prefix}: los aprendizajes esperados son obligatorios.')

        # Verificar que tenga al menos una actividad
        activities = PlanActivity.get_by_area(area['id'])
        if not activities:
            errors.append(f'{prefix}: debe tener al menos una actividad.')

    return errors


# ============================================================
# Validación de actividades
# ============================================================
def _validate_activities(plan_id: int, plan: dict) -> list[str]:
    errors = []
    plan_start = _parse_date(plan.get('start_date'))
    plan_end = _parse_date(plan.get('end_date'))

    activities = PlanActivity.get_by_plan(plan_id)

    if not activities:
        return ['El plan no tiene actividades registradas.']

    # Detección de títulos duplicados por área
    seen_titles = {}

    for idx, act in enumerate(activities, start=1):
        prefix = f'Actividad #{idx} ({act.get("title") or "sin título"})'

        if _is_blank(act.get('title')):
            errors.append(f'{prefix}: el título es obligatorio.')

        if _is_blank(act.get('strategy')):
            errors.append(f'{prefix}: la estrategia pedagógica es obligatoria.')

        if _is_blank(act.get('indicators')):
            errors.append(f'{prefix}: los indicadores son obligatorios.')

        if _is_blank(act.get('evaluation_technique')):
            errors.append(f'{prefix}: la técnica de evaluación es obligatoria.')

        if _is_blank(act.get('evaluation_instrument')):
            errors.append(f'{prefix}: el instrumento de evaluación es obligatorio.')

        # Validar fechas de la actividad
        act_start = _parse_datetime(act.get('start_datetime'))
        act_end = _parse_datetime(act.get('end_datetime'))

        if act_start and act_end and act_end < act_start:
            errors.append(f'{prefix}: la fecha de fin es anterior a la de inicio.')

        if plan_start and act_start and act_start.date() < plan_start:
            errors.append(
                f'{prefix}: la fecha de la actividad es anterior al inicio del plan.'
            )

        if plan_end and act_end and act_end.date() > plan_end:
            errors.append(
                f'{prefix}: la fecha de la actividad es posterior al fin del plan.'
            )

        # Duplicados por área
        key = (act.get('plan_area_id'), (act.get('title') or '').strip().lower())
        if key in seen_titles:
            errors.append(f'{prefix}: título duplicado en la misma área.')
        seen_titles[key] = True

    return errors


# ============================================================
# Función principal
# ============================================================
def validate_plan_for_submission(plan_id: int) -> dict:
    """
    Valida un plan completo antes de permitir su envío a revisión.

    Returns:
        dict con:
            is_valid:  bool
            errors:    list[str]   (errores agrupados)
            summary:   dict        (contadores)
    """
    plan = ClassroomPlan.get_by_id(plan_id)
    if not plan:
        return {
            'is_valid': False,
            'errors': ['El plan no existe o fue eliminado.'],
            'summary': {},
        }

    all_errors: list[str] = []
    all_errors.extend(_validate_header(plan))
    all_errors.extend(_validate_areas(plan_id))
    all_errors.extend(_validate_activities(plan_id, plan))

    areas = PlanArea.get_by_plan(plan_id)
    activities_count = 0
    for area in areas:
        activities_count += len(PlanActivity.get_by_area(area['id']))

    return {
        'is_valid': len(all_errors) == 0,
        'errors': all_errors,
        'summary': {
            'areas_count': len(areas),
            'activities_count': activities_count,
            'total_errors': len(all_errors),
        },
    }