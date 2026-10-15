import type { HeatwaveAnalysis, Region, RegionSearchResult } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // Keep the status message when the response is not JSON.
    }
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join(", ") : message);
  }

  return response.json() as Promise<T>;
}

export async function searchRegions(query: string): Promise<RegionSearchResult[]> {
  return request<RegionSearchResult[]>(`/api/regions/search?q=${encodeURIComponent(query)}`);
}

export async function analyzeHeatwave(input: {
  region: Region;
  startYear: number;
  endYear: number;
}): Promise<HeatwaveAnalysis> {
  return request<HeatwaveAnalysis>("/api/analysis/heatwave", {
    method: "POST",
    body: JSON.stringify({
      region: input.region,
      start_year: input.startYear,
      end_year: input.endYear,
      hazard_type: "heatwave",
    }),
  });
}

export function exportCsvUrl(analysisId: string): string {
  return `${API_BASE_URL}/api/analysis/${analysisId}/export.csv`;
}

