// ============================================================================
// Matchup — a single game in the bracket (two teams, winner highlighted)
//
// Optional `pick` prop enables scored mode: shows ✓ for correct picks,
// ✗ for wrong picks when a result (winner) is also present.
// ============================================================================

import { cn } from '@/lib/utils'
import type { Team } from '@/lib/types'
import { TeamLogo } from '@/components/team-logo'
import { Check, X } from 'lucide-react'

interface MatchupTeamProps {
  teamKey: string | null
  seed: number | null
  teamMap: Map<string, Team>
  isWinner: boolean
  isLoser: boolean
  /** This team was the user's pick for this game */
  isPick: boolean
  /** The user's pick for this game was correct */
  isCorrect: boolean | null
}

function MatchupTeam({ teamKey, seed, teamMap, isWinner, isLoser, isPick, isCorrect }: MatchupTeamProps) {
  const team = teamKey ? teamMap.get(teamKey) : null

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 min-w-0',
        isWinner && 'font-semibold',
        isLoser && 'opacity-40',
        isPick && isCorrect === true && 'bg-green-500/10',
        isPick && isCorrect === false && 'bg-destructive/10',
        isPick && isCorrect === null && 'bg-primary/10',
      )}
    >
      {seed && (
        <span className="text-[10px] text-muted-foreground w-4 text-right shrink-0">
          {seed}
        </span>
      )}
      {team ? (
        <>
          <TeamLogo
            ncaaKey={team.meta.ncaa_key}
            color={team.meta.color}
            school={team.meta.school}
            size={20}
          />
          <span className={cn('truncate text-xs', isPick && isCorrect === false && 'line-through')}>
            {team.meta.school}
          </span>
        </>
      ) : teamKey ? (
        <>
          <div className="w-5 h-5 rounded-full bg-muted shrink-0" />
          <span className="truncate text-xs text-muted-foreground">{teamKey}</span>
        </>
      ) : (
        <span className="text-xs text-muted-foreground/50 italic">TBD</span>
      )}
      {isPick && isCorrect === true && (
        <Check className="h-3 w-3 text-green-500 shrink-0 ml-auto" />
      )}
      {isPick && isCorrect === false && (
        <X className="h-3 w-3 text-destructive shrink-0 ml-auto" />
      )}
    </div>
  )
}

interface MatchupProps {
  topTeam: string | null
  bottomTeam: string | null
  topSeed: number | null
  bottomSeed: number | null
  winner: string | null
  teamMap: Map<string, Team>
  compact?: boolean
  /** Optional: user's pick for this game (enables scored mode) */
  pick?: string | null
}

export function Matchup({
  topTeam,
  bottomTeam,
  topSeed,
  bottomSeed,
  winner,
  teamMap,
  compact,
  pick,
}: MatchupProps) {
  const hasResult = winner !== null
  const hasPick = pick != null
  const pickCorrect = hasPick && hasResult ? pick === winner : null

  return (
    <div
      className={cn(
        'rounded-md border bg-card text-card-foreground shadow-xs',
        compact ? 'w-36' : 'w-44',
        hasPick && pickCorrect === true && 'border-green-500/40',
        hasPick && pickCorrect === false && 'border-destructive/40',
      )}
    >
      <MatchupTeam
        teamKey={topTeam}
        seed={topSeed}
        teamMap={teamMap}
        isWinner={hasResult && winner === topTeam}
        isLoser={hasResult && winner !== topTeam}
        isPick={hasPick && pick === topTeam}
        isCorrect={hasPick && pick === topTeam ? pickCorrect : null}
      />
      <div className="border-t" />
      <MatchupTeam
        teamKey={bottomTeam}
        seed={bottomSeed}
        teamMap={teamMap}
        isWinner={hasResult && winner === bottomTeam}
        isLoser={hasResult && winner !== bottomTeam}
        isPick={hasPick && pick === bottomTeam}
        isCorrect={hasPick && pick === bottomTeam ? pickCorrect : null}
      />
    </div>
  )
}
