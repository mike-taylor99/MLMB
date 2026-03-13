// ============================================================================
// Bracket utilities — pure functions for resolving seeds, matchups, and scores
// ============================================================================

import type { Tournament, RegionDef, PlayInGame } from "./types";

// ---------------------------------------------------------------------------
// Resolve a seed value to an actual team key
// ---------------------------------------------------------------------------

/**
 * Resolve a seed string to a team key.
 * Seeds can be a team key directly, or a play-in reference like "pi_1".
 */
export function resolveSeed(
  seedValue: string | null,
  playIns: PlayInGame[],
): string | null {
  if (!seedValue) return null;
  if (seedValue.startsWith("pi_")) {
    const pi = playIns.find((p) => p.slot === seedValue);
    return pi?.result ?? null;
  }
  return seedValue;
}

// ---------------------------------------------------------------------------
// Round definitions — the bracket structure for one region
// ---------------------------------------------------------------------------

/** Standard NCAA bracket matchup pairings for seeds. */
const SEED_MATCHUPS: [number, number][] = [
  [1, 16], // G1
  [8, 9], // G2
  [5, 12], // G3
  [4, 13], // G4
  [6, 11], // G5
  [3, 14], // G6
  [7, 10], // G7
  [2, 15], // G8
];

// ---------------------------------------------------------------------------
// Reverse seed map — team key → seed number
// ---------------------------------------------------------------------------

/**
 * Build a map from team key → seed number for a region.
 * Uses `resolveSeed` to handle play-in references.
 */
function buildTeamSeedMap(
  region: RegionDef,
  playIns: PlayInGame[],
): Map<string, number> {
  const map = new Map<string, number>();
  for (const [seedStr, rawValue] of Object.entries(region.seeds)) {
    if (!rawValue) continue;
    const teamKey = resolveSeed(rawValue, playIns);
    if (teamKey) map.set(teamKey, Number(seedStr));
  }
  return map;
}

/**
 * Build a map from team key → seed number, resolving play-ins using the
 * user's picks first, then official results.
 */
function buildTeamSeedMapFromPicks(
  region: RegionDef,
  playIns: PlayInGame[],
  picks: Record<string, string>,
): Map<string, number> {
  const map = new Map<string, number>();
  for (const [seedStr, rawValue] of Object.entries(region.seeds)) {
    if (!rawValue) continue;
    const teamKey = resolvePickSeed(rawValue, playIns, picks);
    if (teamKey) map.set(teamKey, Number(seedStr));
  }
  return map;
}

export interface MatchupSlot {
  /** Result key in the tournament results dict, e.g. "south_R64_G1" */
  key: string;
  /** Display round name */
  round: string;
  /** The two seeds or team keys that feed this slot */
  topSeed: number | null;
  bottomSeed: number | null;
  /** Resolved team keys (null if play-in not resolved or seed empty) */
  topTeam: string | null;
  bottomTeam: string | null;
  /** Winner team key from results */
  winner: string | null;
}

export interface RegionBracket {
  regionKey: string;
  regionName: string;
  rounds: MatchupSlot[][]; // rounds[0] = R64 (8 games), rounds[1] = R32 (4), etc.
}

/**
 * Build the full bracket structure for one region.
 */
