# Climate Hazard Trend Analyzer

This is a full-stack case-study app for exploring historical heatwave trends for a selected region. I kept the first version focused on one hazard, heatwaves, because the brief emphasized a working and well-reasoned analysis over a broader but thinner multi-hazard build.

## Architecture

- `frontend/`: React, TypeScript, Vite, Leaflet, Recharts.
- `backend/`: FastAPI, Open-Meteo integration, MongoDB-compatible cache, CSV export.
- Data flow: the frontend sends a selected region and year range to the backend. The backend fetches daily maximum temperature data, caches raw weather data, computes heatwave metrics, caches the derived analysis, and returns JSON for the map, charts, event table, and summary insight.

## Data Source

The backend uses the Open-Meteo Historical Weather API archive endpoint for daily maximum temperature values. I chose Open-Meteo because it is free, does not require an API key, and is straightforward to use in a deployed case-study app. City search uses the Open-Meteo geocoding endpoint.

## Hazard Logic

Heatwave is the supported hazard type and is selected by default.

- Calculate the 95th percentile of daily maximum temperatures for the selected region and selected time range.
- Mark days above that threshold as hot days.
- Detect heatwave events as 3 or more consecutive hot days.
- Summarize annual event count, heatwave days, longest event duration, average intensity, 5-year rolling average, and linear trend slope.

## Assumptions And Limitations

- For a custom lat-lon box, the backend analyzes the center point of the box and keeps the box for UI/context.
- The percentile threshold is computed over the selected period for the selected region.
- Open-Meteo data is treated as the source of truth for this assignment.
- MongoDB Atlas should be configured for deployed caching. Local development falls back to a JSON file cache under `.cache/`.
- The regression slope is a simple linear fit over annual heatwave days. It is useful as an interpretable first-pass trend, but it is not a full statistical significance test.
- The app does not currently aggregate multiple grid cells across a bounding box. That would be the main data-quality improvement I would make next.

## Local Setup

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open the frontend at `http://localhost:5173`.

## Environment Variables

Backend:

- `MONGODB_URI`: MongoDB Atlas connection string. Optional locally, recommended for deployment.
- `MONGODB_DB`: database name, defaults to `climate_hazard_analyzer`.
- `FRONTEND_ORIGINS`: comma-separated allowed frontend origins.
- `OPEN_METEO_ARCHIVE_URL`: archive API override.
- `OPEN_METEO_GEOCODE_URL`: geocoding API override.

Frontend:

- `VITE_API_BASE_URL`: deployed or local backend URL.

## Deployment

Deploy as two Vercel projects:

1. Backend project
   - Root directory: `backend`
   - Add `MONGODB_URI`, `MONGODB_DB`, and `FRONTEND_ORIGINS`.
   - Vercel uses `api/index.py` as the FastAPI entrypoint.

2. Frontend project
   - Root directory: `frontend`
   - Add `VITE_API_BASE_URL` pointing to the backend deployment URL.

MongoDB Atlas M0 free tier is enough for this case-study cache.

## AI Tools Used

I used OpenAI Codex to scaffold parts of the FastAPI and React implementation, help debug local setup/CORS issues, draft documentation, and run verification commands. I reviewed the implementation decisions, tested the API locally, and checked the MongoDB-backed cache path.

## Improvements With More Time

- Add Mann-Kendall trend testing.
- Add PDF export.
- Add gridded aggregation across all cells in a bounding box instead of center-point approximation.
- Add authentication for saved analyses.
- Add scheduled precomputation for common regions.

