from __future__ import annotations

import html
import math
import csv
import asyncio
from dataclasses import dataclass
from io import StringIO

from js import Blob, FileReader, URL, document, fetch
from pyodide.ffi import create_proxy

try:
    from velocity_core import EntitySeries, calculate_velocities, parse_long_csv, parse_wide_csv, sort_series
except ModuleNotFoundError:
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
        year_columns = sorted(int(name) for name in rows[0].keys() if name.isdigit())
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


# ColorBrewer 2.0 diverging schemes by Cynthia A. Brewer,
# Geography, Pennsylvania State University. https://colorbrewer2.org/
PALETTES = {
    "rdylgn": [
        "#a50026",
        "#d73027",
        "#f46d43",
        "#fdae61",
        "#fee08b",
        "#ffffbf",
        "#d9ef8b",
        "#a6d96a",
        "#66bd63",
        "#1a9850",
        "#006837",
    ],
    "rdbu": [
        "#67001f",
        "#b2182b",
        "#d6604d",
        "#f4a582",
        "#fddbc7",
        "#f7f7f7",
        "#d1e5f0",
        "#92c5de",
        "#4393c3",
        "#2166ac",
        "#053061",
    ],
    "brbg": [
        "#543005",
        "#8c510a",
        "#bf812d",
        "#dfc27d",
        "#f6e8c3",
        "#f5f5f5",
        "#c7eae5",
        "#80cdc1",
        "#35978f",
        "#01665e",
        "#003c30",
    ],
    "piyg": [
        "#8e0152",
        "#c51b7d",
        "#de77ae",
        "#f1b6da",
        "#fde0ef",
        "#f7f7f7",
        "#e6f5d0",
        "#b8e186",
        "#7fbc41",
        "#4d9221",
        "#276419",
    ],
    "puor": [
        "#7f3b08",
        "#b35806",
        "#e08214",
        "#fdb863",
        "#fee0b6",
        "#f7f7f7",
        "#d8daeb",
        "#b2abd2",
        "#8073ac",
        "#542788",
        "#2d004b",
    ],
}

GROUP_COLORS = [
    "#235d7a",
    "#b86f2f",
    "#657c3c",
    "#8b4f7a",
    "#566270",
    "#a33a2c",
    "#4f7666",
    "#6f5a9b",
]


def by_id(identifier: str):
    return document.getElementById(identifier)


def set_status(message: str) -> None:
    by_id("status").textContent = message


def read_controls() -> dict[str, str]:
    return {
        "csv_format": by_id("csv-format").value,
        "entity_column": by_id("entity-column").value.strip() or "country",
        "code_column": by_id("code-column").value.strip() or "code",
        "group_column": by_id("group-column").value.strip() or "region",
        "year_column": by_id("year-column").value.strip() or "year",
        "value_column": by_id("value-column").value.strip() or "value",
        "sort_mode": by_id("sort-mode").value,
        "sort_year": by_id("sort-year").value,
        "palette": by_id("palette").value,
        "center_value": by_id("center-value").value,
        "max_velocity": by_id("max-velocity").value,
        "cell_gap": by_id("cell-gap").value,
    }


def parse_series(text: str, controls: dict[str, str]) -> list[EntitySeries]:
    if controls["csv_format"] == "long":
        return parse_long_csv(
            text,
            controls["entity_column"],
            controls["code_column"],
            controls["group_column"],
            controls["year_column"],
            controls["value_column"],
        )
    return parse_wide_csv(text, controls["entity_column"], controls["code_column"], controls["group_column"])