export function buildRegionBracket(
  regionKey: string,
  region: RegionDef,
  tournament: Tournament,
): RegionBracket {
  const { play_in, results } = tournament;
  const seedMap = buildTeamSeedMap(region, play_in);

  // Round of 64
  const r64: MatchupSlot[] = SEED_MATCHUPS.map(([topSeed, bottomSeed], i) => {
    const key = `${regionKey}_R64_G${i + 1}`;
    const topRaw = region.seeds[String(topSeed)] ?? null;
    const bottomRaw = region.seeds[String(bottomSeed)] ?? null;
    return {
      key,
      round: "R64",
      topSeed,
      bottomSeed,
      topTeam: resolveSeed(topRaw, play_in),
      bottomTeam: resolveSeed(bottomRaw, play_in),
      winner: results[key] ?? null,
    };
  });

  // Round of 32 — winners of adjacent R64 pairs
  const r32: MatchupSlot[] = Array.from({ length: 4 }, (_, i) => {
    const key = `${regionKey}_R32_G${i + 1}`;
    const topGame = r64[i * 2];
    const bottomGame = r64[i * 2 + 1];
    const topTeam = topGame.winner;
    const bottomTeam = bottomGame.winner;
    return {
      key,
      round: "R32",
      topSeed: topTeam ? (seedMap.get(topTeam) ?? null) : null,
      bottomSeed: bottomTeam ? (seedMap.get(bottomTeam) ?? null) : null,
      topTeam,
      bottomTeam,
      winner: results[key] ?? null,
    };
  });

  // Sweet 16
  const s16: MatchupSlot[] = Array.from({ length: 2 }, (_, i) => {
    const key = `${regionKey}_S16_G${i + 1}`;
    const topGame = r32[i * 2];
    const bottomGame = r32[i * 2 + 1];
    const topTeam = topGame.winner;
    const bottomTeam = bottomGame.winner;
    return {
      key,
      round: "S16",
      topSeed: topTeam ? (seedMap.get(topTeam) ?? null) : null,
      bottomSeed: bottomTeam ? (seedMap.get(bottomTeam) ?? null) : null,
      topTeam,
      bottomTeam,
      winner: results[key] ?? null,
    };
  });

  // Elite 8
  const e8Key = `${regionKey}_E8`;
  const e8Top = s16[0]?.winner ?? null;
  const e8Bottom = s16[1]?.winner ?? null;
  const e8: MatchupSlot[] = [
    {
      key: e8Key,
      round: "E8",
      topSeed: e8Top ? (seedMap.get(e8Top) ?? null) : null,
      bottomSeed: e8Bottom ? (seedMap.get(e8Bottom) ?? null) : null,
      topTeam: e8Top,
      bottomTeam: e8Bottom,
      winner: results[e8Key] ?? null,
    },
  ];

  return {
    regionKey,
    regionName: region.name,
    rounds: [r64, r32, s16, e8],
  };
}

// ---------------------------------------------------------------------------
// Final Four + Championship
// ---------------------------------------------------------------------------

export interface FinalFourBracket {
  semifinal1: MatchupSlot;
  semifinal2: MatchupSlot;
  championship: MatchupSlot;
}

export function buildFinalFour(tournament: Tournament): FinalFourBracket {
  const { final_four, results, regions, play_in } = tournament;
  const [sf1r1, sf1r2] = final_four.semifinal_1;
  const [sf2r1, sf2r2] = final_four.semifinal_2;

  // Build a combined team→seed map from all regions
  const allSeeds = new Map<string, number>();
  for (const region of Object.values(regions)) {
    for (const [k, v] of buildTeamSeedMap(region, play_in)) allSeeds.set(k, v);
  }

  const sf1Top = results[`${sf1r1}_E8`] ?? null;
  const sf1Bottom = results[`${sf1r2}_E8`] ?? null;

  const semifinal1: MatchupSlot = {
    key: "FF_G1",
    round: "FF",
    topSeed: sf1Top ? (allSeeds.get(sf1Top) ?? null) : null,
    bottomSeed: sf1Bottom ? (allSeeds.get(sf1Bottom) ?? null) : null,
    topTeam: sf1Top,
    bottomTeam: sf1Bottom,
    winner: results["FF_G1"] ?? null,
  };

  const sf2Top = results[`${sf2r1}_E8`] ?? null;
  const sf2Bottom = results[`${sf2r2}_E8`] ?? null;

  const semifinal2: MatchupSlot = {
    key: "FF_G2",
    round: "FF",
    topSeed: sf2Top ? (allSeeds.get(sf2Top) ?? null) : null,
    bottomSeed: sf2Bottom ? (allSeeds.get(sf2Bottom) ?? null) : null,
    topTeam: sf2Top,
    bottomTeam: sf2Bottom,
    winner: results["FF_G2"] ?? null,
  };

  const ncgTop = semifinal1.winner;
  const ncgBottom = semifinal2.winner;

  const championship: MatchupSlot = {
    key: "NCG",
    round: "NCG",
    topSeed: ncgTop ? (allSeeds.get(ncgTop) ?? null) : null,
    bottomSeed: ncgBottom ? (allSeeds.get(ncgBottom) ?? null) : null,
    topTeam: ncgTop,
    bottomTeam: ncgBottom,
    winner: results["NCG"] ?? null,
  };

  return { semifinal1, semifinal2, championship };
}

// ---------------------------------------------------------------------------
// Team display name helper
// ---------------------------------------------------------------------------

/** Round display labels */
export const ROUND_LABELS: Record<string, string> = {
  R64: "Round of 64",
  R32: "Round of 32",
  S16: "Sweet 16",
  E8: "Elite 8",
  FF: "Final Four",
  NCG: "Championship",
};

