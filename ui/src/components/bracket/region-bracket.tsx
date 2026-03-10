// ============================================================================
// RegionBracketView — renders all rounds for a single region
//
// Uses the BracketTree component for the classic "spider web" layout
// with connector lines between rounds.
//
// Set `mirrored` for right-side regions (flows right-to-left).
// ============================================================================

import type { RegionBracket, MatchupSlot } from '@/lib/bracket'
import type { Team } from '@/lib/types'
import { cn } from '@/lib/utils'
import { Matchup } from './matchup'
import { BracketTree } from './bracket-tree'

interface RegionBracketViewProps {
  bracket: RegionBracket
  teamMap: Map<string, Team>
  /** Optional user picks — enables scored mode on each matchup */
  picks?: Record<string, string>
  /** Optional set of eliminated teams — marks busted picks */
  eliminated?: Set<string>
  /** Render right-to-left (for right-side bracket regions) */
  mirrored?: boolean
}

export function RegionBracketView({ bracket, teamMap, picks, eliminated, mirrored }: RegionBracketViewProps) {
  const render = (m: MatchupSlot) => (
    <Matchup
      key={m.key}
      topTeam={m.topTeam}
      bottomTeam={m.bottomTeam}
      topSeed={m.topSeed}
      bottomSeed={m.bottomSeed}
      winner={m.winner}
      teamMap={teamMap}
      pick={picks?.[m.key]}
      eliminated={eliminated}
      compact
    />
  )

  return (
    <div className="space-y-2">
      <h3 className={cn('text-sm font-semibold text-muted-foreground uppercase tracking-wide', mirrored && 'text-right')}>
        {bracket.regionName}
      </h3>
      <BracketTree
        r64={bracket.rounds[0].map(render)}
        r32={bracket.rounds[1].map(render)}
        s16={bracket.rounds[2].map(render)}
        e8={render(bracket.rounds[3][0])}
        mirrored={mirrored}
      />
    </div>
  )
}
