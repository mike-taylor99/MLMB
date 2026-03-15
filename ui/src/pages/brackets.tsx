// ============================================================================
// Brackets page — list available tournaments, link to bracket view
// ============================================================================

import { useMemo } from 'react'
import { Link } from 'react-router'
import { useSport } from '@/context/sport'
import { useTournaments } from '@/lib/hooks'
import { useDocumentTitle } from '@/lib/use-document-title'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { TournamentLogo } from '@/components/tournament-logo'

export function BracketsPage() {
  useDocumentTitle('Brackets')
  const { sport, label } = useSport()
  const { data, isLoading, error } = useTournaments()

  const tournaments = useMemo(
    () => data?.data.filter((t) => t.sport === sport) ?? [],
    [data, sport],
  )

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Brackets</h1>
        <p className="text-muted-foreground">
          {label} tournament brackets and results
        </p>
      </section>

      {error && (
        <Card>
          <CardContent className="py-8 text-center text-destructive">
            Failed to load tournaments.
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-xl" />
          ))}
        </div>
      )}

      {data && tournaments.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No tournaments available for {label.toLowerCase()} yet.
          </CardContent>
        </Card>
      )}

      {tournaments.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {tournaments.map((t) => (
            <Link key={t.id} to={`/brackets/${t.id}`}>
              <Card className="hover:bg-accent/50 transition-colors cursor-pointer h-full">
                <CardContent className="flex items-center gap-3 p-4">
                  <TournamentLogo tournamentId={t.id} size={40} className="shrink-0" />
                  <h3 className="font-semibold truncate">{t.name}</h3>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