def interpolate_hex(left: str, right: str, amount: float) -> str:
    amount = max(0.0, min(1.0, amount))
    left_rgb = tuple(int(left[index : index + 2], 16) for index in (1, 3, 5))
    right_rgb = tuple(int(right[index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(round(a + (b - a) * amount) for a, b in zip(left_rgb, right_rgb))
    return "#" + "".join(f"{channel:02x}" for channel in mixed)


def velocity_color(value: float, palette_name: str, center: float, maximum: float) -> str:
    palette = list(reversed(PALETTES.get(palette_name, PALETTES["rdylgn"])))
    if maximum <= 0:
        maximum = 1
    distance = max(-1.0, min(1.0, (value - center) / maximum))
    scaled = (distance + 1) * (len(palette) - 1) / 2
    lower = int(math.floor(scaled))
    upper = min(lower + 1, len(palette) - 1)
    return interpolate_hex(palette[lower], palette[upper], scaled - lower)


def polar_to_cartesian(center: float, radius: float, angle_degrees: float) -> tuple[float, float]:
    radians = math.radians(angle_degrees - 90)
    return center + radius * math.cos(radians), center + radius * math.sin(radians)


def annular_cell_path(center: float, inner: float, outer: float, start_angle: float, end_angle: float) -> str:
    start_outer = polar_to_cartesian(center, outer, start_angle)
    end_outer = polar_to_cartesian(center, outer, end_angle)
    start_inner = polar_to_cartesian(center, inner, end_angle)
    end_inner = polar_to_cartesian(center, inner, start_angle)
    large_arc = 1 if end_angle - start_angle > 180 else 0
    return (
        f"M {start_outer[0]:.3f} {start_outer[1]:.3f} "
        f"A {outer:.3f} {outer:.3f} 0 {large_arc} 1 {end_outer[0]:.3f} {end_outer[1]:.3f} "
        f"L {start_inner[0]:.3f} {start_inner[1]:.3f} "
        f"A {inner:.3f} {inner:.3f} 0 {large_arc} 0 {end_inner[0]:.3f} {end_inner[1]:.3f} Z"
    )


def build_svg(rows: list[EntitySeries], controls: dict[str, str]) -> str:
    selected_year = int(controls["sort_year"]) if controls["sort_year"].isdigit() else None
    rows = sort_series(rows, controls["sort_mode"], selected_year)
    if not rows:
        raise ValueError("No usable data rows found.")

    all_years = sorted({year for row in rows for year in calculate_velocities(row)})
    if not all_years:
        raise ValueError("At least two years of numeric values are required to calculate velocity.")

    inner_radius = 86
    angle_gap = float(controls["cell_gap"] or 0.8)
    maximum = float(controls["max_velocity"] or 1)
    color_center = float(controls["center_value"] or 0)
    angle_step = 360 / len(rows)
    radial_step = max(24.0, min(46.0, 370 / len(all_years)))
    outer_radius = inner_radius + radial_step * len(all_years)
    view_size = int((outer_radius + 148) * 2)
    center = view_size / 2
    group_names = []
    group_palette: dict[str, str] = {}
    for row in rows:
        if row.group not in group_palette:
            group_palette[row.group] = GROUP_COLORS[len(group_palette) % len(GROUP_COLORS)]
            group_names.append(row.group)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_size} {view_size}" role="img">',
        "<title>Velocity chart</title>",
        '<rect width="100%" height="100%" fill="#fffdf8"/>',
        f'<circle cx="{center}" cy="{center}" r="{inner_radius - 18}" fill="#ffffff" stroke="#d8d5cc"/>',
        f'<text x="{center}" y="{center - 8}" text-anchor="middle" font-size="18" font-weight="700" fill="#202124">Velocity</text>',
        f'<text x="{center}" y="{center + 16}" text-anchor="middle" font-size="12" fill="#667085">center {all_years[0]} / edge {all_years[-1]}</text>',
    ]

    for row_index, row in enumerate(rows):
        start_angle = row_index * angle_step + angle_gap
        end_angle = (row_index + 1) * angle_step - angle_gap
        mid_angle = row_index * angle_step + angle_step / 2
        velocities = calculate_velocities(row)
        for year_index, year in enumerate(all_years):
            value = velocities.get(year)
            if value is None:
                continue
            inner = inner_radius + year_index * radial_step + 0.7
            outer = inner + radial_step - 1.4
            color = velocity_color(value, controls["palette"], color_center, maximum)
            path = annular_cell_path(center, inner, outer, start_angle, end_angle)
            label = html.escape(f"{row.name}, {year}: {value:.2f}")
            parts.append(f'<path d="{path}" fill="{color}" stroke="#ffffff" stroke-width="0.15"><title>{label}</title></path>')

        label_radius = outer_radius + 25
        x, y = polar_to_cartesian(center, label_radius, mid_angle)
        rotation = mid_angle - 90
        anchor = "start"
        if 90 < mid_angle < 270:
            rotation += 180
            anchor = "end"
        parts.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="9" fill="{group_palette[row.group]}" '
            f'text-anchor="{anchor}" dominant-baseline="middle" '
            f'transform="rotate({rotation:.2f} {x:.2f} {y:.2f})">{html.escape(row.code or row.name[:3].upper())}</text>'
        )

    previous_group = None
    for row_index, row in enumerate(rows):
        if row.group == previous_group:
            continue
        boundary_angle = row_index * angle_step
        x1, y1 = polar_to_cartesian(center, inner_radius - 2, boundary_angle)
        x2, y2 = polar_to_cartesian(center, outer_radius + 10, boundary_angle)
        parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#827c70" stroke-width="1.1"/>')
        previous_group = row.group

    for year_index, year in enumerate(all_years):
        radius = inner_radius + year_index * radial_step + radial_step / 2
        parts.append(f'<circle cx="{center}" cy="{center}" r="{radius:.2f}" fill="none" stroke="#d8d5cc" stroke-width="0.35"/>')

    for year in (all_years[0], all_years[len(all_years) // 2], all_years[-1]):
        year_index = all_years.index(year)
        radius = inner_radius + year_index * radial_step + radial_step / 2
        lx, ly = polar_to_cartesian(center, radius, 0)
        parts.append(f'<text x="{lx:.2f}" y="{ly - 5:.2f}" text-anchor="middle" font-size="11" fill="#667085">{year}</text>')

    legend_x = 28
    legend_y = view_size - 28 - 18 * len(group_names)
    for index, group in enumerate(group_names):
        y = legend_y + index * 18
        parts.append(f'<circle cx="{legend_x}" cy="{y}" r="4" fill="{group_palette[group]}"/>')
        parts.append(f'<text x="{legend_x + 10}" y="{y + 4}" font-size="11" fill="#4d5660">{html.escape(group)}</text>')

    parts.append("</svg>")
    return "".join(parts)


def render_legend(palette_name: str) -> None:
    colors = list(reversed(PALETTES.get(palette_name, PALETTES["rdylgn"])))
    by_id("legend").innerHTML = "".join(f'<span style="background:{color}"></span>' for color in colors)


def render_chart(event=None) -> None:
    controls = read_controls()
    text = by_id("csv-input").value
    try:
        rows = parse_series(text, controls)
        svg = build_svg(rows, controls)
    except Exception as exc:
        by_id("chart-output").innerHTML = f'<div class="error-state">{html.escape(str(exc))}</div>'
        set_status("Check CSV settings")
        return

    by_id("chart-output").innerHTML = svg
    render_legend(controls["palette"])
    set_status(f"Rendered {len(rows)} series")


async def load_demo(event=None) -> None:
    try:
        response = await fetch("./data/world_bank_gdp_growth_demo.csv")
        text = await response.text()
    except Exception as exc:
        set_status("Demo load failed")
        by_id("chart-output").innerHTML = f'<div class="error-state">{html.escape(str(exc))}</div>'
        return
    by_id("csv-input").value = text
    by_id("csv-format").value = "wide"
    by_id("sort-mode").value = "end_velocity"
    by_id("sort-year").value = "2023"
    by_id("max-velocity").value = "10"
    by_id("chart-title").textContent = "GDP growth velocity"
    by_id("chart-subtitle").textContent = "Each spoke is a country; annual velocity runs from 2015 at the center to 2023 at the edge"
    render_chart()


def on_file_loaded(event) -> None:
    by_id("csv-input").value = event.target.result
    render_chart()


def handle_file(event) -> None:
    files = event.target.files
    if not files.length:
        return
    reader = FileReader.new()
    reader.onload = create_proxy(on_file_loaded)
    reader.readAsText(files.item(0))


def download_svg(event=None) -> None:
    svg = by_id("chart-output").querySelector("svg")
    if svg is None:
        set_status("Render a chart first")
        return
    blob = Blob.new([svg.outerHTML], {"type": "image/svg+xml"})
    url = URL.createObjectURL(blob)
    link = document.createElement("a")
    link.href = url
    link.download = "velocity-chart.svg"
    link.click()
    URL.revokeObjectURL(url)


def attach_events() -> None:
    by_id("load-demo").addEventListener("click", create_proxy(load_demo))
    by_id("render-chart").addEventListener("click", create_proxy(render_chart))
    by_id("download-svg").addEventListener("click", create_proxy(download_svg))
    by_id("csv-file").addEventListener("change", create_proxy(handle_file))
    for identifier in ("palette", "sort-mode", "sort-year", "center-value", "max-velocity", "cell-gap"):
        by_id(identifier).addEventListener("change", create_proxy(render_chart))


attach_events()
render_legend("rdylgn")
set_status("Ready")
asyncio.ensure_future(load_demo())
