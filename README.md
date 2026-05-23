# Velocity Chart

A static, client-side PyScript tool for generating circular velocity charts from CSV time series.

The app accepts either:

- **Wide CSV**: one row per entity, one column per year.
- **Long CSV**: one row per entity-year observation.

Uploaded data is parsed in the browser. No server-side upload is required.

## Demo Data

The bundled demo uses the World Bank indicator **NY.GDP.MKTP.KD.ZG**, GDP growth (annual %), for selected economies.

Source: <https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG>

World Bank describes this indicator as annual percentage growth rate of GDP at market prices based on constant local currency.

## Run Locally

Serve the directory with any static web server:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000/
```

The app loads PyScript from its public CDN.

## CSV Formats

Wide format:

```csv
country,code,region,2000,2001,2002
United States,USA,North America,4.1,1.0,1.7
```

Long format:

```csv
country,code,region,year,value
United States,USA,North America,2000,4.1
United States,USA,North America,2001,1.0
```

## Tests

The core parsing and velocity helpers are plain Python and can be tested with:

```bash
uv run pytest
```
