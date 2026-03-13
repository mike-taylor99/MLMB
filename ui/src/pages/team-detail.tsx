// ============================================================================
// Team detail page — single team info
// ============================================================================

import { Fragment } from "react";
import { useParams, Link } from "react-router";
import { useTeam } from "@/lib/hooks";
import { useSport } from "@/context/sport";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ArrowLeft, MapPin, CalendarDays } from "lucide-react";
import { TeamLogo } from "@/components/team-logo";
import type { TeamLatestStats } from "@/lib/types";

// ---------------------------------------------------------------------------
// KenPom-style stat table config
// ---------------------------------------------------------------------------

/** How to format a stat value for display. */
type Fmt = (v: number) => string;
const pct01: Fmt = (v) => `${(v * 100).toFixed(1)}%`; // 0-1 decimal → "45.2%"
const pct100: Fmt = (v) => `${v.toFixed(1)}%`; // already 0-100 → "16.7%"
const num: Fmt = (v) => v.toFixed(1); // raw number → "112.3"

interface StatRow {
  label: string;
  off: string | null;
  def: string | null;
  format: Fmt;
  /** If true, show value centered spanning both columns (e.g. Pace). */
  span?: boolean;
}

interface StatSection {
  title: string;
  rows: StatRow[];
}

const SECTIONS: StatSection[] = [
  {
    title: "Efficiency",
    rows: [
      { label: "Rating", off: "ortg", def: "drtg", format: num },
      { label: "Tempo", off: "pace", def: null, format: num, span: true },
    ],
  },
  {
    title: "Four Factors",
    rows: [
      { label: "eFG%", off: "efg_pct", def: "def_efg_pct", format: pct01 },
      {
        label: "Turnover %",
        off: "tov_pct",
        def: "def_tov_pct",
        format: pct100,
      },
      {
        label: "Off. Reb %",
        off: "orb_pct",
        def: "def_orb_pct",
        format: pct100,
      },
      { label: "FTA/FGA", off: "fta_rate", def: "def_fta_rate", format: pct01 },
    ],
  },
  {
    title: "Shooting",
    rows: [
      { label: "FG%", off: "fg_pct", def: "def_fg_pct", format: pct01 },
      { label: "3P%", off: "three_pct", def: "def_three_pct", format: pct01 },
      { label: "2P%", off: "two_pct", def: "def_two_pct", format: pct01 },
      { label: "FT%", off: "ft_pct", def: "def_ft_pct", format: pct01 },
      { label: "TS%", off: "ts_pct", def: null, format: pct01 },
    ],
  },
  {
    title: "Miscellaneous",
    rows: [
      { label: "Block %", off: "blk_pct", def: null, format: pct100 },
      { label: "Steal %", off: "stl_pct", def: null, format: pct100 },
      { label: "3PA/FGA", off: "three_pa_rate", def: null, format: pct01 },
    ],
  },
];

// ---------------------------------------------------------------------------

function LatestStatsCard({
  data,
  teamId,
  school,
}: {
  data: TeamLatestStats;
  teamId: string;
  school: string;
}) {
  const s = data.stats;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Statistical Profile</CardTitle>
        {data.last_played && (
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <CalendarDays className="h-3 w-3" />
            Stats through{" "}
            {new Date(data.last_played + "T00:00:00").toLocaleDateString(
              "en-US",
              { month: "short", day: "numeric", year: "numeric" },
            )}
          </p>
        )}
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <div className="grid grid-cols-[1fr_5rem_5rem] text-sm">
          {/* Column headers */}
          <div className="px-4 py-2 text-xs font-medium text-muted-foreground">
            Category
          </div>
          <div className="py-2 text-center text-xs font-medium text-muted-foreground">
            Offense
          </div>
          <div className="py-2 text-center text-xs font-medium text-muted-foreground">
            Defense
          </div>

          {SECTIONS.map((section) => {
            const hasData = section.rows.some(
              (r) => (r.off && s[r.off] != null) || (r.def && s[r.def] != null),
            );
            if (!hasData) return null;

            return (
              <Fragment key={section.title}>
                {/* Section header — spans all 3 columns */}
                <div className="col-span-3 bg-muted/50 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {section.title}
                </div>

                {/* Stat rows */}
                {section.rows.map((row, i) => {
                  const offVal = row.off ? s[row.off] : undefined;
                  const defVal = row.def ? s[row.def] : undefined;
                  if (offVal == null && defVal == null) return null;

                  const stripe = i % 2 === 1 ? "bg-muted/25" : "";

                  return (
                    <Fragment key={row.label}>
                      <div
                        className={`px-4 py-1.5 text-muted-foreground ${stripe}`}
                      >
                        {row.label}
                      </div>
                      {row.span ? (
                        <>
                          <div
                            className={`col-span-2 py-1.5 text-center tabular-nums font-medium ${stripe}`}
                          >
                            {offVal != null ? row.format(offVal) : "—"}
                          </div>
                        </>
                      ) : (
                        <>
                          <div
                            className={`py-1.5 text-center tabular-nums font-medium ${stripe}`}
                          >
                            {offVal != null ? row.format(offVal) : "—"}
                          </div>
                          <div
                            className={`py-1.5 text-center tabular-nums font-medium ${stripe}`}
                          >
                            {defVal != null ? row.format(defVal) : "—"}
                          </div>
                        </>
                      )}
                    </Fragment>
                  );
                })}
              </Fragment>
            );
          })}
        </div>
      </CardContent>
      <div className="px-6 py-4 border-t">
        <Button className="w-full" variant="outline" asChild>
          <Link to={`/predict?home=${teamId}`}>Predict with {school}</Link>
        </Button>
      </div>
    </Card>
  );
}

export function TeamDetailPage() {
  const { teamId } = useParams<{ teamId: string }>();
  const { sport } = useSport();
  const { data: team, isLoading, error } = useTeam(teamId ?? "");

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full rounded-lg" />
      </div>
    );
  }

  if (error || !team) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/teams">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back to teams
          </Link>
        </Button>
        <Card>
          <CardContent className="py-8 text-center text-destructive">
            {error ? "Failed to load team." : "Team not found."}
          </CardContent>
        </Card>
      </div>
    );
  }

  const sportStats = team.latest?.filter((ls) => ls.sport === sport) ?? [];

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/teams">
          <ArrowLeft className="h-4 w-4 mr-1" /> Back to teams
        </Link>
      </Button>

      <div className="flex items-center gap-4">
        <TeamLogo
          ncaaKey={team.meta.ncaa_key}
          color={team.meta.color}
          school={team.meta.school}
          size={56}
        />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {team.meta.school}
          </h1>
          <p className="text-muted-foreground">{team.meta.name}</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <span>{team.meta.location}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Sports:</span>
            {team.sports.map((s) => (
              <Badge key={s} variant="secondary">
                {s === "ncaam_basketball" ? "Men's" : "Women's"}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Stats for current sport */}
      {sportStats.map((ls) => (
        <LatestStatsCard
          key={ls.sport}
          data={ls}
          teamId={team.id}
          school={team.meta.school}
        />
      ))}
    </div>
  );
}
