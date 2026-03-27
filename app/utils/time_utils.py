from datetime import date, datetime, time


END_OF_DAY_SENTINEL = time(23, 59)


DAY_ORDER = {
    "lunes": 1,
    "martes": 2,
    "miercoles": 3,
    "jueves": 4,
    "viernes": 5,
    "sabado": 6,
}


def calculate_hours_from_blocks(blocks) -> float:
    total_hours = 0.0
    for block in blocks:
        total_hours += calculate_duration_hours(block.hora_inicio, block.hora_fin)
    return round(total_hours, 2)


def calculate_duration_hours(start_time: time, end_time: time) -> float:
    start_dt = datetime.combine(date.min, start_time)
    if end_time == END_OF_DAY_SENTINEL:
        end_dt = datetime.combine(date.min, time(0, 0))
        return round(((end_dt - start_dt).total_seconds() + 24 * 3600) / 3600, 2)

    end_dt = datetime.combine(date.min, end_time)
    return round((end_dt - start_dt).total_seconds() / 3600, 2)


def parse_time_value(value, field_name: str) -> time:
    if value in (None, ""):
        raise ValueError(f"El campo {field_name} es obligatorio")

    if isinstance(value, time):
        return value

    raw_value = str(value).strip()
    if raw_value == "24:00":
        return END_OF_DAY_SENTINEL

    try:
        return datetime.strptime(raw_value, "%H:%M").time()
    except ValueError:
        raise ValueError(f"El campo {field_name} debe usar formato HH:MM")


def format_time_value(value: time) -> str:
    if value == END_OF_DAY_SENTINEL:
        return "24:00"
    return value.strftime("%H:%M")


def day_sort_key(day: str) -> int:
    return DAY_ORDER.get(day, 99)