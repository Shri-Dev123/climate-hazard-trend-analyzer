from datetime import date, timedelta

from app.analysis import build_heatwave_analysis, percentile
from app.models import HeatwaveAnalysisRequest, Region


def test_percentile_interpolates() -> None:
    assert percentile([1, 2, 3, 4, 5], 0.95) == 4.8


def test_heatwave_detection_requires_three_consecutive_days() -> None:
    request = HeatwaveAnalysisRequest(
        region=Region(name="Test City", latitude=10, longitude=20),
        start_year=2000,
        end_year=2000,
    )
    start = date(2000, 1, 1)
    records = [
        {"date": (start + timedelta(days=offset)).isoformat(), "temperature_2m_max": 30}
        for offset in range(95)
    ]
    records.extend(
        {
            "date": (start + timedelta(days=95 + offset)).isoformat(),
            "temperature_2m_max": temperature,
        }
        for offset, temperature in enumerate([50, 51, 52, 53, 54])
    )

    analysis = build_heatwave_analysis(request, records, cached_weather=False)

    assert analysis.event_count == 1
    assert analysis.events[0].duration_days == 5
    assert analysis.annual[0].heatwave_days == 5

