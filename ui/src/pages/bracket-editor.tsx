// ============================================================================
// BracketEditorPage — create or edit a user bracket
//
// Route: /brackets/:tournamentId/edit        (new bracket)
//        /brackets/:tournamentId/edit/:bracketId  (edit existing)
// ============================================================================

import { useState, useMemo, useCallback, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router";
import {
  useTournament,
  useTeams,
  useBracket,
  useCreateBracket,
  useUpdateBracket,
} from "@/lib/hooks";
import {
  Matchup,
  PickMatchup,
  BracketTree,
  BracketFullLayout,
} from "@/components/bracket";
import type { MatchupPredictions } from "@/lib/types";
import { toPredictionScenarios } from "@/components/bracket/pick-matchup";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Save, Loader2, Trophy } from "lucide-react";
import { TeamLogo } from "@/components/team-logo";
import { TournamentLogo } from "@/components/tournament-logo";
import { cn } from "@/lib/utils";
import { createAnalysis } from "@/lib/api";
import { useDocumentTitle } from "@/lib/use-document-title";
import type { Team, Tournament, Sport, Analysis } from "@/lib/types";

// ---------------------------------------------------------------------------
// Seed matchup pairings (same as bracket.ts)
// ---------------------------------------------------------------------------

const SEED_MATCHUPS: [number, number][] = [
  [1, 16],
  [8, 9],
  [5, 12],
  [4, 13],
  [6, 11],
  [3, 14],
  [7, 10],
  [2, 15],
];

// ---------------------------------------------------------------------------
// Helper: resolve the team feeding into a game based on picks
// ---------------------------------------------------------------------------

function resolvePickTeam(
  feederKey: string,
  picks: Record<string, string>,
  results: Record<string, string>,
): string | null {
  // Use tournament result if available, otherwise user pick
  return results[feederKey] ?? picks[feederKey] ?? null;
}

// ---------------------------------------------------------------------------
// Build the interactive bracket structure
// ---------------------------------------------------------------------------

interface GameSlot {
  key: string;
  round: string;
  topSeed: number | null;
  bottomSeed: number | null;
  topTeam: string | null;
  bottomTeam: string | null;
  /** Is this game decided by tournament results (not pickable)? */
  locked: boolean;
}

function buildInteractiveBracket(
  regionKey: string,
  region: { name: string; seeds: Record<string, string | null> },
  tournament: Tournament,
  picks: Record<string, string>,
): GameSlot[][] {
  const { play_in, results } = tournament;

  // Resolve a seed value — check play-in results first, then user picks
  function resolvePickSeed(seedValue: string | null): string | null {
    if (!seedValue) return null;
    if (seedValue.startsWith("pi_")) {
      const pi = play_in.find((p) => p.slot === seedValue);
      // Official result takes priority, then user pick
      return pi?.result ?? picks[seedValue] ?? null;
    }
    return seedValue;
  }

  // Build team→seed reverse map for propagating seeds to later rounds
  const seedMap = new Map<string, number>();
  for (const [seedStr, rawValue] of Object.entries(region.seeds)) {
    if (!rawValue) continue;
    const teamKey = resolvePickSeed(rawValue);
    if (teamKey) seedMap.set(teamKey, Number(seedStr));
  }

  // R64
  const r64: GameSlot[] = SEED_MATCHUPS.map(([topSeed, bottomSeed], i) => {
    const key = `${regionKey}_R64_G${i + 1}`;
    const topRaw = region.seeds[String(topSeed)] ?? null;
    const bottomRaw = region.seeds[String(bottomSeed)] ?? null;
    return {
      key,
      round: "R64",
      topSeed,
      bottomSeed,
      topTeam: resolvePickSeed(topRaw),
      bottomTeam: resolvePickSeed(bottomRaw),
      locked: key in results,
    };
  });

  // R32
  const r32: GameSlot[] = Array.from({ length: 4 }, (_, i) => {
    const key = `${regionKey}_R32_G${i + 1}`;
    const g1Key = r64[i * 2].key;
    const g2Key = r64[i * 2 + 1].key;
    const topTeam = resolvePickTeam(g1Key, picks, results);
    const bottomTeam = resolvePickTeam(g2Key, picks, results);
    return {
      key,
      round: "R32",
      topSeed: topTeam ? (seedMap.get(topTeam) ?? null) : null,
      bottomSeed: bottomTeam ? (seedMap.get(bottomTeam) ?? null) : null,
      topTeam,
      bottomTeam,
      locked: key in results,
    };
  });

  // S16
  const s16: GameSlot[] = Array.from({ length: 2 }, (_, i) => {
    const key = `${regionKey}_S16_G${i + 1}`;
    const g1Key = r32[i * 2].key;
    const g2Key = r32[i * 2 + 1].key;
    const topTeam = resolvePickTeam(g1Key, picks, results);
    const bottomTeam = resolvePickTeam(g2Key, picks, results);
    return {
      key,
      round: "S16",
      topSeed: topTeam ? (seedMap.get(topTeam) ?? null) : null,
      bottomSeed: bottomTeam ? (seedMap.get(bottomTeam) ?? null) : null,
      topTeam,
      bottomTeam,
      locked: key in results,
    };
  });

  // E8
  const e8Key = `${regionKey}_E8`;
  const e8Top = resolvePickTeam(s16[0].key, picks, results);
  const e8Bottom = resolvePickTeam(s16[1].key, picks, results);
  const e8: GameSlot[] = [
    {
      key: e8Key,
      round: "E8",
      topSeed: e8Top ? (seedMap.get(e8Top) ?? null) : null,
      bottomSeed: e8Bottom ? (seedMap.get(e8Bottom) ?? null) : null,
      topTeam: e8Top,
      bottomTeam: e8Bottom,
      locked: e8Key in results,
    },
  ];

  return [r64, r32, s16, e8];
}

