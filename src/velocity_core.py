from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from io import StringIO


@dataclass(frozen=True)
class EntitySeries:
    name: str
    code: str
    group: str
    values: dict[int, float]


def _clean_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number):
        return None
    return number


def parse_wide_csv(
    text: str,
    entity_column: str = "country",
    code_column: str = "code",
    group_column: str = "region",
) -> list[EntitySeries]:
    rows = list(csv.DictReader(StringIO(text.strip())))
    if not rows:
        return []

    fieldnames = rows[0].keys()
    year_columns = sorted(int(name) for name in fieldnames if name.isdigit())
    series: list[EntitySeries] = []

    for row in rows:
        values = {
            year: value
            for year in year_columns
            if (value := _clean_float(row.get(str(year)))) is not None
        }
        if values:
            name = row.get(entity_column, "").strip()
            code = row.get(code_column, "").strip() or name[:3].upper()
            group = row.get(group_column, "").strip() or "Ungrouped"
            series.append(EntitySeries(name=name, code=code, group=group, values=values))

    return series


def parse_long_csv(
    text: str,
    entity_column: str = "country",
    code_column: str = "code",
    group_column: str = "region",
    year_column: str = "year",
    value_column: str = "value",
) -> list[EntitySeries]:
    grouped: dict[tuple[str, str, str], dict[int, float]] = {}

    for row in csv.DictReader(StringIO(text.strip())):
        name = row.get(entity_column, "").strip()
        if not name:
            continue
        code = row.get(code_column, "").strip() or name[:3].upper()
        group = row.get(group_column, "").strip() or "Ungrouped"
        year_text = row.get(year_column, "").strip()
        if not year_text.isdigit():
            continue
        value = _clean_float(row.get(value_column))
        if value is None:
            continue
        grouped.setdefault((name, code, group), {})[int(year_text)] = value

    return [
        EntitySeries(name=name, code=code, group=group, values=dict(sorted(values.items())))
        for (name, code, group), values in grouped.items()
        if values
    ]


def calculate_velocities(series: EntitySeries) -> dict[int, float]:
    years = sorted(series.values)
    velocities: dict[int, float] = {}
    for previous, current in zip(years, years[1:]):
        velocities[current] = series.values[current] - series.values[previous]
    return velocities


def sort_series(
    rows: list[EntitySeries],
    mode: str = "end_velocity",
    selected_year: int | None = None,
) -> list[EntitySeries]:
    def start_value(row: EntitySeries) -> float:
        return row.values[min(row.values)]

    def end_value(row: EntitySeries) -> float:
        return row.values[max(row.values)]

    def selected_value(row: EntitySeries) -> float:
        if selected_year is None:
            return end_value(row)
        return row.values.get(selected_year, math.inf)

    def selected_velocity(row: EntitySeries) -> float:
        velocities = calculate_velocities(row)
        if selected_year is None:
            return velocities.get(max(velocities), math.inf) if velocities else math.inf
        return velocities.get(selected_year, math.inf)

    key_functions = {
        "name": lambda row: row.name.lower(),
        "start_value": start_value,
        "end_value": end_value,
        "selected_year_value": selected_value,
        "selected_year_velocity": selected_velocity,
        "end_velocity": selected_velocity,
    }
    key_function = key_functions.get(mode, key_functions["end_velocity"])

    return sorted(rows, key=lambda row: (row.group.lower(), key_function(row), row.name.lower()))
