export type BoundingBox = {
  north: number;
  south: number;
  east: number;
  west: number;
};

export type Region = {
  name: string;
  latitude: number;
  longitude: number;
  country?: string | null;
  admin1?: string | null;
  bbox?: BoundingBox | null;
};

export type RegionSearchResult = {
  id: number;
  name: string;
  country?: string | null;
  admin1?: string | null;
  latitude: number;
  longitude: number;
};

export type AnnualMetric = {
  year: number;
  event_count: number;
  heatwave_days: number;
  longest_event_days: number;
  average_intensity_c: number;
  rolling_heatwave_days: number | null;
};

export type HeatwaveEvent = {
  start_date: string;
  end_date: string;
  duration_days: number;
  max_temperature_c: number;
  average_excess_c: number;
};

export type TrendSummary = {
  baseline_year: number;
  latest_year: number;
  baseline_heatwave_days: number;
  latest_heatwave_days: number;
  percent_change: number | null;
  slope_days_per_year: number;
  insight: string;
};

export type HeatwaveAnalysis = {
  analysis_id: string;
  region: Region;
  start_year: number;
  end_year: number;
  hazard_type: "heatwave";
  threshold_c: number;
  event_count: number;
  heatwave_days: number;
  annual: AnnualMetric[];
  events: HeatwaveEvent[];
  summary: TrendSummary;
  source: string;
  cached: boolean;
};

