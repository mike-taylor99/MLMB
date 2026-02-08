// ============================================================================
// Home page — hero section + Top 25 rankings
// ============================================================================

import { useMemo } from 'react'
import { useSport } from '@/context/sport'
import { useRankings, useTeams } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Link } from 'react-router'
import { TeamLogo } from '@/components/team-logo'

export function HomePage() {
  const { sport } = useSport()
  const { data, isLoading, error } = useRankings(sport)
  const { data: teamsData } = useTeams({ sport, limit: 500 })

  // Build a quick lookup map: team key → team meta
  const teamMap = useMemo(() => {
    const map = new Map<string, { school: string; name: string; ncaa_key: string | null; color: string | null }>()
    for (const t of teamsData?.data ?? []) {
      map.set(t.id, { school: t.meta.school, name: t.meta.name, ncaa_key: t.meta.ncaa_key, color: t.meta.color })
    }
    return map
  }, [teamsData])

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="text-center space-y-3 py-8">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Machine Learning March Bracketology
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          NCAA basketball predictions powered by ensemble machine learning models
          trained on historical team performance data.
        </p>
      </section>

      {/* Top 25 */}
      <section>
        <h2 className="text-2xl font-semibold">Top 25</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Every AP Top 25 matchup simulated across all model and span combinations
        </p>

        {error && (
          <Card>
            <CardContent className="py-8 text-center text-destructive">
              Failed to load rankings. Is the API running?
            </CardContent>
          </Card>
        )}

        {isLoading && (
          <div className="grid gap-2">
            {Array.from({ length: 10 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full rounded-lg" />
            ))}
          </div>
        )}

        {data && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-muted-foreground font-normal">
                Updated {new Date(data.updated_at).toLocaleDateString()}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y">
                {data.rankings.map((entry) => {
                  const meta = teamMap.get(entry.team)
                  return (
                    <Link
                      key={entry.rank}
                      to={`/teams/${entry.team}`}
                      className="flex items-center gap-3 px-4 py-3 hover:bg-accent/50 transition-colors sm:px-6 sm:gap-4"
                    >
                      <Badge
                        variant={entry.rank <= 3 ? 'default' : 'secondary'}
                        className="w-8 justify-center tabular-nums"
                      >
                        {entry.rank}
                      </Badge>
                      <TeamLogo
                        ncaaKey={meta?.ncaa_key ?? null}
                        color={meta?.color ?? null}
                        school={meta?.school ?? entry.team}
                        size={32}
                      />
                      <div className="flex-1 min-w-0">
                        <span className="font-medium truncate block">
                          {meta?.school ?? entry.team}
                        </span>
                        {meta && meta.name !== meta.school && (
                          <span className="text-xs text-muted-foreground truncate block">
                            {meta.name}
                          </span>
                        )}
                      </div>
                      <span className="text-sm text-muted-foreground tabular-nums">
                        {entry.rating.toFixed(3)}
                      </span>
                    </Link>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  )
}
