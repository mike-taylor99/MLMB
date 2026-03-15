// ============================================================================
// History page — paginated prediction history
// ============================================================================

import { useSport } from '@/context/sport'
import { usePredictions, useTeams } from '@/lib/hooks'
import { useDocumentTitle } from '@/lib/use-document-title'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { History } from 'lucide-react'
import { PredictionCard } from '@/components/prediction-card'

export function HistoryPage() {
  useDocumentTitle('History')
  const { sport, label } = useSport()
  const { data, isLoading, error, fetchNextPage, hasNextPage, isFetchingNextPage } =
    usePredictions({ sport, limit: 20 })
  const { data: teamsData } = useTeams({ sport, limit: 500 })

  const teams = teamsData?.data ?? []
  const predictions = data?.pages.flatMap((p) => p.data) ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">History</h1>
        <p className="text-muted-foreground mt-1">
          Past {label} predictions
        </p>
      </div>

      {error && (
        <Card>
          <CardContent className="py-8 text-center text-destructive">
            Failed to load prediction history.
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      )}

      {data && predictions.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center space-y-2">
            <History className="h-8 w-8 mx-auto text-muted-foreground" />
            <p className="text-muted-foreground">No predictions yet.</p>
          </CardContent>
        </Card>
      )}

      {predictions.length > 0 && (
        <div className="space-y-3">
          {predictions.map((p) => (
            <PredictionCard key={p.id} prediction={p} teams={teams} compact />
          ))}

          {hasNextPage && (
            <div className="text-center pt-2">
              <Button
                variant="outline"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? 'Loading…' : 'Load more'}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
