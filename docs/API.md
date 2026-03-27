# KHIS Toolkit API

The KHIS Toolkit API exposes county metadata, indicator discovery, cleaned data pulls, quality summaries, forecasting, and a curated mental-health workflow through FastAPI.

If `KHIS_API_KEY` is set in the environment, send it in the `X-API-Key` header. If it is not set, the API runs in development mode without auth and prints a warning on startup.

Base local URL used in the examples below:

```bash
http://127.0.0.1:8000
```

## GET /health

Returns service health and auth mode.

```bash
curl http://127.0.0.1:8000/health
```

## GET /counties

Returns all 47 Kenya counties with their metadata.

```bash
curl -H "X-API-Key: your-key-if-enabled" \
  http://127.0.0.1:8000/counties
```

## GET /indicators?search={term}

Searches indicators available to the configured DHIS2/KHIS connection.

```bash
curl -H "X-API-Key: your-key-if-enabled" \
  "http://127.0.0.1:8000/indicators?search=malaria"
```

## GET /data/{county}/{indicator}?periods=last_12_months

Pulls and cleans one county-indicator series. In demo mode, this can fall back to the cached demo dataset if live county IDs are unavailable.

```bash
curl -H "X-API-Key: your-key-if-enabled" \
  "http://127.0.0.1:8000/data/Nairobi/Malaria%20Cases?periods=last_12_months"
```

## POST /forecast

Creates a forecast for a county and indicator using `prophet`, `xgboost`, or `ensemble`.

```bash
curl -X POST http://127.0.0.1:8000/forecast \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key-if-enabled" \
  -d "{\"county\":\"Nairobi\",\"indicator\":\"Malaria Cases\",\"weeks_ahead\":4,\"method\":\"ensemble\"}"
```

## GET /quality/{county}

Returns the county quality scorecard row from the cached dataset.

```bash
curl -H "X-API-Key: your-key-if-enabled" \
  "http://127.0.0.1:8000/quality/Nairobi"
```

## GET /mental-health/indicators

Returns the curated mental-health indicator package together with live KHIS
availability where it can be resolved.

```bash
curl -H "X-API-Key: your-key-if-enabled" \
  "http://127.0.0.1:8000/mental-health/indicators"
```

## GET /mental-health/summary

Returns a county-level mental-health summary table built from the cached mental
health workflow.

```bash
curl -H "X-API-Key: your-key-if-enabled" \
  "http://127.0.0.1:8000/mental-health/summary"
```

## GET /mental-health/{county}

Returns one county's mental-health summary plus the latest indicator snapshot.

```bash
curl -H "X-API-Key: your-key-if-enabled" \
  "http://127.0.0.1:8000/mental-health/Nairobi"
```

## GET /docs

FastAPI automatically serves Swagger UI at `/docs`.

```bash
http://127.0.0.1:8000/docs
```

## Running Locally

```bash
uvicorn src.api:app --reload
```
