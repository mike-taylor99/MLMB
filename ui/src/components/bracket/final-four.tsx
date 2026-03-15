// ============================================================================
// FinalFourView — Final Four + Championship (center of the bracket layout)
//
//   [SF1] ──┐         ┌── [SF2]
//           ├── NCG ──┤
//
// SF1 feeds from the left-side regions, SF2 from the right-side regions.
// The championship sits at the true center.
// ============================================================================

import type { FinalFourBracket } from "@/lib/bracket";
import type { Team, Sport } from "@/lib/types";
import { Matchup } from "./matchup";
import { TeamLogo } from "@/components/team-logo";
import { TournamentLogo } from "@/components/tournament-logo";
import { Trophy } from "lucide-react";

interface FinalFourViewProps {
  bracket: FinalFourBracket;
  teamMap: Map<string, Team>;
  /** Optional tournament ID — renders the event logo above the heading */
  tournamentId?: string;
  /** Optional user picks — enables scored mode on each matchup */
  picks?: Record<string, string>;
  /** Optional set of eliminated teams — marks busted picks */
  eliminated?: Set<string>;
  /** Optional analysis IDs keyed by game slot */
  analyses?: Record<string, string>;
  /** Sport code — required when analyses is provided */
  sport?: Sport;
}

export function FinalFourView({
  bracket,
  teamMap,
  tournamentId,
  picks,
  eliminated,
  analyses,
  sport,
}: FinalFourViewProps) {
  const champion = bracket.championship.winner;
  const championTeam = champion ? teamMap.get(champion) : null;
  const championPick = picks?.["NCG"] ?? null;
  const championPickTeam = championPick ? teamMap.get(championPick) : null;

  return (
    <div className="flex flex-col items-center gap-3">
      {tournamentId && <TournamentLogo tournamentId={tournamentId} size={96} />}
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide text-center">
        Final Four
      </h3>

      <div className="flex items-center gap-3">
        {/* SF1 — left side, flows right */}
        <Matchup
          topTeam={bracket.semifinal1.topTeam}
          bottomTeam={bracket.semifinal1.bottomTeam}
          topSeed={bracket.semifinal1.topSeed}
          bottomSeed={bracket.semifinal1.bottomSeed}
          winner={bracket.semifinal1.winner}
          teamMap={teamMap}
          pick={picks?.["FF_G1"]}
          eliminated={eliminated}
          analysisId={analyses?.["FF_G1"]}
          sport={sport}
        />

        {/* Championship — center */}
        <Matchup
          topTeam={bracket.championship.topTeam}
          bottomTeam={bracket.championship.bottomTeam}
          topSeed={bracket.championship.topSeed}
          bottomSeed={bracket.championship.bottomSeed}
          winner={bracket.championship.winner}
          teamMap={teamMap}
          pick={picks?.["NCG"]}
          eliminated={eliminated}
          analysisId={analyses?.["NCG"]}
          sport={sport}
        />

        {/* SF2 — right side, flows left */}
        <Matchup
          topTeam={bracket.semifinal2.topTeam}
          bottomTeam={bracket.semifinal2.bottomTeam}
          topSeed={bracket.semifinal2.topSeed}
          bottomSeed={bracket.semifinal2.bottomSeed}
          winner={bracket.semifinal2.winner}
          teamMap={teamMap}
          pick={picks?.["FF_G2"]}
          eliminated={eliminated}
          analysisId={analyses?.["FF_G2"]}
          sport={sport}
        />
      </div>

      {/* Champion callout — shows actual champion or user's pick */}
      {(champion || championPick) && (
        <div className="flex items-center gap-2 rounded-lg border bg-primary/5 px-3 py-2">
          <Trophy className="h-5 w-5 text-primary shrink-0" />
          {champion ? (
            championTeam ? (
              <>
                <TeamLogo
                  ncaaKey={championTeam.meta.ncaa_key}
                  color={championTeam.meta.color}
                  school={championTeam.meta.school}
                  size={24}
                />
                <div>
                  <div className="text-sm font-bold">
                    {championTeam.meta.school}
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    Champion
                  </div>
                </div>
              </>
            ) : (
              <div className="text-sm font-bold">{champion}</div>
            )
          ) : championPickTeam ? (
            <>
              <TeamLogo
                ncaaKey={championPickTeam.meta.ncaa_key}
                color={championPickTeam.meta.color}
                school={championPickTeam.meta.school}
                size={24}
              />
              <div>
                <div className="text-sm font-bold">
                  {championPickTeam.meta.school}
                </div>
                <div className="text-[10px] text-muted-foreground">
                  Champion Pick
                </div>
              </div>
            </>
          ) : (
            <div className="text-sm font-bold text-muted-foreground">
              {championPick}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
