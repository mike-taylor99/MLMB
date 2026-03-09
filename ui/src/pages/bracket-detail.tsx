// ============================================================================
// BracketDetail page — full bracket view for a tournament
// ============================================================================

import { useMemo } from 'react'
import { useParams, Link } from 'react-router'
import { useAuth } from '@/context/auth'
import { useTournament, useTeams, useBrackets, useDeleteBracket } from '@/lib/hooks'
import { buildRegionBracket, buildFinalFour } from '@/lib/bracket'
import { Matchup, RegionBracketView, FinalFourView } from '@/components/bracket'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowLeft, Lock, Unlock, Plus, Pencil, Trash2 } from 'lucide-react'
import type { Team } from '@/lib/types'

export function BracketDetailPage() {
  const { tournamentId } = useParams<{ tournamentId: string }>()
  const { data: tournament, isLoading, error } = useTournament(tournamentId ?? '')
  const sport = tournament?.sport as 'ncaam_basketball' | 'ncaaw_basketball' | undefined
  const { data: teamsData } = useTeams({ sport, limit: 500, enabled: !!sport })

  // Auth + user brackets
  const { user, isLocal } = useAuth()
  const isAuthenticated = !!user || isLocal
  const { data: bracketsData } = useBrackets(tournamentId)
  const deleteMut = useDeleteBracket()

  // Team lookup map
  const teamMap = useMemo(() => {
    const map = new Map<string, Team>()
    for (const t of teamsData?.data ?? []) {
      map.set(t.id, t)
    }
    return map
  }, [teamsData])

  // Build bracket data
  const regionBrackets = useMemo(() => {
    if (!tournament) return []
    return Object.entries(tournament.regions).map(([key, region]) =>
      buildRegionBracket(key, region, tournament),
    )
  }, [tournament])

  const finalFour = useMemo(() => {
    if (!tournament) return null
    return buildFinalFour(tournament)
  }, [tournament])

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-destructive">
          Failed to load tournament.
        </CardContent>
      </Card>
    )
  }

  if (isLoading || !tournament) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    )
  }

  const hasResults = Object.keys(tournament.results).length > 0
  const totalGames = Object.keys(tournament.results).length
  const isComplete = tournament.results['NCG'] !== undefined

  // Check if all seeds are filled (bracket is ready for picks)
  const seedsFilled = Object.values(tournament.regions).every((region) =>
    Object.values(region.seeds).every((v) => v != null),
  )

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-3">
        <Link
          to="/brackets"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          All Brackets
        </Link>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{tournament.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-xs">
                {tournament.sport === 'ncaam_basketball' ? "Men's" : "Women's"}
              </Badge>
              <Badge
                variant={tournament.is_locked ? 'secondary' : 'default'}
                className="text-xs"
              >
                {tournament.is_locked ? (
                  <span className="flex items-center gap-1">
                    <Lock className="h-3 w-3" /> Locked
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <Unlock className="h-3 w-3" /> Open
                  </span>
                )}
              </Badge>
              {hasResults && (
                <span className="text-sm text-muted-foreground">
                  {isComplete ? '✓ Complete' : `${totalGames} games played`}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* My Brackets */}
      {isAuthenticated && (bracketsData?.data.length || !tournament.is_locked) && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">My Brackets</h2>
            {!tournament.is_locked && seedsFilled && (
              <Button asChild size="sm">
                <Link to={`/brackets/${tournamentId}/edit`}>
                  <Plus className="h-4 w-4 mr-1" />
                  New Bracket
                </Link>
              </Button>
            )}
          </div>
          {!seedsFilled && !tournament.is_locked && (
            <Card>
              <CardContent className="py-6 text-center text-muted-foreground">
                Seeds haven't been announced yet. Check back once the field is set!
              </CardContent>
            </Card>
          )}
          {bracketsData && bracketsData.data.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {bracketsData.data.map((b) => (
                <Link key={b.id} to={`/brackets/${tournamentId}/view/${b.id}`} className="block">
                  <Card className="transition-colors hover:border-primary/40">
                    <CardContent className="flex items-center justify-between p-4">
                      <div className="min-w-0">
                        <div className="font-medium truncate">{b.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {Object.keys(b.picks).length} picks ·{' '}
                          {tournament.is_locked
                            ? 'Locked'
                            : new Date(b.updated_at).toLocaleDateString()}
                        </div>
                      </div>
                      {!tournament.is_locked && seedsFilled && (
                        <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.preventDefault()}>
                          <Button asChild variant="ghost" size="icon">
                            <Link to={`/brackets/${tournamentId}/edit/${b.id}`}>
                              <Pencil className="h-4 w-4" />
                            </Link>
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => {
                              if (confirm('Delete this bracket?')) {
                                deleteMut.mutate({ bracketId: b.id, tournamentId: tournamentId! })
                              }
                            }}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          ) : !tournament.is_locked && seedsFilled ? (
            <Card>
              <CardContent className="py-6 text-center text-muted-foreground">
                You haven't created any brackets yet.
              </CardContent>
            </Card>
          ) : null}
        </section>
      )}

      {/* Play-in games */}
      {tournament.play_in.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">First Four</h2>
          <div className="flex flex-wrap gap-4">
            {tournament.play_in.map((pi) => (
              <div key={pi.slot} className="space-y-1">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wide px-1">
                  {pi.region} · Seed {pi.seed}
                </div>
                <Matchup
                  topTeam={pi.teams[0] ?? null}
                  bottomTeam={pi.teams[1] ?? null}
                  topSeed={pi.seed}
                  bottomSeed={pi.seed}
                  winner={pi.result}
                  teamMap={teamMap}
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Regional brackets */}
      {regionBrackets.map((rb) => (
        <section key={rb.regionKey}>
          <RegionBracketView bracket={rb} teamMap={teamMap} />
        </section>
      ))}

      {/* Final Four */}
      {finalFour && (
        <section>
          <FinalFourView bracket={finalFour} teamMap={teamMap} />
        </section>
      )}
    </div>
  )
}
