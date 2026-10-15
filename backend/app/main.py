import csv
import io
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.analysis import analysis_key, build_heatwave_analysis
from app.cache import CacheRepository, build_cache
from app.config import Settings, get_settings
from app.models import HeatwaveAnalysisRequest, HeatwaveAnalysisResponse, RegionSearchResult
from app.rate_limit import InMemoryRateLimiter
from app.weather import WeatherService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.cache = build_cache(settings)
    app.state.rate_limiter = InMemoryRateLimiter()
    yield


app = FastAPI(
    title="Climate Hazard Trend Analyzer API",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_cache(request: Request) -> CacheRepository:
    return request.app.state.cache


def rate_limit(request: Request) -> None:
    request.app.state.rate_limiter.check(request)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "Climate Hazard Trend Analyzer API", "status": "ok"}


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/regions/search", response_model=list[RegionSearchResult], dependencies=[Depends(rate_limit)])
async def search_regions(q: str, cache: CacheRepository = Depends(get_cache)) -> list[RegionSearchResult]:
    if len(q.strip()) < 2:
        raise HTTPException(status_code=422, detail="Search query must be at least 2 characters")
    service = WeatherService(get_settings(), cache)
    return await service.search_regions(q.strip())


@app.post(
    "/api/analysis/heatwave",
    response_model=HeatwaveAnalysisResponse,
    dependencies=[Depends(rate_limit)],
)
async def analyze_heatwave(
    request: HeatwaveAnalysisRequest,
    cache: CacheRepository = Depends(get_cache),
) -> HeatwaveAnalysisResponse:
    key = analysis_key(request)
    cached_analysis = await cache.get("analysis", key)
    if cached_analysis:
        payload = cached_analysis["payload"]
        payload["cached"] = True
        return HeatwaveAnalysisResponse(**payload)

    service = WeatherService(get_settings(), cache)
    weather_records, cached_weather = await service.daily_max_temperatures(
        request.region.latitude,
        request.region.longitude,
        request.start_year,
        request.end_year,
    )
    analysis = build_heatwave_analysis(request, weather_records, cached_weather)
    await cache.set("analysis", key, analysis.model_dump())
    return analysis


@app.get("/api/analysis/{analysis_id}", response_model=HeatwaveAnalysisResponse)
async def get_analysis(analysis_id: str, cache: CacheRepository = Depends(get_cache)) -> HeatwaveAnalysisResponse:
    cached_analysis = await cache.get("analysis", analysis_id)
    if not cached_analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return HeatwaveAnalysisResponse(**cached_analysis["payload"])


@app.get("/api/analysis/{analysis_id}/export.csv")
async def export_analysis_csv(analysis_id: str, cache: CacheRepository = Depends(get_cache)) -> StreamingResponse:
    cached_analysis = await cache.get("analysis", analysis_id)
    if not cached_analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    analysis = HeatwaveAnalysisResponse(**cached_analysis["payload"])

    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "year",
            "event_count",
            "heatwave_days",
            "longest_event_days",
            "average_intensity_c",
            "rolling_heatwave_days",
        ]
    )
    for metric in analysis.annual:
        writer.writerow(
            [
                metric.year,
                metric.event_count,
                metric.heatwave_days,
                metric.longest_event_days,
                metric.average_intensity_c,
                metric.rolling_heatwave_days or "",
            ]
        )
    stream.seek(0)
    filename = f"heatwave-analysis-{analysis_id[:8]}.csv"
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

