// ============================================================================
// TanStack Query hooks — one hook per API call
// ============================================================================

import {
  useQuery,
  useMutation,
  useInfiniteQuery,
  useQueryClient,
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
  fetchTournaments,
  fetchTournament,
  fetchBrackets,
  fetchBracket,
  fetchPublicBracket,
  createBracket,
  updateBracket,
  deleteBracket,
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
  TournamentListResponse,
  Tournament,
  BracketListResponse,
  Bracket,
  CreateBracketRequest,
  UpdateBracketRequest,
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
  tournaments: ['tournaments'] as const,
  tournament: (id: string) => ['tournaments', id] as const,
  brackets: (tournamentId?: string) => ['brackets', tournamentId] as const,
  bracket: (id: string) => ['brackets', 'detail', id] as const,
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
  const { enabled, ...fetchParams } = params
  return useQuery({
    queryKey: queryKeys.teams(fetchParams),
    queryFn: () => fetchTeams(fetchParams),
    staleTime: 5 * 60_000, // teams rarely change
    enabled: enabled ?? true,
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

// ---------------------------------------------------------------------------
// Tournaments
// ---------------------------------------------------------------------------

export function useTournaments() {
  return useQuery<TournamentListResponse>({
    queryKey: queryKeys.tournaments,
    queryFn: fetchTournaments,
    staleTime: 5 * 60_000,
  })
}

export function useTournament(id: string) {
  return useQuery<Tournament>({
    queryKey: queryKeys.tournament(id),
    queryFn: () => fetchTournament(id),
    staleTime: 5 * 60_000,
    enabled: !!id,
  })
}

// ---------------------------------------------------------------------------
// Brackets
// ---------------------------------------------------------------------------

export function useBrackets(tournamentId?: string) {
  return useQuery<BracketListResponse>({
    queryKey: queryKeys.brackets(tournamentId),
    queryFn: () => fetchBrackets(tournamentId),
    staleTime: 60_000,
  })
}

export function useBracket(bracketId: string) {
  return useQuery<Bracket>({
    queryKey: queryKeys.bracket(bracketId),
    queryFn: () => fetchBracket(bracketId),
    staleTime: 60_000,
    enabled: !!bracketId,
  })
}

export function usePublicBracket(tournamentId?: string, bracketId?: string) {
  return useQuery<Bracket>({
    queryKey: ['public-bracket', tournamentId, bracketId],
    queryFn: () => fetchPublicBracket(tournamentId!, bracketId!),
    staleTime: 60_000,
    enabled: !!tournamentId && !!bracketId,
  })
}

export function useCreateBracket() {
  const qc = useQueryClient()
  return useMutation<Bracket, Error, CreateBracketRequest>({
    mutationFn: createBracket,
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.brackets(vars.tournament_id) })
    },
  })
}

export function useUpdateBracket() {
  const qc = useQueryClient()
  return useMutation<Bracket, Error, { bracketId: string; body: UpdateBracketRequest }>({
    mutationFn: ({ bracketId, body }) => updateBracket(bracketId, body),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.bracket(data.id), data)
      qc.invalidateQueries({ queryKey: queryKeys.brackets(data.tournament_id) })
    },
  })
}

export function useDeleteBracket() {
  const qc = useQueryClient()
  return useMutation<void, Error, { bracketId: string; tournamentId: string }>({
    mutationFn: ({ bracketId }) => deleteBracket(bracketId),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.brackets(vars.tournamentId) })
    },
  })
}
