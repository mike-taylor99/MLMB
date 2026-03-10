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
  /** This team was eliminated in an earlier round (shouldn't be here) */
  isEliminated: boolean
}

function MatchupTeam({ teamKey, seed, teamMap, isWinner, isLoser, isPick, isCorrect, isEliminated }: MatchupTeamProps) {
  const team = teamKey ? teamMap.get(teamKey) : null
  // Show as wrong if it's a wrong pick OR the team is eliminated
  const showWrong = (isPick && isCorrect === false) || isEliminated

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 min-w-0',
        isWinner && 'font-semibold',
        isLoser && 'opacity-40',
        isEliminated && !isLoser && 'opacity-40 bg-destructive/10',
        isPick && isCorrect === true && 'bg-green-500/10',
        isPick && isCorrect === false && 'bg-destructive/10',
        isPick && isCorrect === null && !isEliminated && 'bg-primary/10',
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
          <span className={cn('truncate text-xs', showWrong && 'line-through')}>
            {team.meta.school}
          </span>
        </>
      ) : teamKey ? (
        <>
          <div className="w-5 h-5 rounded-full bg-muted shrink-0" />
          <span className={cn('truncate text-xs text-muted-foreground', showWrong && 'line-through')}>{teamKey}</span>
        </>
      ) : (
        <span className="text-xs text-muted-foreground/50 italic">TBD</span>
      )}
      {isPick && isCorrect === true && (
        <Check className="h-3 w-3 text-green-500 shrink-0 ml-auto" />
      )}
      {showWrong && (
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
  /** Optional: set of teams eliminated in earlier rounds (marks busted picks) */
  eliminated?: Set<string>
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
  eliminated,
}: MatchupProps) {
  const hasResult = winner !== null
  const hasPick = pick != null
  // Pick is wrong if there's a result and it doesn't match, OR if the
  // picked team has been eliminated in an earlier round (busted pick).
  const pickBusted = hasPick && !hasResult && eliminated?.has(pick!) === true
  const pickCorrect = hasPick && hasResult
    ? pick === winner
    : pickBusted
      ? false
      : null

  // A team appearing in this slot that was already knocked out
  const topEliminated = !!topTeam && !hasResult && eliminated?.has(topTeam) === true
  const bottomEliminated = !!bottomTeam && !hasResult && eliminated?.has(bottomTeam) === true
  // Border: red if any team is eliminated or pick is wrong
  const hasBustedSlot = topEliminated || bottomEliminated

  return (
    <div
      className={cn(
        'rounded-md border bg-card text-card-foreground shadow-xs',
        compact ? 'w-36' : 'w-44',
        hasPick && pickCorrect === true && 'border-green-500/40',
        (hasPick && pickCorrect === false) || hasBustedSlot ? 'border-destructive/40' : '',
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
        isEliminated={topEliminated}
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
        isEliminated={bottomEliminated}
      />
    </div>
  )
}
