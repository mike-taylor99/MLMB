// ============================================================================
// PickMatchup — an interactive matchup where the user clicks to pick a winner
//
// ML predictions: up to 6 scenarios (3 spans × 2 home/away orientations).
// Click the sparkle icon to fetch all 6, shown in a popover with a summary
// average displayed inline on each team slot.
// ============================================================================

import { cn } from "@/lib/utils";
import type { Team, Span } from "@/lib/types";
import { TeamLogo } from "@/components/team-logo";
import { Sparkles, Loader2, ChevronDown } from "lucide-react";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import { useState, useEffect, useRef } from "react";

// ---------------------------------------------------------------------------
// Prediction data for a single matchup — 6 scenarios
// ---------------------------------------------------------------------------

/** One prediction scenario */
export interface PredictionScenario {
  span: Span;
  /** true when the top team was passed as home_team in the request */
  topIsHome: boolean;
  /** The top team's estimated win probability (0–1) */
  topWinProb: number;
}

/** Full set of predictions for a matchup */
export interface MatchupPredictions {
  scenarios: PredictionScenario[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Average the top-team win probability across all loaded scenarios. */
function averageTopProb(scenarios: PredictionScenario[]): number {
  if (scenarios.length === 0) return 0.5;
  return scenarios.reduce((s, sc) => s + sc.topWinProb, 0) / scenarios.length;
}

function fmt(p: number): string {
  return `${Math.round(p * 100)}%`;
}

// ---------------------------------------------------------------------------
// PickTeam — individual team slot inside a matchup
// ---------------------------------------------------------------------------

interface PickTeamProps {
  teamKey: string | null;
  seed: number | null;
  teamMap: Map<string, Team>;
  isPicked: boolean;
  isEliminated: boolean;
  onClick: () => void;
  disabled: boolean;
  /** Average win probability from ML predictions */
  avgProb?: number;
}

function PickTeam({
  teamKey,
  seed,
  teamMap,
  isPicked,
  isEliminated,
  onClick,
  disabled,
  avgProb,
}: PickTeamProps) {
  const team = teamKey ? teamMap.get(teamKey) : null;
  const canClick = teamKey !== null && !disabled;

  return (
    <button
      type="button"
      onClick={canClick ? onClick : undefined}
      disabled={!canClick}
      className={cn(
        "flex items-center gap-1.5 px-2 py-1.5 min-w-0 w-full text-left transition-colors",
        canClick && "hover:bg-primary/15 cursor-pointer",
        isPicked && "bg-primary/10 font-semibold",
        isEliminated && "opacity-30",
        !canClick && "cursor-default",
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
          {avgProb !== undefined && (
            <span
              className={cn(
                "ml-auto text-[10px] font-medium tabular-nums shrink-0",
                avgProb >= 0.5 ? "text-primary" : "text-muted-foreground",
              )}
            >
              {fmt(avgProb)}
            </span>
          )}
          {avgProb === undefined && canClick && !isPicked && !isEliminated && (
            <span className="ml-auto text-[10px] text-primary/60 shrink-0">
              ▸
            </span>
          )}
        </>
      ) : teamKey ? (
        <>
          <div className="w-5 h-5 rounded-full bg-muted shrink-0" />
          <span className="truncate text-xs text-muted-foreground">
            {teamKey}
          </span>
        </>
      ) : (
        <span className="text-xs text-muted-foreground/50 italic">TBD</span>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// PredictionDetail — popover body showing team-centric win probabilities
// ---------------------------------------------------------------------------

/** Labels for span values (game lookback window for moving averages). */
const SPAN_LABEL: Record<number, string> = {
  3: "3-game",
  5: "5-game",
  7: "7-game",
};

function PredictionDetail({
  predictions,
  topTeam,
  bottomTeam,
  teamMap,
}: {
  predictions: MatchupPredictions;
  topTeam: string;
  bottomTeam: string;
  teamMap: Map<string, Team>;
}) {
  const [expanded, setExpanded] = useState(false);

  const topSchool = teamMap.get(topTeam)?.meta.school ?? topTeam;
  const bottomSchool = teamMap.get(bottomTeam)?.meta.school ?? bottomTeam;

  const overallAvg = averageTopProb(predictions.scenarios);
  const topPct = Math.round(overallAvg * 100);
  const bottomPct = 100 - topPct;

  const favored = overallAvg >= 0.5 ? topSchool : bottomSchool;

  // Sort scenarios for display: by span, then topIsHome first
  const sorted = [...predictions.scenarios].sort(
    (a, b) =>
      a.span - b.span ||
      (a.topIsHome === b.topIsHome ? 0 : a.topIsHome ? -1 : 1),
  );

  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-violet-600 dark:text-violet-300">
        <Sparkles className="h-3.5 w-3.5" />
        ML Prediction
      </div>

      {/* Team names */}
      <div className="flex items-center justify-between text-xs gap-1">
        <span
          className={cn(
            "font-medium truncate",
            overallAvg >= 0.5 && "text-primary",
          )}
        >
          {topSchool}
        </span>
        <span
          className={cn(
            "font-medium truncate text-right",
            overallAvg < 0.5 && "text-primary",
          )}
        >
          {bottomSchool}
        </span>
      </div>

      {/* Probability bar */}
      <div className="flex h-2 rounded-full overflow-hidden bg-muted">
        <div
          className="bg-primary transition-all"
          style={{ width: `${Math.max(topPct, 2)}%` }}
        />
      </div>

      {/* Percentages */}
      <div className="flex items-center justify-between text-xs">
        <span
          className={cn(
            "tabular-nums font-semibold",
            overallAvg >= 0.5 && "text-primary",
          )}
        >
          {topPct}%
        </span>
        <span
          className={cn(
            "tabular-nums font-semibold",
            overallAvg < 0.5 && "text-primary",
          )}
        >
          {bottomPct}%
        </span>
      </div>

      {/* Summary + expand toggle */}
      <div className="pt-1 border-t">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer py-0.5"
        >
          <span>
            {predictions.scenarios.length} model runs · favors{" "}
            <span className="font-semibold text-foreground">{favored}</span>
          </span>
          <ChevronDown
            className={cn(
              "h-3 w-3 transition-transform",
              expanded && "rotate-180",
            )}
          />
        </button>

        {/* Expanded detail rows */}
        {expanded && (
          <div className="mt-2 space-y-1">
            {sorted.map((sc, i) => {
              const pct = Math.round(sc.topWinProb * 100);
              return (
                <div
                  key={i}
                  className="flex items-center justify-between text-[11px]"
                >
                  <span className="text-muted-foreground">
                    {SPAN_LABEL[sc.span] ?? `${sc.span}-game`}
                    {" · "}
                    <span className="opacity-70">
                      {sc.topIsHome ? topSchool : bottomSchool} home
                    </span>
                  </span>
                  <span className="tabular-nums font-medium ml-2 shrink-0">
                    <span
                      className={cn(
                        sc.topWinProb >= 0.5
                          ? "text-primary"
                          : "text-muted-foreground",
                      )}
                    >
                      {pct}%
                    </span>
                    <span className="text-muted-foreground mx-0.5">–</span>
                    <span
                      className={cn(
                        sc.topWinProb < 0.5
                          ? "text-primary"
                          : "text-muted-foreground",
                      )}
                    >
                      {100 - pct}%
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PickMatchup
// ---------------------------------------------------------------------------

interface PickMatchupProps {
  gameKey: string;
  topTeam: string | null;
  bottomTeam: string | null;
  topSeed: number | null;
  bottomSeed: number | null;
  pick: string | null;
  teamMap: Map<string, Team>;
  onPick: (gameKey: string, winner: string) => void;
  disabled?: boolean;
  compact?: boolean;
  /** All 6 prediction scenarios for this matchup */
  predictions?: MatchupPredictions;
  /** Request ML predictions for this matchup */
  onRequestPredictions?: (
    gameKey: string,
    topTeam: string,
    bottomTeam: string,
  ) => void;
  /** Whether predictions are currently loading */
  predictionsLoading?: boolean;
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
  predictions,
  onRequestPredictions,
  predictionsLoading,
}: PickMatchupProps) {
  const needsPick =
    !disabled && pick === null && topTeam !== null && bottomTeam !== null;
  const bothTeams = topTeam !== null && bottomTeam !== null;

  const avgTop = predictions
    ? averageTopProb(predictions.scenarios)
    : undefined;

  // Controlled popover — auto-opens when predictions finish loading
  const [popoverOpen, setPopoverOpen] = useState(false);
  const wasLoadingRef = useRef(false);

  useEffect(() => {
    if (predictionsLoading) {
      wasLoadingRef.current = true;
    } else if (wasLoadingRef.current && predictions) {
      // Just finished loading → auto-open
      wasLoadingRef.current = false;
      setPopoverOpen(true);
    }
  }, [predictionsLoading, predictions]);

  const handleSparkleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (predictions) {
      // Already have results — toggle the popover
      setPopoverOpen((prev) => !prev);
    } else if (onRequestPredictions && !predictionsLoading) {
      // Fire the fetch; useEffect will auto-open when it finishes
      onRequestPredictions(gameKey, topTeam!, bottomTeam!);
    }
  };

  const hasResults = !!predictions;

  return (
    <div
      className={cn(
        "rounded-md border bg-card text-card-foreground shadow-xs transition-colors relative",
        compact ? "w-36" : "w-44",
        needsPick && "border-primary/50 ring-1 ring-primary/25",
      )}
    >
      {/* ML predict / view button — top-right corner */}
      {bothTeams && !disabled && onRequestPredictions && (
        <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
          <PopoverTrigger asChild>
            <button
              type="button"
              onClick={handleSparkleClick}
              disabled={predictionsLoading}
              className={cn(
                "absolute -top-2 -right-2 z-10 flex items-center justify-center w-5 h-5 rounded-full transition-colors shadow-sm cursor-pointer",
                hasResults
                  ? "bg-violet-500 text-white hover:bg-violet-600 border border-violet-400 dark:border-violet-600"
                  : "bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-300 hover:bg-violet-200 dark:hover:bg-violet-900/60 border border-violet-200 dark:border-violet-700",
              )}
              title={hasResults ? "View ML predictions" : "Get ML predictions"}
            >
              {predictionsLoading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Sparkles className="h-3 w-3" />
              )}
            </button>
          </PopoverTrigger>
          {predictions && (
            <PopoverContent side="top" className="w-56 p-3">
              <PredictionDetail
                predictions={predictions}
                topTeam={topTeam!}
                bottomTeam={bottomTeam!}
                teamMap={teamMap}
              />
            </PopoverContent>
          )}
        </Popover>
      )}

      <PickTeam
        teamKey={topTeam}
        seed={topSeed}
        teamMap={teamMap}
        isPicked={pick === topTeam && topTeam !== null}
        isEliminated={pick !== null && pick !== topTeam && topTeam !== null}
        onClick={() => topTeam && onPick(gameKey, topTeam)}
        disabled={disabled}
        avgProb={avgTop}
      />
      <div className="border-t" />
      <PickTeam
        teamKey={bottomTeam}
        seed={bottomSeed}
        teamMap={teamMap}
        isPicked={pick === bottomTeam && bottomTeam !== null}
        isEliminated={
          pick !== null && pick !== bottomTeam && bottomTeam !== null
        }
        onClick={() => bottomTeam && onPick(gameKey, bottomTeam)}
        disabled={disabled}
        avgProb={avgTop !== undefined ? 1 - avgTop : undefined}
      />
    </div>
  );
}