// ---------------------------------------------------------------------------
// Eliminated teams — teams knocked out by official results
// ---------------------------------------------------------------------------

/**
 * Compute the set of team keys that have been eliminated by official results.
 * A team is eliminated if it appeared in a resolved game and was NOT the winner.
 */
export function getEliminatedTeams(tournament: Tournament): Set<string> {
  const eliminated = new Set<string>();
  const { regions, play_in } = tournament;

  // Play-in eliminations
  for (const pi of play_in) {
    if (pi.result) {
      for (const team of pi.teams) {
        if (team !== pi.result) eliminated.add(team);
      }
    }
  }

  // Region round eliminations — build each official bracket and check
  for (const [regionKey, region] of Object.entries(regions)) {
    const bracket = buildRegionBracket(regionKey, region, tournament);
    for (const round of bracket.rounds) {
      for (const game of round) {
        if (game.winner) {
          if (game.topTeam && game.topTeam !== game.winner)
            eliminated.add(game.topTeam);
          if (game.bottomTeam && game.bottomTeam !== game.winner)
            eliminated.add(game.bottomTeam);
        }
      }
    }
  }

  // Final Four + Championship
  const ff = buildFinalFour(tournament);
  for (const game of [ff.semifinal1, ff.semifinal2, ff.championship]) {
    if (game.winner) {
      if (game.topTeam && game.topTeam !== game.winner)
        eliminated.add(game.topTeam);
      if (game.bottomTeam && game.bottomTeam !== game.winner)
        eliminated.add(game.bottomTeam);
    }
  }

  return eliminated;
}

// ---------------------------------------------------------------------------
// Pick-based bracket builders — for the "view my bracket" page
// ---------------------------------------------------------------------------

/**
 * Resolve a seed using the user's play-in pick first, then the official
 * play-in result as fallback. This ensures the bracket-view page shows
 * the user's chosen path through the bracket.
 */
function resolvePickSeed(
  seedValue: string | null,
  playIns: PlayInGame[],
  picks: Record<string, string>,
): string | null {
  if (!seedValue) return null;
  if (seedValue.startsWith("pi_")) {
    const pi = playIns.find((p) => p.slot === seedValue);
    // User's play-in pick takes priority (so we can show their wrong pick)
    return picks[seedValue] ?? pi?.result ?? null;
  }
  return seedValue;
}

/**
 * Build a region bracket where downstream teams are populated from the user's
 * picks rather than official results. `winner` on each slot is still the
 * official result (for scoring). Pass the returned bracket + picks to views.
 */
export function buildRegionBracketFromPicks(
  regionKey: string,
  region: RegionDef,
  tournament: Tournament,
  picks: Record<string, string>,
): RegionBracket {
  const { play_in, results } = tournament;
  const seedMap = buildTeamSeedMapFromPicks(region, play_in, picks);

  const r64: MatchupSlot[] = SEED_MATCHUPS.map(([topSeed, bottomSeed], i) => {
    const key = `${regionKey}_R64_G${i + 1}`;
    const topRaw = region.seeds[String(topSeed)] ?? null;
    const bottomRaw = region.seeds[String(bottomSeed)] ?? null;
    return {
      key,
      round: "R64",
      topSeed,
      bottomSeed,
      topTeam: resolvePickSeed(topRaw, play_in, picks),
      bottomTeam: resolvePickSeed(bottomRaw, play_in, picks),
      winner: results[key] ?? null,
    };
  });

  const r32: MatchupSlot[] = Array.from({ length: 4 }, (_, i) => {
    const key = `${regionKey}_R32_G${i + 1}`;
    const topTeam = picks[r64[i * 2].key] ?? null;
    const bottomTeam = picks[r64[i * 2 + 1].key] ?? null;
    return {
      key,
      round: "R32",
      topSeed: topTeam ? (seedMap.get(topTeam) ?? null) : null,
      bottomSeed: bottomTeam ? (seedMap.get(bottomTeam) ?? null) : null,
      topTeam,
      bottomTeam,
      winner: results[key] ?? null,
    };
  });

  const s16: MatchupSlot[] = Array.from({ length: 2 }, (_, i) => {
    const key = `${regionKey}_S16_G${i + 1}`;
    const topTeam = picks[r32[i * 2].key] ?? null;
    const bottomTeam = picks[r32[i * 2 + 1].key] ?? null;
    return {
      key,
      round: "S16",
      topSeed: topTeam ? (seedMap.get(topTeam) ?? null) : null,
      bottomSeed: bottomTeam ? (seedMap.get(bottomTeam) ?? null) : null,
      topTeam,
      bottomTeam,
      winner: results[key] ?? null,
    };
  });

  const e8Key = `${regionKey}_E8`;
  const e8Top = picks[s16[0]?.key] ?? null;
  const e8Bottom = picks[s16[1]?.key] ?? null;
  const e8: MatchupSlot[] = [
    {
      key: e8Key,
      round: "E8",
      topSeed: e8Top ? (seedMap.get(e8Top) ?? null) : null,
      bottomSeed: e8Bottom ? (seedMap.get(e8Bottom) ?? null) : null,
      topTeam: e8Top,
      bottomTeam: e8Bottom,
      winner: results[e8Key] ?? null,
    },
  ];

  return { regionKey, regionName: region.name, rounds: [r64, r32, s16, e8] };
}

