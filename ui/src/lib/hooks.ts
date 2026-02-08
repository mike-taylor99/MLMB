// ============================================================================
// TanStack Query hooks — one hook per API call
// ============================================================================

import {
  useQuery,
  useMutation,
  useInfiniteQuery,
  type UseQueryOptions,
  type InfiniteData,
} from '@tanstack/react-query'

import {
  fetchHealth,
  fetchTeams,
  fetchTeam,
  fetchRankings,
  fetchPredictions,
  createPrediction,
  type ListTeamsParams,
  type ListPredictionsParams,
} from './api'

import type {
  HealthResponse,
  TeamsListResponse,
  Team,
  RankingsResponse,
  PredictionListResponse,
  Prediction,
  PredictionRequest,
  Sport,
} from './types'

// ---------------------------------------------------------------------------
// Query keys — centralised for easy invalidation
// ---------------------------------------------------------------------------

export const queryKeys = {
  health: ['health'] as const,
  teams: (params?: ListTeamsParams) => ['teams', params] as const,
  team: (id: string) => ['teams', id] as const,
  rankings: (sport: Sport) => ['rankings', sport] as const,
  predictions: (params: ListPredictionsParams) => ['predictions', params] as const,
} as const

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function useHealth(opts?: Partial<UseQueryOptions<HealthResponse>>) {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: fetchHealth,
    staleTime: 30_000,
    ...opts,
  })
}

// ---------------------------------------------------------------------------
// Teams
// ---------------------------------------------------------------------------

export function useTeams(params: ListTeamsParams = {}) {
  return useQuery({
    queryKey: queryKeys.teams(params),
    queryFn: () => fetchTeams(params),
    staleTime: 5 * 60_000, // teams rarely change
  })
}

/** Infinite-scroll teams list. */
export function useInfiniteTeams(sport?: Sport, limit = 50) {
  return useInfiniteQuery<TeamsListResponse, Error, InfiniteData<TeamsListResponse>, readonly unknown[], string | undefined>({
    queryKey: queryKeys.teams({ sport, limit }),
    queryFn: ({ pageParam }) => fetchTeams({ sport, limit, after_id: pageParam }),
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => (lastPage.has_more ? lastPage.last_id ?? undefined : undefined),
    staleTime: 5 * 60_000,
  })
}

export function useTeam(teamId: string) {
  return useQuery<Team>({
    queryKey: queryKeys.team(teamId),
    queryFn: () => fetchTeam(teamId),
    staleTime: 5 * 60_000,
    enabled: !!teamId,
  })
}

// ---------------------------------------------------------------------------
// Rankings
// ---------------------------------------------------------------------------

export function useRankings(sport: Sport) {
  return useQuery<RankingsResponse>({
    queryKey: queryKeys.rankings(sport),
    queryFn: () => fetchRankings(sport),
    staleTime: 10 * 60_000, // rankings update infrequently
  })
}

// ---------------------------------------------------------------------------
// Predictions
// ---------------------------------------------------------------------------

export function usePredictions(params: ListPredictionsParams) {
  return useInfiniteQuery<PredictionListResponse, Error, InfiniteData<PredictionListResponse>, readonly unknown[], string | undefined>({
    queryKey: queryKeys.predictions(params),
    queryFn: ({ pageParam }) =>
      fetchPredictions({ ...params, after_id: pageParam }),
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => (lastPage.has_more ? lastPage.last_id ?? undefined : undefined),
    staleTime: 60_000,
  })
}

export function useCreatePrediction() {
  return useMutation<Prediction, Error, PredictionRequest>({
    mutationFn: createPrediction,
  })
}
