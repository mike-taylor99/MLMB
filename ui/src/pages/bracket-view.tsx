// ============================================================================
// BracketView page — scored read-only view of a user's bracket picks
// ============================================================================

import { useState, useCallback, useMemo } from "react";
import { useParams, Link } from "react-router";
import { useTournament, useTeams, usePublicBracket } from "@/lib/hooks";
import {
  buildRegionBracketFromPicks,
  buildFinalFourFromPicks,
  scoreBracket,
  getEliminatedTeams,
} from "@/lib/bracket";
import {
  Matchup,
  RegionBracketView,
  FinalFourView,
  BracketFullLayout,
} from "@/components/bracket";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Check, X, Clock, Share2 } from "lucide-react";
import type { Team } from "@/lib/types";

// ---------------------------------------------------------------------------
// ShareButton — uses native Web Share API on mobile, clipboard fallback
// ---------------------------------------------------------------------------

function ShareButton({ title, text }: { title: string; text: string }) {
  const [copied, setCopied] = useState(false);

  const handleShare = useCallback(async () => {
    const url = window.location.href;

    if (navigator.share) {
      try {
        await navigator.share({ title, text, url });
        return;
      } catch {
        // User cancelled — fall through to clipboard
      }
    }

    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      prompt("Copy this link:", url);
    }
  }, [title, text]);

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleShare}
      className="shrink-0"
    >
      {copied ? (
        <>
          <Check className="h-4 w-4 mr-1.5" />
          Link Copied
        </>
      ) : (
        <>
          <Share2 className="h-4 w-4 mr-1.5" />
          Share
        </>
      )}
    </Button>
  );
}

export function BracketViewPage() {
  const { tournamentId, bracketId } = useParams<{
    tournamentId: string;
    bracketId: string;
  }>();

  const { data: tournament, isLoading: tLoading } = useTournament(
    tournamentId ?? "",
  );
  const { data: bracket, isLoading: bLoading } = usePublicBracket(
    tournamentId,
    bracketId,
  );
  const sport = tournament?.sport as
    | "ncaam_basketball"
    | "ncaaw_basketball"
    | undefined;
  const { data: teamsData } = useTeams({ sport, limit: 500, enabled: !!sport });

  // Team lookup map
  const teamMap = useMemo(() => {
    const map = new Map<string, Team>();
    for (const t of teamsData?.data ?? []) map.set(t.id, t);
    return map;
  }, [teamsData]);

  const picks = bracket?.picks ?? {};

  // Build bracket structures from picks (user's view of the bracket)
  const regionBrackets = useMemo(() => {
    if (!tournament) return [];
    return Object.entries(tournament.regions).map(([key, region]) =>
      buildRegionBracketFromPicks(key, region, tournament, picks),
    );
  }, [tournament, picks]);

  const finalFour = useMemo(() => {
    if (!tournament) return null;
    return buildFinalFourFromPicks(tournament, picks);
  }, [tournament, picks]);

  // Compute eliminated teams for busted-pick detection
  const eliminated = useMemo(() => {
    if (!tournament) return new Set<string>();
    return getEliminatedTeams(tournament);
  }, [tournament]);

  // Score the bracket
  const score = useMemo(() => {
    if (!tournament) return null;
    return scoreBracket(picks, tournament.results, eliminated);
  }, [tournament, picks, eliminated]);

  const hasResults = tournament
    ? Object.keys(tournament.results).length > 0
    : false;

  // Loading / error states
  if (tLoading || bLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (!tournament || !bracket) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-destructive">
          Bracket not found.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-3">
        <Link
          to={`/brackets/${tournamentId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Tournament
        </Link>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {bracket.name}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm text-muted-foreground">
                {tournament.name}
              </span>
              <Badge variant="outline" className="text-xs">
                {tournament.sport === "ncaam_basketball" ? "Men's" : "Women's"}
              </Badge>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ShareButton
              title={bracket.name}
              text={`Check out my bracket for ${tournament.name}`}
            />
          </div>
        </div>
      </div>

      {/* Score summary — compact pills inline with header */}
      {score && hasResults && (
        <div className="flex items-center gap-2 flex-wrap">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-green-500/15 px-3 py-1">
            <Check className="h-3.5 w-3.5 text-green-600" />
            <span className="text-sm font-semibold text-green-600">
              {score.correct}
            </span>
          </div>
          <div className="inline-flex items-center gap-1.5 rounded-full bg-destructive/15 px-3 py-1">
            <X className="h-3.5 w-3.5 text-destructive" />
            <span className="text-sm font-semibold text-destructive">
              {score.wrong}
            </span>
          </div>
          {score.pending > 0 && (
            <div className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1">
              <Clock className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-sm font-semibold text-muted-foreground">
                {score.pending}
              </span>
            </div>
          )}
          <div className="inline-flex items-center rounded-full bg-muted px-3 py-1">
            <span className="text-sm font-semibold">
              {score.total > 0
                ? `${Math.round((score.correct / (score.correct + score.wrong || 1)) * 100)}%`
                : "—"}
            </span>
          </div>
        </div>
      )}

      {/* Full bracket — 4 regions + Final Four center */}
      {tournament &&
        finalFour &&
        (() => {
          const [sf1r1, sf1r2] = tournament.final_four.semifinal_1;
          const [sf2r1, sf2r2] = tournament.final_four.semifinal_2;
          const rm = new Map(regionBrackets.map((rb) => [rb.regionKey, rb]));
          return (
            <BracketFullLayout
              topLeft={
                rm.get(sf1r1) && (
                  <RegionBracketView
                    bracket={rm.get(sf1r1)!}
                    teamMap={teamMap}
                    picks={picks}
                    eliminated={eliminated}
                  />
                )
              }
              bottomLeft={
                rm.get(sf1r2) && (
                  <RegionBracketView
                    bracket={rm.get(sf1r2)!}
                    teamMap={teamMap}
                    picks={picks}
                    eliminated={eliminated}
                  />
                )
              }
              topRight={
                rm.get(sf2r1) && (
                  <RegionBracketView
                    bracket={rm.get(sf2r1)!}
                    teamMap={teamMap}
                    picks={picks}
                    eliminated={eliminated}
                    mirrored
                  />
                )
              }
              bottomRight={
                rm.get(sf2r2) && (
                  <RegionBracketView
                    bracket={rm.get(sf2r2)!}
                    teamMap={teamMap}
                    picks={picks}
                    eliminated={eliminated}
                    mirrored
                  />
                )
              }
              center={
                <FinalFourView
                  bracket={finalFour}
                  teamMap={teamMap}
                  tournamentId={tournamentId!}
                  picks={picks}
                  eliminated={eliminated}
                />
              }
              header={
                tournament.play_in.length > 0 ? (
                  <section className="space-y-3">
                    <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide text-center">
                      First Four
                    </h3>
                    <div className="flex flex-wrap gap-4 justify-center">
                      {tournament.play_in.map((pi) => (
                        <div key={pi.slot} className="space-y-1">
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wide px-1">
                            {pi.region} · Seed {pi.seed}
                          </div>
                          <Matchup
                            topTeam={pi.teams[0] ?? null}
                            bottomTeam={pi.teams[1] ?? null}
                            topSeed={pi.seed}
                            bottomSeed={pi.seed}
                            winner={pi.result}
                            teamMap={teamMap}
                            pick={picks[pi.slot]}
                            eliminated={eliminated}
                          />
                        </div>
                      ))}
                    </div>
                  </section>
                ) : undefined
              }
            />
          );
        })()}
    </div>
  );
}
