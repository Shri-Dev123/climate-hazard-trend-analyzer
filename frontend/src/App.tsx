import { FormEvent, useMemo, useState } from "react";
import { Activity, Download, Loader2, MapPin, Search, ThermometerSun } from "lucide-react";
import { MapContainer, TileLayer, CircleMarker, Rectangle, useMapEvents } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyzeHeatwave, exportCsvUrl, searchRegions } from "./api";
import type { BoundingBox, HeatwaveAnalysis, Region, RegionSearchResult } from "./types";

const defaultRegion: Region = {
  name: "Bengaluru",
  latitude: 12.9716,
  longitude: 77.5946,
  country: "India",
  admin1: "Karnataka",
};

const defaultBox: BoundingBox = {
  north: 13.18,
  south: 12.78,
  east: 77.82,
  west: 77.36,
};

function MapClickHandler({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(event) {
      onPick(Number(event.latlng.lat.toFixed(4)), Number(event.latlng.lng.toFixed(4)));
    },
  });
  return null;
}

function formatRegion(region: Region): string {
  return [region.name, region.admin1, region.country].filter(Boolean).join(", ");
}

function metricValue(value: number | string): string {
  return typeof value === "number" ? value.toLocaleString() : value;
}

function App() {
  const [query, setQuery] = useState("Bengaluru");
  const [regionResults, setRegionResults] = useState<RegionSearchResult[]>([]);
  const [region, setRegion] = useState<Region>(defaultRegion);
  const [startYear, setStartYear] = useState(1990);
  const [endYear, setEndYear] = useState(2020);
  const [customBox, setCustomBox] = useState<BoundingBox>(defaultBox);
  const [isCustomBox, setIsCustomBox] = useState(false);
  const [analysis, setAnalysis] = useState<HeatwaveAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeRegion = useMemo<Region>(() => {
    if (!isCustomBox) {
      return region;
    }
    return {
      name: "Custom lat-lon box",
      latitude: Number(((customBox.north + customBox.south) / 2).toFixed(4)),
      longitude: Number(((customBox.east + customBox.west) / 2).toFixed(4)),
      bbox: customBox,
    };
  }, [customBox, isCustomBox, region]);

  const bounds = useMemo<LatLngBoundsExpression | null>(() => {
    if (!activeRegion.bbox) {
      return null;
    }
    return [
      [activeRegion.bbox.south, activeRegion.bbox.west],
      [activeRegion.bbox.north, activeRegion.bbox.east],
    ];
  }, [activeRegion.bbox]);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSearching(true);
    try {
      const results = await searchRegions(query);
      setRegionResults(results);
      if (results[0]) {
        setRegion({
          name: results[0].name,
          country: results[0].country,
          admin1: results[0].admin1,
          latitude: results[0].latitude,
          longitude: results[0].longitude,
        });
        setIsCustomBox(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Region search failed");
    } finally {
      setSearching(false);
    }
  }

  async function handleAnalyze() {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeHeatwave({ region: activeRegion, startYear, endYear });
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  function updateBox(key: keyof BoundingBox, value: number) {
    setCustomBox((current) => ({ ...current, [key]: value }));
  }

  function pickMapPoint(lat: number, lon: number) {
    setRegion({
      name: `Point ${lat}, ${lon}`,
      latitude: lat,
      longitude: lon,
    });
    setIsCustomBox(false);
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="control-panel">
          <div className="brand-row">
            <div className="brand-mark">
              <ThermometerSun size={24} aria-hidden="true" />
            </div>
            <div>
              <h1>Climate Hazard Trend Analyzer</h1>
              <p>Heatwave trend dashboard</p>
            </div>
          </div>

          <form className="search-row" onSubmit={handleSearch}>
            <label htmlFor="region-search">Region</label>
            <div className="input-with-button">
              <input
                id="region-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="City or state"
              />
              <button type="submit" className="icon-button" aria-label="Search region" title="Search region">
                {searching ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
              </button>
            </div>
          </form>

          {regionResults.length > 0 && (
            <div className="result-list">
              {regionResults.map((result) => (
                <button
                  type="button"
                  key={result.id}
                  className="result-button"
                  onClick={() => {
                    setRegion({
                      name: result.name,
                      country: result.country,
                      admin1: result.admin1,
                      latitude: result.latitude,
                      longitude: result.longitude,
                    });
                    setIsCustomBox(false);
                  }}
                >
                  <MapPin size={15} aria-hidden="true" />
                  <span>{[result.name, result.admin1, result.country].filter(Boolean).join(", ")}</span>
                </button>
              ))}
            </div>
          )}

          <div className="field-grid two">
            <label>
              Start year
              <input
                type="number"
                min="1940"
                max="2100"
                value={startYear}
                onChange={(event) => setStartYear(Number(event.target.value))}
              />
            </label>
            <label>
              End year
              <input
                type="number"
                min="1940"
                max="2100"
                value={endYear}
                onChange={(event) => setEndYear(Number(event.target.value))}
              />
            </label>
          </div>

          <label>
            Hazard
            <select value="heatwave" disabled>
              <option value="heatwave">Heatwave</option>
            </select>
          </label>

          <div className="toggle-row">
            <input
              id="custom-box"
              type="checkbox"
              checked={isCustomBox}
              onChange={(event) => setIsCustomBox(event.target.checked)}
            />
            <label htmlFor="custom-box">Use custom lat-lon box</label>
          </div>

          {isCustomBox && (
            <div className="field-grid two compact">
              <label>
                North
                <input type="number" step="0.01" value={customBox.north} onChange={(e) => updateBox("north", Number(e.target.value))} />
              </label>
              <label>
                South
                <input type="number" step="0.01" value={customBox.south} onChange={(e) => updateBox("south", Number(e.target.value))} />
              </label>
              <label>
                East
                <input type="number" step="0.01" value={customBox.east} onChange={(e) => updateBox("east", Number(e.target.value))} />
              </label>
              <label>
                West
                <input type="number" step="0.01" value={customBox.west} onChange={(e) => updateBox("west", Number(e.target.value))} />
              </label>
            </div>
          )}

          <button className="primary-action" type="button" onClick={handleAnalyze} disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <Activity size={18} />}
            Run analysis
          </button>

          {error && <div className="error-banner">{error}</div>}
        </aside>

        <section className="dashboard">
          <div className="status-band">
            <div>
              <span className="eyebrow">Selected region</span>
              <h2>{formatRegion(activeRegion)}</h2>
              <p>
                {activeRegion.latitude.toFixed(4)}, {activeRegion.longitude.toFixed(4)}
              </p>
            </div>
            {analysis && (
              <a className="download-link" href={exportCsvUrl(analysis.analysis_id)}>
                <Download size={18} aria-hidden="true" />
                CSV
              </a>
            )}
          </div>

          <div className="map-panel">
            <MapContainer
              center={[activeRegion.latitude, activeRegion.longitude]}
              zoom={isCustomBox ? 9 : 7}
              scrollWheelZoom
              className="map"
              key={`${activeRegion.latitude}-${activeRegion.longitude}-${isCustomBox}`}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapClickHandler onPick={pickMapPoint} />
              <CircleMarker center={[activeRegion.latitude, activeRegion.longitude]} radius={9} pathOptions={{ color: "#d97706", fillColor: "#f59e0b", fillOpacity: 0.8 }} />
              {bounds && <Rectangle bounds={bounds} pathOptions={{ color: "#15803d", weight: 2 }} />}
            </MapContainer>
          </div>

          {analysis ? (
            <>
              <div className="metric-grid">
                <div className="metric-card">
                  <span>Threshold</span>
                  <strong>{metricValue(analysis.threshold_c)} deg C</strong>
                </div>
                <div className="metric-card">
                  <span>Events</span>
                  <strong>{metricValue(analysis.event_count)}</strong>
                </div>
                <div className="metric-card">
                  <span>Heatwave days</span>
                  <strong>{metricValue(analysis.heatwave_days)}</strong>
                </div>
                <div className="metric-card">
                  <span>Trend</span>
                  <strong>{analysis.summary.slope_days_per_year} d/yr</strong>
                </div>
              </div>

              <div className="insight-panel">
                <span className="eyebrow">Summary insight</span>
                <p>{analysis.summary.insight}</p>
                <small>{analysis.cached ? "Loaded from cache" : `Source: ${analysis.source}`}</small>
              </div>

              <div className="chart-grid">
                <section className="chart-panel">
                  <h3>Annual heatwave days</h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <LineChart data={analysis.annual} margin={{ top: 12, right: 24, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#d9ded7" />
                      <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="heatwave_days" stroke="#166534" strokeWidth={2.5} dot={false} name="Heatwave days" />
                      <Line type="monotone" dataKey="rolling_heatwave_days" stroke="#2563eb" strokeWidth={2} dot={false} name="5-year rolling avg" />
                    </LineChart>
                  </ResponsiveContainer>
                </section>

                <section className="chart-panel">
                  <h3>Event count and intensity</h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={analysis.annual} margin={{ top: 12, right: 24, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#d9ded7" />
                      <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="event_count" fill="#d97706" name="Events" />
                      <Bar dataKey="average_intensity_c" fill="#0f766e" name="Avg excess deg C" />
                    </BarChart>
                  </ResponsiveContainer>
                </section>
              </div>

              <section className="events-panel">
                <h3>Recent detected events</h3>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Start</th>
                        <th>End</th>
                        <th>Days</th>
                        <th>Max deg C</th>
                        <th>Avg excess</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.events.slice(-8).reverse().map((event) => (
                        <tr key={`${event.start_date}-${event.end_date}`}>
                          <td>{event.start_date}</td>
                          <td>{event.end_date}</td>
                          <td>{event.duration_days}</td>
                          <td>{event.max_temperature_c}</td>
                          <td>{event.average_excess_c}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          ) : (
            <div className="empty-state">
              <ThermometerSun size={30} aria-hidden="true" />
              <p>Run an analysis to populate the trend dashboard.</p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

export default App;

