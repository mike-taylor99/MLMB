// ============================================================================
// RegionBracketView — renders all rounds for a single region
//
// Layout: R64 (8 games) → R32 (4) → S16 (2) → E8 (1)
// Each round column stretches to the same height so that justify-around
// vertically centers matchups opposite their feeder games.
// ============================================================================

import type { RegionBracket } from '@/lib/bracket'
import type { Team } from '@/lib/types'
import { Matchup } from './matchup'

interface RegionBracketViewProps {
  bracket: RegionBracket
  teamMap: Map<string, Team>
  /** Optional user picks — enables scored mode on each matchup */
  picks?: Record<string, string>
}

const ROUND_HEADERS = ['Round of 64', 'Round of 32', 'Sweet 16', 'Elite 8']

export function RegionBracketView({ bracket, teamMap, picks }: RegionBracketViewProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold">{bracket.regionName} Region</h3>
      <div className="flex gap-3 items-stretch overflow-x-auto pb-2">
        {bracket.rounds.map((round, roundIdx) => (
          <div key={roundIdx} className="flex flex-col shrink-0">
            <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide mb-2 px-1">
              {ROUND_HEADERS[roundIdx]}
            </div>
            <div
              className="flex flex-col justify-around flex-1"
              style={{ gap: roundIdx === 0 ? '4px' : undefined }}
            >
              {round.map((matchup) => (
                <Matchup
                  key={matchup.key}
                  topTeam={matchup.topTeam}
                  bottomTeam={matchup.bottomTeam}
                  topSeed={matchup.topSeed}
                  bottomSeed={matchup.bottomSeed}
                  winner={matchup.winner}
                  teamMap={teamMap}
                  pick={picks?.[matchup.key]}
                  compact
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
