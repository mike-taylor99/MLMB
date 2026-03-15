// ============================================================================
// Predict page — pick two teams and get a win probability
// ============================================================================

import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router";
import { useSport } from "@/context/sport";
import { useTeams, useCreatePrediction } from "@/lib/hooks";
import { useDocumentTitle } from "@/lib/use-document-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import { X, Crosshair, Info } from "lucide-react";
import type { Prediction, Span } from "@/lib/types";
import { TeamCombobox } from "@/components/team-combobox";
import { PredictionCard } from "@/components/prediction-card";

const SPANS: Span[] = [3, 5, 7];

export function PredictPage() {
  useDocumentTitle("Predict");
  const { sport, label } = useSport();
  const [searchParams] = useSearchParams();
  const { data: teamsData, isLoading: teamsLoading } = useTeams({
    sport,
    limit: 500,
  });
  const mutation = useCreatePrediction();

  const [homeTeam, setHomeTeam] = useState("");
  const [awayTeam, setAwayTeam] = useState("");
  const [span, setSpan] = useState<Span>(3);
  const [neutral, setNeutral] = useState(false);
  const [results, setResults] = useState<Prediction[]>([]);

  const newestResultRef = useRef<HTMLDivElement>(null);
  const prevResultsLen = useRef(results.length);

  // Scroll the newest prediction into view when it appears
  useEffect(() => {
    if (results.length > prevResultsLen.current && newestResultRef.current) {
      newestResultRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
    prevResultsLen.current = results.length;
  }, [results.length]);

  // Pre-fill home team from query param (e.g. /predict?home=duke)
  useEffect(() => {
    const home = searchParams.get("home");
    if (home) setHomeTeam(home);
  }, [searchParams]);

  // Clear results when sport changes
  useEffect(() => {
    setResults([]);
  }, [sport]);

  const teams = teamsData?.data ?? [];
  const isDuplicate = results.some(
    (r) =>
      r.home_team === homeTeam &&
      r.away_team === awayTeam &&
      r.span === span &&
      r.neutral === neutral,
  );
  const canSubmit =
    homeTeam &&
    awayTeam &&
    homeTeam !== awayTeam &&
    !mutation.isPending &&
    !isDuplicate;

  async function handlePredict() {
    if (!canSubmit) return;
    const prediction = await mutation.mutateAsync({
      home_team: homeTeam,
      away_team: awayTeam,
      span,
      neutral,
      sport,
    });
    setResults((prev) => [prediction, ...prev]);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Predict</h1>
        <p className="text-muted-foreground mt-1">
          Get win probabilities for {label} matchups
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Matchup</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {teamsLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium">Home Team</label>
                <TeamCombobox
                  teams={teams}
                  value={homeTeam}
                  onSelect={setHomeTeam}
                  placeholder="Select home team…"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Away Team</label>
                <TeamCombobox
                  teams={teams}
                  value={awayTeam}
                  onSelect={setAwayTeam}
                  placeholder="Select away team…"
                />
              </div>
            </div>
          )}

          {/* Options */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-1">
                <label className="text-sm font-medium">Span</label>
                <Popover>
                  <PopoverTrigger asChild>
                    <button className="text-muted-foreground hover:text-foreground transition-colors">
                      <Info className="size-3.5" />
                    </button>
                  </PopoverTrigger>
                  <PopoverContent side="top" className="text-sm w-64">
                    Number of recent games used to calculate team stats for the
                    prediction.
                  </PopoverContent>
                </Popover>
              </div>
              <div className="flex gap-1">
                {SPANS.map((s) => (
                  <Button
                    key={s}
                    variant={span === s ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSpan(s)}
                    className="w-10"
                  >
                    {s}
                  </Button>
                ))}
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Site</label>
              <div className="flex gap-1">
                <Button
                  variant={!neutral ? "default" : "outline"}
                  size="sm"
                  onClick={() => setNeutral(false)}
                >
                  Home/Away
                </Button>
                <Button
                  variant={neutral ? "default" : "outline"}
                  size="sm"
                  onClick={() => setNeutral(true)}
                >
                  Neutral
                </Button>
              </div>
            </div>
          </div>

          <Button
            onClick={handlePredict}
            disabled={!canSubmit}
            className="w-full sm:w-auto"
          >
            <Crosshair className="h-4 w-4 mr-2" />
            {mutation.isPending ? "Predicting…" : "Predict"}
          </Button>

          {mutation.isError && (
            <p className="text-sm text-destructive">{mutation.error.message}</p>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          {results.map((p, i) => (
            <div
              key={p.id ?? i}
              ref={i === 0 ? newestResultRef : undefined}
              className="relative"
            >
              <PredictionCard prediction={p} teams={teams} />
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2 h-7 w-7 rounded-full text-muted-foreground hover:text-foreground"
                onClick={() =>
                  setResults((prev) => prev.filter((_, j) => j !== i))
                }
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
