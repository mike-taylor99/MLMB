// ============================================================================
// API Client — thin fetch wrapper for the MLMB API
// ============================================================================

import type {
  Analysis,
  AnalysisRequest,
  BatchRequest,
  BatchResponse,
  Bracket,
  BracketListResponse,
  CreateBracketRequest,
  HealthResponse,
  Prediction,
  PredictionListResponse,
  PredictionRequest,
  RankingsResponse,
  Sport,
  Team,
  TeamsListResponse,
  Tournament,
  TournamentListResponse,
  UpdateBracketRequest,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(
      res.status,
      body?.error?.code ?? "unknown",
      body?.error?.message ?? res.statusText,
    );
  }

  // 204 No Content — nothing to parse
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function fetchHealth(): Promise<HealthResponse> {
  return request("/api/health");
}

// ---------------------------------------------------------------------------
// Teams
// ---------------------------------------------------------------------------

export interface ListTeamsParams {
  sport?: Sport;
  limit?: number;
  after_id?: string;
  before_id?: string;
  enabled?: boolean;
}

export function fetchTeams(
  params: ListTeamsParams = {},
): Promise<TeamsListResponse> {
  const qs = new URLSearchParams();
  if (params.sport) qs.set("sport", params.sport);
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.after_id) qs.set("after_id", params.after_id);
  if (params.before_id) qs.set("before_id", params.before_id);
  const q = qs.toString();
  return request(`/api/teams${q ? `?${q}` : ""}`);
}

export function fetchTeam(teamId: string): Promise<Team> {
  return request(`/api/teams/${encodeURIComponent(teamId)}`);
}

// ---------------------------------------------------------------------------
// Predictions
// ---------------------------------------------------------------------------

export function createPrediction(body: PredictionRequest): Promise<Prediction> {
  return request("/api/predictions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function createBatchPredictions(
  body: BatchRequest,
): Promise<BatchResponse> {
  return request("/api/predictions/batch", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function createAnalysis(body: AnalysisRequest): Promise<Analysis> {
  return request("/api/predictions/analysis", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchAnalysis(id: string, sport: Sport): Promise<Analysis> {
  return request(
    `/api/predictions/analysis/${encodeURIComponent(id)}?sport=${sport}`,
  );
}

export interface ListPredictionsParams {
  sport: Sport;
  limit?: number;
  after_id?: string;
  before_id?: string;
}

export function fetchPredictions(
  params: ListPredictionsParams,
): Promise<PredictionListResponse> {
  const qs = new URLSearchParams({ sport: params.sport });
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.after_id) qs.set("after_id", params.after_id);
  if (params.before_id) qs.set("before_id", params.before_id);
  return request(`/api/predictions?${qs}`);
}

export function fetchPrediction(id: string, sport: Sport): Promise<Prediction> {
  return request(`/api/predictions/${encodeURIComponent(id)}?sport=${sport}`);
}

// ---------------------------------------------------------------------------
// Rankings
// ---------------------------------------------------------------------------

export function fetchRankings(sport: Sport): Promise<RankingsResponse> {
  return request(`/api/rankings/${sport}`);
}

// ---------------------------------------------------------------------------
// Tournaments
// ---------------------------------------------------------------------------

export function fetchTournaments(): Promise<TournamentListResponse> {
  return request("/api/tournaments");
}

export function fetchTournament(id: string): Promise<Tournament> {
  return request(`/api/tournaments/${encodeURIComponent(id)}`);
}

// ---------------------------------------------------------------------------
// Brackets
// ---------------------------------------------------------------------------

export function fetchBrackets(
  tournamentId?: string,
): Promise<BracketListResponse> {
  const qs = tournamentId
    ? `?tournament_id=${encodeURIComponent(tournamentId)}`
    : "";
  return request(`/api/brackets${qs}`);
}

export function fetchBracket(bracketId: string): Promise<Bracket> {
  return request(`/api/brackets/${encodeURIComponent(bracketId)}`);
}

export function fetchPublicBracket(
  tournamentId: string,
  bracketId: string,
): Promise<Bracket> {
  return request(
    `/api/tournaments/${encodeURIComponent(tournamentId)}/brackets/${encodeURIComponent(bracketId)}`,
  );
}

export function createBracket(body: CreateBracketRequest): Promise<Bracket> {
  return request("/api/brackets", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateBracket(
  bracketId: string,
  body: UpdateBracketRequest,
): Promise<Bracket> {
  return request(`/api/brackets/${encodeURIComponent(bracketId)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteBracket(bracketId: string): Promise<void> {
  return request(`/api/brackets/${encodeURIComponent(bracketId)}`, {
    method: "DELETE",
  });
}

export { ApiError };