/**
 * Build the Final Four from user picks.
 */
export function buildFinalFourFromPicks(
  tournament: Tournament,
  picks: Record<string, string>,
): FinalFourBracket {
  const { final_four, results, regions, play_in } = tournament;
  const [sf1r1, sf1r2] = final_four.semifinal_1;
  const [sf2r1, sf2r2] = final_four.semifinal_2;

  // Build a combined team→seed map from all regions (using picks for play-ins)
  const allSeeds = new Map<string, number>();
  for (const region of Object.values(regions)) {
    for (const [k, v] of buildTeamSeedMapFromPicks(region, play_in, picks))
      allSeeds.set(k, v);
  }

  const sf1Top = picks[`${sf1r1}_E8`] ?? null;
  const sf1Bottom = picks[`${sf1r2}_E8`] ?? null;

  const semifinal1: MatchupSlot = {
    key: "FF_G1",
    round: "FF",
    topSeed: sf1Top ? (allSeeds.get(sf1Top) ?? null) : null,
    bottomSeed: sf1Bottom ? (allSeeds.get(sf1Bottom) ?? null) : null,
    topTeam: sf1Top,
    bottomTeam: sf1Bottom,
    winner: results["FF_G1"] ?? null,
  };

  const sf2Top = picks[`${sf2r1}_E8`] ?? null;
  const sf2Bottom = picks[`${sf2r2}_E8`] ?? null;

  const semifinal2: MatchupSlot = {
    key: "FF_G2",
    round: "FF",
    topSeed: sf2Top ? (allSeeds.get(sf2Top) ?? null) : null,
    bottomSeed: sf2Bottom ? (allSeeds.get(sf2Bottom) ?? null) : null,
    topTeam: sf2Top,
    bottomTeam: sf2Bottom,
    winner: results["FF_G2"] ?? null,
  };

  const ncgTop = picks["FF_G1"] ?? null;
  const ncgBottom = picks["FF_G2"] ?? null;

  const championship: MatchupSlot = {
    key: "NCG",
    round: "NCG",
    topSeed: ncgTop ? (allSeeds.get(ncgTop) ?? null) : null,
    bottomSeed: ncgBottom ? (allSeeds.get(ncgBottom) ?? null) : null,
    topTeam: ncgTop,
    bottomTeam: ncgBottom,
    winner: results["NCG"] ?? null,
  };

  return { semifinal1, semifinal2, championship };
}

// ---------------------------------------------------------------------------
// Score a bracket against results
// ---------------------------------------------------------------------------

export interface BracketScore {
  correct: number;
  wrong: number;
  pending: number;
  total: number;
}

/**
 * Score a bracket's picks against official results.
 * Only counts games where the user made a pick.
 *
 * If `eliminated` is provided, picks for teams that have been knocked out
 * in earlier rounds are counted as wrong even before that game has a result.
 */
export function scoreBracket(
  picks: Record<string, string>,
  results: Record<string, string>,
  eliminated?: Set<string>,
): BracketScore {
  let correct = 0;
  let wrong = 0;
  let pending = 0;

  for (const [key, pick] of Object.entries(picks)) {
    // skip play-in picks from the count
    if (key.startsWith("pi_")) continue;
    const result = results[key];
    if (result) {
      if (pick === result) correct++;
      else wrong++;
    } else if (eliminated?.has(pick)) {
      // Team was knocked out in an earlier round — pick is busted
      wrong++;
    } else {
      pending++;
    }
  }

  return { correct, wrong, pending, total: correct + wrong + pending };
}
