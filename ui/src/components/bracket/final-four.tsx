// ============================================================================
// FinalFourView — Final Four + Championship matchups
// ============================================================================

import type { FinalFourBracket } from '@/lib/bracket'
import type { Team } from '@/lib/types'
import { Matchup } from './matchup'
import { TeamLogo } from '@/components/team-logo'
import { Trophy } from 'lucide-react'

interface FinalFourViewProps {
  bracket: FinalFourBracket
  teamMap: Map<string, Team>
  /** Optional user picks — enables scored mode on each matchup */
  picks?: Record<string, string>
}

export function FinalFourView({ bracket, teamMap, picks }: FinalFourViewProps) {
  const champion = bracket.championship.winner
  const championTeam = champion ? teamMap.get(champion) : null
  const championPick = picks?.['NCG'] ?? null
  const championPickTeam = championPick ? teamMap.get(championPick) : null

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Final Four &amp; Championship</h3>
      <div className="flex items-center gap-6 flex-wrap">
        {/* Semifinal 1 */}
        <div className="space-y-1">
          <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide px-1">
            Semifinal 1
          </div>
          <Matchup
            topTeam={bracket.semifinal1.topTeam}
            bottomTeam={bracket.semifinal1.bottomTeam}
            topSeed={null}
            bottomSeed={null}
            winner={bracket.semifinal1.winner}
            teamMap={teamMap}
            pick={picks?.['FF_G1']}
          />
        </div>

        {/* Championship */}
        <div className="space-y-1">
          <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide px-1">
            Championship
          </div>
          <Matchup
            topTeam={bracket.championship.topTeam}
            bottomTeam={bracket.championship.bottomTeam}
            topSeed={null}
            bottomSeed={null}
            winner={bracket.championship.winner}
            teamMap={teamMap}
            pick={picks?.['NCG']}
          />
        </div>

        {/* Semifinal 2 */}
        <div className="space-y-1">
          <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide px-1">
            Semifinal 2
          </div>
          <Matchup
            topTeam={bracket.semifinal2.topTeam}
            bottomTeam={bracket.semifinal2.bottomTeam}
            topSeed={null}
            bottomSeed={null}
            winner={bracket.semifinal2.winner}
            teamMap={teamMap}
            pick={picks?.['FF_G2']}
          />
        </div>
      </div>

      {/* Champion callout — shows actual champion or user's pick */}
      {(champion || championPick) && (
        <div className="flex items-center gap-3 rounded-lg border bg-primary/5 px-4 py-3">
          <Trophy className="h-6 w-6 text-primary shrink-0" />
          {champion ? (
            // actual champion known
            championTeam ? (
              <>
                <TeamLogo
                  ncaaKey={championTeam.meta.ncaa_key}
                  color={championTeam.meta.color}
                  school={championTeam.meta.school}
                  size={32}
                />
                <div>
                  <div className="font-bold">{championTeam.meta.school}</div>
                  <div className="text-sm text-muted-foreground">National Champion</div>
                </div>
              </>
            ) : (
              <div className="font-bold">{champion}</div>
            )
          ) : championPickTeam ? (
            // no result yet, show user's champion pick
            <>
              <TeamLogo
                ncaaKey={championPickTeam.meta.ncaa_key}
                color={championPickTeam.meta.color}
                school={championPickTeam.meta.school}
                size={32}
              />
              <div>
                <div className="font-bold">{championPickTeam.meta.school}</div>
                <div className="text-sm text-muted-foreground">Champion Pick</div>
              </div>
            </>
          ) : (
            <div className="font-bold text-muted-foreground">Champion: {championPick}</div>
          )}
        </div>
      )}
    </div>
  )
}
