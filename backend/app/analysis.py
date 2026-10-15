import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean
from typing import Any

from app.models import (
    AnnualMetric,
    HeatwaveAnalysisRequest,
    HeatwaveAnalysisResponse,
    HeatwaveEvent,
    TrendSummary,
)


def analysis_key(request: HeatwaveAnalysisRequest) -> str:
    encoded = json.dumps(request.model_dump(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def percentile(values: list[float], percentile_rank: float) -> float:
    if not values:
        raise ValueError("values cannot be empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_rank
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def linear_regression_slope(points: list[tuple[int, int]]) -> float:
    if len(points) < 2:
        return 0.0
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_avg = mean(xs)
    y_avg = mean(ys)
    denominator = sum((x - x_avg) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    numerator = sum((x - x_avg) * (y - y_avg) for x, y in zip(xs, ys, strict=True))
    return numerator / denominator


def rolling_average(values: list[int], window: int = 5) -> list[float | None]:
    averaged: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < window:
            averaged.append(None)
            continue
        averaged.append(round(mean(values[index + 1 - window : index + 1]), 2))
    return averaged


def build_heatwave_analysis(
    request: HeatwaveAnalysisRequest,
    weather_records: list[dict[str, Any]],
    cached_weather: bool,
) -> HeatwaveAnalysisResponse:
    temperatures = [float(record["temperature_2m_max"]) for record in weather_records]
    # The brief suggests a percentile-based heatwave definition. This threshold is
    # local to the selected region and analysis period rather than a global value.
    threshold = round(percentile(temperatures, 0.95), 2)

    by_day = [
        (date.fromisoformat(record["date"]), float(record["temperature_2m_max"]))
        for record in weather_records
    ]

    events: list[HeatwaveEvent] = []
    current: list[tuple[date, float]] = []

    def flush_event() -> None:
        # A heatwave is counted only when at least three hot days are consecutive.
        if len(current) < 3:
            return
        temps = [temperature for _, temperature in current]
        events.append(
            HeatwaveEvent(
                start_date=current[0][0].isoformat(),
                end_date=current[-1][0].isoformat(),
                duration_days=len(current),
                max_temperature_c=round(max(temps), 2),
                average_excess_c=round(mean([temperature - threshold for temperature in temps]), 2),
            )
        )

    previous_day: date | None = None
    for day, temperature in by_day:
        is_hot = temperature > threshold
        is_consecutive = previous_day is None or day == previous_day + timedelta(days=1)
        if is_hot and is_consecutive:
            current.append((day, temperature))
        else:
            flush_event()
            current = [(day, temperature)] if is_hot else []
        previous_day = day
    flush_event()

    annual_events: dict[int, list[HeatwaveEvent]] = defaultdict(list)
    annual_days: dict[int, set[str]] = defaultdict(set)
    for event in events:
        start = date.fromisoformat(event.start_date)
        for offset in range(event.duration_days):
            event_day = start + timedelta(days=offset)
            annual_days[event_day.year].add(event_day.isoformat())
        annual_events[start.year].append(event)

    heatwave_days_by_year = []
    for year in range(request.start_year, request.end_year + 1):
        heatwave_days_by_year.append(len(annual_days[year]))

    rolling = rolling_average(heatwave_days_by_year)
    annual: list[AnnualMetric] = []
    for index, year in enumerate(range(request.start_year, request.end_year + 1)):
        year_events = annual_events[year]
        intensities = [event.average_excess_c for event in year_events]
        annual.append(
            AnnualMetric(
                year=year,
                event_count=len(year_events),
                heatwave_days=heatwave_days_by_year[index],
                longest_event_days=max([event.duration_days for event in year_events], default=0),
                average_intensity_c=round(mean(intensities), 2) if intensities else 0,
                rolling_heatwave_days=rolling[index],
            )
        )

    points = [(metric.year, metric.heatwave_days) for metric in annual]
    slope = round(linear_regression_slope(points), 3)
    baseline = annual[0]
    latest = annual[-1]
    if baseline.heatwave_days == 0:
        percent_change = None if latest.heatwave_days == 0 else 100.0
    else:
        percent_change = round(
            ((latest.heatwave_days - baseline.heatwave_days) / baseline.heatwave_days) * 100,
            1,
        )

    if percent_change is None:
        insight = (
            f"No heatwave days were detected in either {baseline.year} or {latest.year}; "
            f"the fitted trend is {slope} days per year."
        )
    elif percent_change >= 0:
        insight = (
            f"Heatwave days increased from {baseline.heatwave_days} in {baseline.year} "
            f"to {latest.heatwave_days} in {latest.year} ({percent_change}% change). "
            f"The fitted trend is {slope} days per year."
        )
    else:
        insight = (
            f"Heatwave days decreased from {baseline.heatwave_days} in {baseline.year} "
            f"to {latest.heatwave_days} in {latest.year} ({abs(percent_change)}% change). "
            f"The fitted trend is {slope} days per year."
        )

    return HeatwaveAnalysisResponse(
        analysis_id=analysis_key(request),
        region=request.region,
        start_year=request.start_year,
        end_year=request.end_year,
        hazard_type="heatwave",
        threshold_c=threshold,
        event_count=len(events),
        heatwave_days=sum(metric.heatwave_days for metric in annual),
        annual=annual,
        events=events,
        summary=TrendSummary(
            baseline_year=baseline.year,
            latest_year=latest.year,
            baseline_heatwave_days=baseline.heatwave_days,
            latest_heatwave_days=latest.heatwave_days,
            percent_change=percent_change,
            slope_days_per_year=slope,
            insight=insight,
        ),
        source="Open-Meteo Archive API",
        cached=cached_weather,
    )

