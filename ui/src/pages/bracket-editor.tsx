// ============================================================================
// BracketEditorPage — create or edit a user bracket
//
// Route: /brackets/:tournamentId/edit        (new bracket)
//        /brackets/:tournamentId/edit/:bracketId  (edit existing)
// ============================================================================

import { useState, useMemo, useCallback, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router'
import { useTournament, useTeams, useBracket, useCreateBracket, useUpdateBracket } from '@/lib/hooks'
import { Matchup } from '@/components/bracket'
import { PickMatchup } from '@/components/bracket/pick-matchup'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowLeft, Save, Loader2, Trophy } from 'lucide-react'
import { TeamLogo } from '@/components/team-logo'
import { cn } from '@/lib/utils'
import type { Team, Tournament } from '@/lib/types'

// ---------------------------------------------------------------------------
// Seed matchup pairings (same as bracket.ts)
// ---------------------------------------------------------------------------

const SEED_MATCHUPS: [number, number][] = [
  [1, 16], [8, 9], [5, 12], [4, 13], [6, 11], [3, 14], [7, 10], [2, 15],
]

// ---------------------------------------------------------------------------
// Helper: resolve the team feeding into a game based on picks
// ---------------------------------------------------------------------------

function resolvePickTeam(
  feederKey: string,
  picks: Record<string, string>,
  results: Record<string, string>,
): string | null {
  // Use tournament result if available, otherwise user pick
  return results[feederKey] ?? picks[feederKey] ?? null
}

// ---------------------------------------------------------------------------
// Build the interactive bracket structure
// ---------------------------------------------------------------------------

interface GameSlot {
  key: string
  round: string
  topSeed: number | null
  bottomSeed: number | null
  topTeam: string | null
  bottomTeam: string | null
  /** Is this game decided by tournament results (not pickable)? */
  locked: boolean
}

function buildInteractiveBracket(
  regionKey: string,
  region: { name: string; seeds: Record<string, string | null> },
  tournament: Tournament,
  picks: Record<string, string>,
): GameSlot[][] {
  const { play_in, results } = tournament

  // Resolve a seed value — check play-in results first, then user picks
  function resolvePickSeed(seedValue: string | null): string | null {
    if (!seedValue) return null
    if (seedValue.startsWith('pi_')) {
      const pi = play_in.find((p) => p.slot === seedValue)
      // Official result takes priority, then user pick
      return pi?.result ?? picks[seedValue] ?? null
    }
    return seedValue
  }

  // R64
  const r64: GameSlot[] = SEED_MATCHUPS.map(([topSeed, bottomSeed], i) => {
    const key = `${regionKey}_R64_G${i + 1}`
    const topRaw = region.seeds[String(topSeed)] ?? null
    const bottomRaw = region.seeds[String(bottomSeed)] ?? null
    return {
      key,
      round: 'R64',
      topSeed,
      bottomSeed,
      topTeam: resolvePickSeed(topRaw),
      bottomTeam: resolvePickSeed(bottomRaw),
      locked: key in results,
    }
  })

  // R32
  const r32: GameSlot[] = Array.from({ length: 4 }, (_, i) => {
    const key = `${regionKey}_R32_G${i + 1}`
    const g1Key = r64[i * 2].key
    const g2Key = r64[i * 2 + 1].key
    return {
      key,
      round: 'R32',
      topSeed: null,
      bottomSeed: null,
      topTeam: resolvePickTeam(g1Key, picks, results),
      bottomTeam: resolvePickTeam(g2Key, picks, results),
      locked: key in results,
    }
  })

  // S16
  const s16: GameSlot[] = Array.from({ length: 2 }, (_, i) => {
    const key = `${regionKey}_S16_G${i + 1}`
    const g1Key = r32[i * 2].key
    const g2Key = r32[i * 2 + 1].key
    return {
      key,
      round: 'S16',
      topSeed: null,
      bottomSeed: null,
      topTeam: resolvePickTeam(g1Key, picks, results),
      bottomTeam: resolvePickTeam(g2Key, picks, results),
      locked: key in results,
    }
  })

  // E8
  const e8Key = `${regionKey}_E8`
  const e8: GameSlot[] = [{
    key: e8Key,
    round: 'E8',
    topSeed: null,
    bottomSeed: null,
    topTeam: resolvePickTeam(s16[0].key, picks, results),
    bottomTeam: resolvePickTeam(s16[1].key, picks, results),
    locked: e8Key in results,
  }]

  return [r64, r32, s16, e8]
}

