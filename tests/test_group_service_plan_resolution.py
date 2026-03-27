from app.models import PlanEstudio
from app.services.group_service import GroupService


def test_get_plan_by_key_prioritizes_exact_match(db):
    old_plan = PlanEstudio(clave="2015-2", nombre="Plan Viejo")
    alias_plan = PlanEstudio(clave="2025-2", nombre="Alias")
    db.session.add_all([old_plan, alias_plan])
    db.session.commit()

    selected = GroupService._get_plan_by_key("2015-2")

    assert selected.id == old_plan.id
    assert selected.clave == "2015-2"


def test_get_plan_by_key_uses_alias_as_fallback(db):
    alias_plan = PlanEstudio(clave="2025-2", nombre="Alias")
    db.session.add(alias_plan)
    db.session.commit()

    selected = GroupService._get_plan_by_key("2015-2")

    assert selected.id == alias_plan.id
    assert selected.clave == "2025-2"
