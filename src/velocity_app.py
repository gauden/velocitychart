from __future__ import annotations

import html
import math

from js import Blob, FileReader, URL, document, fetch
from pyodide.ffi import create_proxy

from velocity_core import EntitySeries, calculate_velocities, parse_long_csv, parse_wide_csv, sort_series


PALETTES = {
    "red_green": ("#2f8f67", "#f7f7f2", "#b94235"),
    "red_blue": ("#3569a8", "#f7f7f2", "#bd3d31"),
    "purple_teal": ("#188f88", "#f7f7f2", "#7b4aa8"),
    "orange_cyan": ("#2b94a8", "#f7f7f2", "#c7691f"),
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
    negative, neutral, positive = PALETTES.get(palette_name, PALETTES["red_green"])
    if maximum <= 0:
        maximum = 1
    distance = max(-1.0, min(1.0, (value - center) / maximum))
    if abs(distance) < 0.015:
        return neutral
    if distance > 0:
        return interpolate_hex(neutral, positive, distance)
    return interpolate_hex(neutral, negative, abs(distance))


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

    center = 500
    row_height = max(7.0, min(17.0, 360 / max(len(rows), 1)))
    inner_radius = 96
    angle_gap = float(controls["cell_gap"] or 0.8)
    maximum = float(controls["max_velocity"] or 1)
    color_center = float(controls["center_value"] or 0)
    angle_step = 360 / len(all_years)
    outer_radius = inner_radius + row_height * len(rows)
    view_size = int((outer_radius + 105) * 2)
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
        f'<text x="{center}" y="{center + 16}" text-anchor="middle" font-size="12" fill="#667085">{all_years[0]}-{all_years[-1]}</text>',
    ]

    for row_index, row in enumerate(rows):
        inner = inner_radius + row_index * row_height
        outer = inner + row_height - 0.7
        velocities = calculate_velocities(row)
        for year_index, year in enumerate(all_years):
            value = velocities.get(year)
            if value is None:
                continue
            start_angle = year_index * angle_step + angle_gap
            end_angle = (year_index + 1) * angle_step - angle_gap
            color = velocity_color(value, controls["palette"], color_center, maximum)
            path = annular_cell_path(center, inner, outer, start_angle, end_angle)
            label = html.escape(f"{row.name}, {year}: {value:.2f}")
            parts.append(f'<path d="{path}" fill="{color}" stroke="#ffffff" stroke-width="0.15"><title>{label}</title></path>')

        label_angle = 92
        label_radius = outer_radius + 16
        x, y = polar_to_cartesian(center, label_radius, label_angle + row_index * 0.07)
        parts.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="8.5" fill="{group_palette[row.group]}" '
            f'text-anchor="middle">{html.escape(row.code or row.name[:3].upper())}</text>'
        )

    for year in (all_years[0], all_years[len(all_years) // 2], all_years[-1]):
        year_index = all_years.index(year)
        angle = year_index * angle_step + angle_step / 2
        x1, y1 = polar_to_cartesian(center, inner_radius - 8, angle)
        x2, y2 = polar_to_cartesian(center, outer_radius + 8, angle)
        lx, ly = polar_to_cartesian(center, outer_radius + 44, angle)
        parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#b9b5aa" stroke-width="0.7"/>')
        parts.append(f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" font-size="11" fill="#667085">{year}</text>')

    legend_x = 28
    legend_y = view_size - 28 - 18 * len(group_names)
    for index, group in enumerate(group_names):
        y = legend_y + index * 18
        parts.append(f'<circle cx="{legend_x}" cy="{y}" r="4" fill="{group_palette[group]}"/>')
        parts.append(f'<text x="{legend_x + 10}" y="{y + 4}" font-size="11" fill="#4d5660">{html.escape(group)}</text>')

    parts.append("</svg>")
    return "".join(parts)


def render_legend(palette_name: str) -> None:
    negative, neutral, positive = PALETTES.get(palette_name, PALETTES["red_green"])
    colors = [
        interpolate_hex(neutral, negative, 1),
        interpolate_hex(neutral, negative, 0.45),
        neutral,
        interpolate_hex(neutral, positive, 0.45),
        interpolate_hex(neutral, positive, 1),
    ]
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
    response = await fetch("./data/world_bank_gdp_growth_demo.csv")
    text = await response.text()
    by_id("csv-input").value = text
    by_id("csv-format").value = "wide"
    by_id("sort-mode").value = "end_velocity"
    by_id("sort-year").value = "2023"
    by_id("max-velocity").value = "10"
    by_id("chart-title").textContent = "GDP growth velocity"
    by_id("chart-subtitle").textContent = "Annual change in GDP growth rate, percentage points per year"
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
render_legend("red_green")
set_status("Ready")