// ---------------------------------------------------------------------------
// Count filled picks
// ---------------------------------------------------------------------------

function countPicks(picks: Record<string, string>): number {
  return Object.values(picks).filter(Boolean).length
}

// Max picks for a full bracket: 4 regions × 15 + 3 (FF + NCG) = 63
const TOTAL_GAMES = 63

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ROUND_HEADERS = ['Round of 64', 'Round of 32', 'Sweet 16', 'Elite 8']

export function BracketEditorPage() {
  const { tournamentId, bracketId } = useParams<{
    tournamentId: string
    bracketId?: string
  }>()
  const navigate = useNavigate()

  const isEditing = !!bracketId

  // Data fetching
  const { data: tournament, isLoading: loadingT } = useTournament(tournamentId ?? '')
  const sport = tournament?.sport as 'ncaam_basketball' | 'ncaaw_basketball' | undefined
  const { data: teamsData } = useTeams({ sport, limit: 500, enabled: !!sport })
  const { data: existingBracket, isLoading: loadingB } = useBracket(bracketId ?? '')

  // Mutations
  const createMut = useCreateBracket()
  const updateMut = useUpdateBracket()

  // State
  const [name, setName] = useState('')
  const [picks, setPicks] = useState<Record<string, string>>({})
  const [initialized, setInitialized] = useState(false)

  // Initialize from existing bracket
  useEffect(() => {
    if (isEditing && existingBracket && !initialized) {
      setName(existingBracket.name)
      setPicks(existingBracket.picks)
      setInitialized(true)
    }
  }, [isEditing, existingBracket, initialized])

  // Team map
  const teamMap = useMemo(() => {
    const map = new Map<string, Team>()
    for (const t of teamsData?.data ?? []) map.set(t.id, t)
    return map
  }, [teamsData])

  // Merge results + picks for resolving downstream teams
  const mergedPicks = useMemo(() => {
    if (!tournament) return picks
    // Tournament results always take precedence
    return { ...picks, ...tournament.results }
  }, [picks, tournament])

  // Handle a pick
  const handlePick = useCallback(
    (gameKey: string, winner: string) => {
      setPicks((prev) => {
        const next = { ...prev }

        // Set the pick
        next[gameKey] = winner

        // If changing a pick, cascade: clear all downstream picks that depended on
        // the old winner. We do this by finding any game whose teams come from this
        // game's winner and resetting them if the previous winner was different.
        const oldWinner = prev[gameKey]
        if (oldWinner && oldWinner !== winner) {
          // Clear downstream games that had the old winner
          clearDownstream(next, gameKey, oldWinner, tournament)
        }

        return next
      })
    },
    [tournament],
  )

  // Save
  const isSaving = createMut.isPending || updateMut.isPending
  const handleSave = async () => {
    if (!tournamentId || !name.trim()) return
    try {
      if (isEditing && bracketId) {
        await updateMut.mutateAsync({
          bracketId,
          body: { name: name.trim(), picks },
        })
      } else {
        await createMut.mutateAsync({
          tournament_id: tournamentId,
          name: name.trim(),
          picks,
        })
      }
      navigate(`/brackets/${tournamentId}`)
    } catch {
      // Error is shown via mutation state
    }
  }

  // Loading states
  if (loadingT || (isEditing && loadingB)) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    )
  }

  if (!tournament) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-destructive">
          Tournament not found.
        </CardContent>
      </Card>
    )
  }

  const filledPicks = countPicks(picks)
  const unresolvedPlayIns = tournament.play_in.filter((pi) => pi.result === null).length
  const resultsCount = Object.keys(tournament.results).length
  const remainingPicks = TOTAL_GAMES + unresolvedPlayIns - resultsCount

  // Build region brackets
  const regionEntries = Object.entries(tournament.regions)

  // Final four teams
  const ff = tournament.final_four
  const [sf1r1, sf1r2] = ff.semifinal_1
  const [sf2r1, sf2r2] = ff.semifinal_2

  const ffG1Top = resolvePickTeam(`${sf1r1}_E8`, mergedPicks, tournament.results)
  const ffG1Bottom = resolvePickTeam(`${sf1r2}_E8`, mergedPicks, tournament.results)
  const ffG2Top = resolvePickTeam(`${sf2r1}_E8`, mergedPicks, tournament.results)
  const ffG2Bottom = resolvePickTeam(`${sf2r2}_E8`, mergedPicks, tournament.results)
  const ncgTop = resolvePickTeam('FF_G1', mergedPicks, tournament.results)
  const ncgBottom = resolvePickTeam('FF_G2', mergedPicks, tournament.results)

  const ffG1Locked = 'FF_G1' in tournament.results
  const ffG2Locked = 'FF_G2' in tournament.results
  const ncgLocked = 'NCG' in tournament.results

  const champion = mergedPicks['NCG'] ?? null
  const championTeam = champion ? teamMap.get(champion) : null

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-3">
        <Link
          to={`/brackets/${tournamentId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Bracket
        </Link>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight">
              {isEditing ? 'Edit Bracket' : 'New Bracket'}
            </h1>
            <p className="text-sm text-muted-foreground">{tournament.name}</p>
          </div>
        </div>

        {/* Bracket name input */}
        <div className="max-w-sm space-y-1">
          <Input
            placeholder="Enter bracket name…"
            value={name}
            onChange={(e) => setName(e.target.value.slice(0, 50))}
            maxLength={50}
          />
          <div className="flex justify-end">
            <span className={cn('text-xs', name.length >= 50 ? 'text-destructive' : 'text-muted-foreground')}>
              {name.length}/50
            </span>
          </div>
        </div>

        {(createMut.error || updateMut.error) && (
          <p className="text-sm text-destructive">
            {createMut.error?.message || updateMut.error?.message}
          </p>
        )}
      </div>

      {/* Play-in games */}
      {tournament.play_in.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">First Four</h2>
          <div className="flex flex-wrap gap-4">
            {tournament.play_in.map((pi) => {
              const hasResult = pi.result !== null
              return (
                <div key={pi.slot} className="space-y-1">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wide px-1">
                    {pi.region} · Seed {pi.seed}
                  </div>
                  {hasResult ? (
                    <Matchup
                      topTeam={pi.teams[0] ?? null}
                      bottomTeam={pi.teams[1] ?? null}
                      topSeed={pi.seed}
                      bottomSeed={pi.seed}
                      winner={pi.result}
                      teamMap={teamMap}
                    />
                  ) : (
                    <PickMatchup
                      gameKey={pi.slot}
                      topTeam={pi.teams[0] ?? null}
                      bottomTeam={pi.teams[1] ?? null}
                      topSeed={pi.seed}
                      bottomSeed={pi.seed}
                      pick={picks[pi.slot] ?? null}
                      teamMap={teamMap}
                      onPick={handlePick}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Regional brackets */}
      {regionEntries.map(([regionKey, region]) => {
        const rounds = buildInteractiveBracket(regionKey, region, tournament, mergedPicks)
        return (
          <section key={regionKey} className="space-y-3">
            <h3 className="text-lg font-semibold">{region.name} Region</h3>
            <div className="flex gap-3 items-stretch overflow-x-auto pb-2">
              {rounds.map((round, roundIdx) => (
                <div key={roundIdx} className="flex flex-col shrink-0">
                  <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide mb-2 px-1">
                    {ROUND_HEADERS[roundIdx]}
                  </div>
                  <div
                    className="flex flex-col justify-around flex-1"
                    style={{ gap: roundIdx === 0 ? '4px' : undefined }}
                  >
                    {round.map((game) => (
                      <PickMatchup
                        key={game.key}
                        gameKey={game.key}
                        topTeam={game.topTeam}
                        bottomTeam={game.bottomTeam}
                        topSeed={game.topSeed}
                        bottomSeed={game.bottomSeed}
                        pick={mergedPicks[game.key] ?? null}
                        teamMap={teamMap}
                        onPick={handlePick}
                        disabled={game.locked}
                        compact
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )
      })}

      {/* Final Four */}
      <section className="space-y-4">
        <h3 className="text-lg font-semibold">Final Four &amp; Championship</h3>
        <div className="flex items-center gap-6 flex-wrap">
          <div className="space-y-1">
            <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide px-1">
              Semifinal 1
            </div>
            <PickMatchup
              gameKey="FF_G1"
              topTeam={ffG1Top}
              bottomTeam={ffG1Bottom}
              topSeed={null}
              bottomSeed={null}
              pick={mergedPicks['FF_G1'] ?? null}
              teamMap={teamMap}
              onPick={handlePick}
              disabled={ffG1Locked}
            />
          </div>

          <div className="space-y-1">
            <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide px-1">
              Championship
            </div>
            <PickMatchup
              gameKey="NCG"
              topTeam={ncgTop}
              bottomTeam={ncgBottom}
              topSeed={null}
              bottomSeed={null}
              pick={mergedPicks['NCG'] ?? null}
              teamMap={teamMap}
              onPick={handlePick}
              disabled={ncgLocked}
            />
          </div>

          <div className="space-y-1">
            <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide px-1">
              Semifinal 2
            </div>
            <PickMatchup
              gameKey="FF_G2"
              topTeam={ffG2Top}
              bottomTeam={ffG2Bottom}
              topSeed={null}
              bottomSeed={null}
              pick={mergedPicks['FF_G2'] ?? null}
              teamMap={teamMap}
              onPick={handlePick}
              disabled={ffG2Locked}
            />
          </div>
        </div>

        {/* Champion callout */}
        {champion && (
          <div className="flex items-center gap-3 rounded-lg border bg-primary/5 px-4 py-3">
            <Trophy className="h-6 w-6 text-primary shrink-0" />
            {championTeam ? (
              <>
                <TeamLogo
                  ncaaKey={championTeam.meta.ncaa_key}
                  color={championTeam.meta.color}
                  school={championTeam.meta.school}
                  size={32}
                />
                <div>
                  <div className="font-bold">{championTeam.meta.school}</div>
                  <div className="text-sm text-muted-foreground">Your Champion Pick</div>
                </div>
              </>
            ) : (
              <div className="font-bold">{champion}</div>
            )}
          </div>
        )}
      </section>

      {/* Bottom save bar */}
      <div className="sticky bottom-16 md:bottom-0 flex items-center justify-between rounded-lg border bg-background/95 backdrop-blur px-4 py-3">
        <div className="text-sm">
          <span className="font-medium">{filledPicks}</span>
          <span className="text-muted-foreground">/{remainingPicks} picks made</span>
        </div>
        <Button onClick={handleSave} disabled={isSaving || !name.trim()}>
          {isSaving ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : (
            <Save className="h-4 w-4 mr-1" />
          )}
          {isEditing ? 'Save Changes' : 'Create Bracket'}
        </Button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Downstream clearing — when a pick changes, clear any picks that depended
// on the old winner advancing.
// ---------------------------------------------------------------------------

function clearDownstream(
  picks: Record<string, string>,
  _gameKey: string,
  oldWinner: string,
  tournament: Tournament | undefined,
) {
  if (!tournament) return
  // Simple approach: scan all picks and remove any that reference the old winner
  // as a team in a later round. Since the old winner can't advance anymore,
  // any game they were picked to win is now invalid.
  let changed = true
  while (changed) {
    changed = false
    for (const [key, value] of Object.entries(picks)) {
      if (key in tournament.results) continue // don't clear tournament results
      if (value === oldWinner) {
        delete picks[key]
        changed = true
      }
    }
  }
}
