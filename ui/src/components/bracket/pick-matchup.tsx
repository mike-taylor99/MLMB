// ============================================================================
// PickMatchup — an interactive matchup where the user clicks to pick a winner
// ============================================================================

import { cn } from '@/lib/utils'
import type { Team } from '@/lib/types'
import { TeamLogo } from '@/components/team-logo'

interface PickTeamProps {
  teamKey: string | null
  seed: number | null
  teamMap: Map<string, Team>
  isPicked: boolean
  isEliminated: boolean
  onClick: () => void
  disabled: boolean
}

function PickTeam({
  teamKey,
  seed,
  teamMap,
  isPicked,
  isEliminated,
  onClick,
  disabled,
}: PickTeamProps) {
  const team = teamKey ? teamMap.get(teamKey) : null
  const canClick = teamKey !== null && !disabled

  return (
    <button
      type="button"
      onClick={canClick ? onClick : undefined}
      disabled={!canClick}
      className={cn(
        'flex items-center gap-1.5 px-2 py-1.5 min-w-0 w-full text-left transition-colors',
        canClick && 'hover:bg-primary/15 cursor-pointer',
        isPicked && 'bg-primary/10 font-semibold',
        isEliminated && 'opacity-30',
        !canClick && 'cursor-default',
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
          <span className="truncate text-xs">{team.meta.school}</span>
          {canClick && !isPicked && !isEliminated && (
            <span className="ml-auto text-[10px] text-primary/60 shrink-0">▸</span>
          )}
        </>
      ) : teamKey ? (
        <>
          <div className="w-5 h-5 rounded-full bg-muted shrink-0" />
          <span className="truncate text-xs text-muted-foreground">{teamKey}</span>
        </>
      ) : (
        <span className="text-xs text-muted-foreground/50 italic">TBD</span>
      )}
    </button>
  )
}

interface PickMatchupProps {
  gameKey: string
  topTeam: string | null
  bottomTeam: string | null
  topSeed: number | null
  bottomSeed: number | null
  pick: string | null
  teamMap: Map<string, Team>
  onPick: (gameKey: string, winner: string) => void
  disabled?: boolean
  compact?: boolean
}

export function PickMatchup({
  gameKey,
  topTeam,
  bottomTeam,
  topSeed,
  bottomSeed,
  pick,
  teamMap,
  onPick,
  disabled = false,
  compact,
}: PickMatchupProps) {
  const needsPick = !disabled && pick === null && topTeam !== null && bottomTeam !== null

  return (
    <div
      className={cn(
        'rounded-md border bg-card text-card-foreground shadow-xs transition-colors',
        compact ? 'w-36' : 'w-44',
        needsPick && 'border-primary/50 ring-1 ring-primary/25',
      )}
    >
      <PickTeam
        teamKey={topTeam}
        seed={topSeed}
        teamMap={teamMap}
        isPicked={pick === topTeam && topTeam !== null}
        isEliminated={pick !== null && pick !== topTeam && topTeam !== null}
        onClick={() => topTeam && onPick(gameKey, topTeam)}
        disabled={disabled}
      />
      <div className="border-t" />
      <PickTeam
        teamKey={bottomTeam}
        seed={bottomSeed}
        teamMap={teamMap}
        isPicked={pick === bottomTeam && bottomTeam !== null}
        isEliminated={pick !== null && pick !== bottomTeam && bottomTeam !== null}
        onClick={() => bottomTeam && onPick(gameKey, bottomTeam)}
        disabled={disabled}
      />
    </div>
  )
}
