from src.velocity_core import calculate_velocities, parse_long_csv, parse_wide_csv, sort_series


def test_parse_wide_csv_reads_year_columns_and_metadata():
    text = """country,code,region,2000,2001,2002
France,FRA,Europe,3.9,1.9,1.1
India,IND,Asia,3.8,4.8,3.8
"""

    rows = parse_wide_csv(text)

    assert rows[0].name == "France"
    assert rows[0].code == "FRA"
    assert rows[0].group == "Europe"
    assert rows[0].values == {2000: 3.9, 2001: 1.9, 2002: 1.1}


def test_parse_long_csv_groups_country_year_observations():
    text = """country,code,region,year,value
France,FRA,Europe,2000,3.9
France,FRA,Europe,2001,1.9
India,IND,Asia,2000,3.8
"""

    rows = parse_long_csv(text)

    assert len(rows) == 2
    assert rows[0].values == {2000: 3.9, 2001: 1.9}


def test_calculate_velocities_uses_year_on_year_absolute_change():
    row = parse_wide_csv("country,code,region,2000,2001,2002\nFrance,FRA,Europe,3.9,1.9,1.1")[0]

    assert calculate_velocities(row) == {2001: -2.0, 2002: -0.7999999999999998}


def test_sort_series_supports_name_start_end_and_selected_year():
    text = """country,code,region,2000,2001,2002
Beta,BET,Group,2,4,8
Alpha,ALP,Group,9,6,3
Gamma,GAM,Group,4,7,5
"""
    rows = parse_wide_csv(text)

    assert [row.name for row in sort_series(rows, "name")] == ["Alpha", "Beta", "Gamma"]
    assert [row.name for row in sort_series(rows, "start_value")] == ["Beta", "Gamma", "Alpha"]
    assert [row.name for row in sort_series(rows, "end_value")] == ["Alpha", "Gamma", "Beta"]
    assert [row.name for row in sort_series(rows, "selected_year_value", 2001)] == ["Beta", "Alpha", "Gamma"]
    assert [row.name for row in sort_series(rows, "selected_year_velocity", 2002)] == ["Alpha", "Gamma", "Beta"]
