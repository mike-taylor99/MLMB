// ============================================================================
// API Client — thin fetch wrapper for the MLMB API
// ============================================================================

import type {
  BatchRequest,
  BatchResponse,
  HealthResponse,
  Prediction,
  PredictionListResponse,
  PredictionRequest,
  RankingsResponse,
  Sport,
  Team,
  TeamsListResponse,
} from './types'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(
      res.status,
      body?.error?.code ?? 'unknown',
      body?.error?.message ?? res.statusText,
    )
  }

  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function fetchHealth(): Promise<HealthResponse> {
  return request('/health')
}

// ---------------------------------------------------------------------------
// Teams
// ---------------------------------------------------------------------------

export interface ListTeamsParams {
  sport?: Sport
  limit?: number
  after_id?: string
  before_id?: string
}

export function fetchTeams(params: ListTeamsParams = {}): Promise<TeamsListResponse> {
  const qs = new URLSearchParams()
  if (params.sport) qs.set('sport', params.sport)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.after_id) qs.set('after_id', params.after_id)
  if (params.before_id) qs.set('before_id', params.before_id)
  const q = qs.toString()
  return request(`/teams${q ? `?${q}` : ''}`)
}

export function fetchTeam(teamId: string): Promise<Team> {
  return request(`/teams/${encodeURIComponent(teamId)}`)
}

// ---------------------------------------------------------------------------
// Predictions
// ---------------------------------------------------------------------------

export function createPrediction(body: PredictionRequest): Promise<Prediction> {
  return request('/predictions', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function createBatchPredictions(body: BatchRequest): Promise<BatchResponse> {
  return request('/predictions/batch', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export interface ListPredictionsParams {
  sport: Sport
  limit?: number
  after_id?: string
  before_id?: string
}

export function fetchPredictions(params: ListPredictionsParams): Promise<PredictionListResponse> {
  const qs = new URLSearchParams({ sport: params.sport })
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.after_id) qs.set('after_id', params.after_id)
  if (params.before_id) qs.set('before_id', params.before_id)
  return request(`/predictions?${qs}`)
}

export function fetchPrediction(id: string, sport: Sport): Promise<Prediction> {
  return request(`/predictions/${encodeURIComponent(id)}?sport=${sport}`)
}

// ---------------------------------------------------------------------------
// Rankings
// ---------------------------------------------------------------------------

export function fetchRankings(sport: Sport): Promise<RankingsResponse> {
  return request(`/rankings/${sport}`)
}

export { ApiError }