// ---------------------------------------------------------------------------
// Count filled picks
// ---------------------------------------------------------------------------

function countPicks(picks: Record<string, string>): number {
  return Object.values(picks).filter(Boolean).length;
}

// Max picks for a full bracket: 4 regions × 15 + 3 (FF + NCG) = 63
const TOTAL_GAMES = 63;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function BracketEditorPage() {
  const { tournamentId, bracketId } = useParams<{
    tournamentId: string;
    bracketId?: string;
  }>();
  const navigate = useNavigate();

  const isEditing = !!bracketId;

  // Data fetching
  const { data: tournament, isLoading: loadingT } = useTournament(
    tournamentId ?? "",
  );
  useDocumentTitle(
    tournament
      ? isEditing
        ? `Edit Bracket · ${tournament.name}`
        : `New Bracket · ${tournament.name}`
      : undefined,
  );
  const sport = tournament?.sport as
    | "ncaam_basketball"
    | "ncaaw_basketball"
    | undefined;
  const { data: teamsData } = useTeams({ sport, limit: 500, enabled: !!sport });
  const { data: existingBracket, isLoading: loadingB } = useBracket(
    bracketId ?? "",
  );

  // Mutations
  const createMut = useCreateBracket();
  const updateMut = useUpdateBracket();

  // State
  const [name, setName] = useState("");
  const [picks, setPicks] = useState<Record<string, string>>({});
  const [initialized, setInitialized] = useState(false);

  // ML prediction state
  const [predictions, setPredictions] = useState<
    Record<string, MatchupPredictions>
  >({});
  const [analyses, setAnalyses] = useState<Record<string, Analysis>>({});
  const [loadingPredictions, setLoadingPredictions] = useState<Set<string>>(
    new Set(),
  );

  // Initialize from existing bracket
  useEffect(() => {
    if (isEditing && existingBracket && !initialized) {
      setName(existingBracket.name);
      setPicks(existingBracket.picks);
      setInitialized(true);
    }
  }, [isEditing, existingBracket, initialized]);

  // Team map
  const teamMap = useMemo(() => {
    const map = new Map<string, Team>();
    for (const t of teamsData?.data ?? []) map.set(t.id, t);
    return map;
  }, [teamsData]);

  // Merge results + picks for resolving downstream teams
  const mergedPicks = useMemo(() => {
    if (!tournament) return picks;
    // Tournament results always take precedence
    return { ...picks, ...tournament.results };
  }, [picks, tournament]);

  // Build combined team→seed map from all regions for FF/NCG seed display
  const allSeeds = useMemo(() => {
    if (!tournament) return new Map<string, number>();
    const map = new Map<string, number>();
    for (const region of Object.values(tournament.regions)) {
      for (const [seedStr, rawValue] of Object.entries(region.seeds)) {
        if (!rawValue) continue;
        let teamKey: string | null = rawValue;
        if (rawValue.startsWith("pi_")) {
          const pi = tournament.play_in.find((p) => p.slot === rawValue);
          teamKey = pi?.result ?? mergedPicks[rawValue] ?? null;
        }
        if (teamKey) map.set(teamKey, Number(seedStr));
      }
    }
    return map;
  }, [tournament, mergedPicks]);

  // Handle a pick
  const handlePick = useCallback(
    (gameKey: string, winner: string) => {
      setPicks((prev) => {
        const next = { ...prev };

        // Set the pick
        next[gameKey] = winner;

        // If changing a pick, cascade: clear all downstream picks that depended on
        // the old winner. We do this by finding any game whose teams come from this
        // game's winner and resetting them if the previous winner was different.
        const oldWinner = prev[gameKey];
        if (oldWinner && oldWinner !== winner) {
          // Clear downstream games that had the old winner
          clearDownstream(next, gameKey, oldWinner, tournament);
          // Also clear stale predictions for downstream games whose teams changed
          setPredictions((prevP) => {
            const nextP = { ...prevP };
            for (const key of Object.keys(nextP)) {
              if (key === gameKey) continue;
              if (getRoundIndex(key) > getRoundIndex(gameKey)) {
                delete nextP[key];
              }
            }
            return nextP;
          });
          setAnalyses((prevA) => {
            const nextA = { ...prevA };
            for (const key of Object.keys(nextA)) {
              if (key === gameKey) continue;
              if (getRoundIndex(key) > getRoundIndex(gameKey)) {
                delete nextA[key];
              }
            }
            return nextA;
          });
        }

        return next;
      });
    },
    [tournament],
  );

  // Request ML predictions — single analysis call (replaces 6 individual requests)
  const handleRequestPredictions = useCallback(
    async (gameKey: string, topTeam: string, bottomTeam: string) => {
      if (!sport) return;

      // Determine home/away and neutral based on tournament context.
      // Women's tournament: R64 & R32 are hosted by the top-4 seeds,
      // so the 1–4 seed is the home team and the game is NOT neutral.
      let homeTeam = topTeam;
      let awayTeam = bottomTeam;
      let neutral = true;

      if (sport === "ncaaw_basketball") {
        // Extract round from game key — handles region keys with underscores
        // e.g. "fort_worth_1_R64_G1" or "albany_R64_G1"
        const parts = gameKey.split("_");
        const round = parts.find((p) => /^(R64|R32|S16|E8|FF)$/.test(p));
        if (round === "R64" || round === "R32") {
          const topSeed = allSeeds.get(topTeam);
          const bottomSeed = allSeeds.get(bottomTeam);
          if (topSeed && topSeed <= 4) {
            homeTeam = topTeam;
            awayTeam = bottomTeam;
            neutral = false;
          } else if (bottomSeed && bottomSeed <= 4) {
            homeTeam = bottomTeam;
            awayTeam = topTeam;
            neutral = false;
          }
        }
      }

      setLoadingPredictions((prev) => new Set(prev).add(gameKey));

      try {
        const result = await createAnalysis({
          home_team: homeTeam,
          away_team: awayTeam,
          neutral,
          sport: sport as Sport,
        });

        // Convert analysis predictions to PredictionScenario format
        const scenarios = toPredictionScenarios(result.predictions, topTeam);

        if (scenarios.length > 0) {
          setPredictions((prev) => ({ ...prev, [gameKey]: { scenarios } }));
        }
        setAnalyses((prev) => ({ ...prev, [gameKey]: result }));
      } finally {
        setLoadingPredictions((prev) => {
          const next = new Set(prev);
          next.delete(gameKey);
          return next;
        });
      }
    },
    [sport, allSeeds],
  );

  // Save
  const isSaving = createMut.isPending || updateMut.isPending;
  const handleSave = async () => {
    if (!tournamentId || !name.trim()) return;
    try {
      let savedId: string;
      if (isEditing && bracketId) {
        const saved = await updateMut.mutateAsync({
          bracketId,
          body: { name: name.trim(), picks },
        });
        savedId = saved.id;
      } else {
        const saved = await createMut.mutateAsync({
          tournament_id: tournamentId,
          name: name.trim(),
          picks,
        });
        savedId = saved.id;
      }
      navigate(`/brackets/${tournamentId}/view/${savedId}`);
    } catch {
      // Error is shown via mutation state
    }
  };

  // Loading states
  if (loadingT || (isEditing && loadingB)) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (!tournament) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-destructive">
          Tournament not found.
        </CardContent>
      </Card>
    );
  }

  const filledPicks = countPicks(picks);
  const unresolvedPlayIns = tournament.play_in.filter(
    (pi) => pi.result === null,
  ).length;
  const resultsCount = Object.keys(tournament.results).length;
  const remainingPicks = TOTAL_GAMES + unresolvedPlayIns - resultsCount;

  // Final four teams
  const ff = tournament.final_four;
  const [sf1r1, sf1r2] = ff.semifinal_1;
  const [sf2r1, sf2r2] = ff.semifinal_2;

  const ffG1Top = resolvePickTeam(
    `${sf1r1}_E8`,
    mergedPicks,
    tournament.results,
  );
  const ffG1Bottom = resolvePickTeam(
    `${sf1r2}_E8`,
    mergedPicks,
    tournament.results,
  );
  const ffG2Top = resolvePickTeam(
    `${sf2r1}_E8`,
    mergedPicks,
    tournament.results,
  );
  const ffG2Bottom = resolvePickTeam(
    `${sf2r2}_E8`,
    mergedPicks,
    tournament.results,
  );
  const ncgTop = resolvePickTeam("FF_G1", mergedPicks, tournament.results);
  const ncgBottom = resolvePickTeam("FF_G2", mergedPicks, tournament.results);

  const ffG1Locked = "FF_G1" in tournament.results;
  const ffG2Locked = "FF_G2" in tournament.results;
  const ncgLocked = "NCG" in tournament.results;

  const champion = mergedPicks["NCG"] ?? null;
  const championTeam = champion ? teamMap.get(champion) : null;

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
              {isEditing ? "Edit Bracket" : "New Bracket"}
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
            <span
              className={cn(
                "text-xs",
                name.length >= 50
                  ? "text-destructive"
                  : "text-muted-foreground",
              )}
            >
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

      {/* Full bracket layout — 4 regions in corners, FF center */}
      {(() => {
        const [sf1r1, sf1r2] = tournament.final_four.semifinal_1;
        const [sf2r1, sf2r2] = tournament.final_four.semifinal_2;

        const buildRegion = (regionKey: string, mirrored: boolean) => {
          const region = tournament.regions[regionKey];
          if (!region) return null;
          const rounds = buildInteractiveBracket(
            regionKey,
            region,
            tournament,
            mergedPicks,
          );
          const pick = (game: GameSlot) => (
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
              predictions={predictions[game.key]}
              analysis={analyses[game.key]}
              onRequestPredictions={handleRequestPredictions}
              predictionsLoading={loadingPredictions.has(game.key)}
            />
          );
          return (
            <div className="space-y-2">
              <h3
                className={cn(
                  "text-sm font-semibold text-muted-foreground uppercase tracking-wide",
                  mirrored && "text-right",
                )}
              >
                {region.name}
              </h3>
              <BracketTree
                r64={rounds[0].map(pick)}
                r32={rounds[1].map(pick)}
                s16={rounds[2].map(pick)}
                e8={pick(rounds[3][0])}
                mirrored={mirrored}
              />
            </div>
          );
        };

        const firstFourHeader =
          tournament.play_in.length > 0 ? (
            <section className="space-y-3">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide text-center">
                First Four
              </h3>
              <div className="flex flex-wrap gap-4 justify-center">
                {tournament.play_in.map((pi) => {
                  const hasResult = pi.result !== null;
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
                          predictions={predictions[pi.slot]}
                          analysis={analyses[pi.slot]}
                          onRequestPredictions={handleRequestPredictions}
                          predictionsLoading={loadingPredictions.has(pi.slot)}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          ) : undefined;

        return (
          <BracketFullLayout
            topLeft={buildRegion(sf1r1, false)}
            bottomLeft={buildRegion(sf1r2, false)}
            topRight={buildRegion(sf2r1, true)}
            bottomRight={buildRegion(sf2r2, true)}
            header={firstFourHeader}
            center={
              <div className="flex flex-col items-center gap-3">
                <TournamentLogo tournamentId={tournamentId!} size={96} />
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide text-center">
                  Final Four
                </h3>
                <div className="flex items-center gap-3">
                  {/* SF1 — left side, feeds from left regions */}
                  <PickMatchup
                    gameKey="FF_G1"
                    topTeam={ffG1Top}
                    bottomTeam={ffG1Bottom}
                    topSeed={ffG1Top ? (allSeeds.get(ffG1Top) ?? null) : null}
                    bottomSeed={
                      ffG1Bottom ? (allSeeds.get(ffG1Bottom) ?? null) : null
                    }
                    pick={mergedPicks["FF_G1"] ?? null}
                    teamMap={teamMap}
                    onPick={handlePick}
                    disabled={ffG1Locked}
                    predictions={predictions["FF_G1"]}
                    analysis={analyses["FF_G1"]}
                    onRequestPredictions={handleRequestPredictions}
                    predictionsLoading={loadingPredictions.has("FF_G1")}
                  />

                  {/* Championship — center */}
                  <PickMatchup
                    gameKey="NCG"
                    topTeam={ncgTop}
                    bottomTeam={ncgBottom}
                    topSeed={ncgTop ? (allSeeds.get(ncgTop) ?? null) : null}
                    bottomSeed={
                      ncgBottom ? (allSeeds.get(ncgBottom) ?? null) : null
                    }
                    pick={mergedPicks["NCG"] ?? null}
                    teamMap={teamMap}
                    onPick={handlePick}
                    disabled={ncgLocked}
                    predictions={predictions["NCG"]}
                    analysis={analyses["NCG"]}
                    onRequestPredictions={handleRequestPredictions}
                    predictionsLoading={loadingPredictions.has("NCG")}
                  />

                  {/* SF2 — right side, feeds from right regions */}
                  <PickMatchup
                    gameKey="FF_G2"
                    topTeam={ffG2Top}
                    bottomTeam={ffG2Bottom}
                    topSeed={ffG2Top ? (allSeeds.get(ffG2Top) ?? null) : null}
                    bottomSeed={
                      ffG2Bottom ? (allSeeds.get(ffG2Bottom) ?? null) : null
                    }
                    pick={mergedPicks["FF_G2"] ?? null}
                    teamMap={teamMap}
                    onPick={handlePick}
                    disabled={ffG2Locked}
                    predictions={predictions["FF_G2"]}
                    analysis={analyses["FF_G2"]}
                    onRequestPredictions={handleRequestPredictions}
                    predictionsLoading={loadingPredictions.has("FF_G2")}
                  />
                </div>
                {/* Champion callout */}
                {champion && (
                  <div className="flex items-center gap-2 rounded-lg border bg-primary/5 px-3 py-2">
                    <Trophy className="h-5 w-5 text-primary shrink-0" />
                    {championTeam ? (
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
                            Your Champion Pick
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="text-sm font-bold">{champion}</div>
                    )}
                  </div>
                )}
              </div>
            }
          />
        );
      })()}

      {/* Bottom save bar */}
      <div className="sticky bottom-16 md:bottom-0 flex items-center justify-between rounded-lg border bg-background/95 backdrop-blur px-4 py-3">
        <div className="text-sm">
          <span className="font-medium">{filledPicks}</span>
          <span className="text-muted-foreground">
            /{remainingPicks} picks made
          </span>
        </div>
        <Button onClick={handleSave} disabled={isSaving || !name.trim()}>
          {isSaving ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : (
            <Save className="h-4 w-4 mr-1" />
          )}
          {isEditing ? "Save Changes" : "Create Bracket"}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Downstream clearing — when a pick changes, clear any picks that depended
// on the old winner advancing, but only in rounds AFTER the current game.
// ---------------------------------------------------------------------------

/** Order of rounds — higher index = later round */
const ROUND_ORDER = ["pi", "R64", "R32", "S16", "E8", "FF", "NCG"] as const;

function getRoundIndex(gameKey: string): number {
  if (gameKey.startsWith("pi_")) return 0;
  if (gameKey === "NCG") return 6;
  if (gameKey.startsWith("FF_")) return 5;
  // Region keys like "south_R64_G1" — extract round part
  const parts = gameKey.split("_");
  const round = parts[1]; // R64, R32, S16, E8
  return ROUND_ORDER.indexOf(round as (typeof ROUND_ORDER)[number]);
}

function clearDownstream(
  picks: Record<string, string>,
  gameKey: string,
  oldWinner: string,
  tournament: Tournament | undefined,
) {
  if (!tournament) return;
  const currentRoundIdx = getRoundIndex(gameKey);

  // Only clear picks that are in later rounds AND had the old winner as their value
  let changed = true;
  while (changed) {
    changed = false;
    for (const [key, value] of Object.entries(picks)) {
      if (key in tournament.results) continue; // don't clear tournament results
      if (getRoundIndex(key) <= currentRoundIdx) continue; // don't clear same or earlier rounds
      if (value === oldWinner) {
        delete picks[key];
        changed = true;
      }
    }
  }
}
