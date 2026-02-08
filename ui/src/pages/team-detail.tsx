// ============================================================================
// Team detail page — single team info
// ============================================================================

import { useParams, Link } from 'react-router'
import { useTeam } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { ArrowLeft, MapPin } from 'lucide-react'
import { TeamLogo } from '@/components/team-logo'

export function TeamDetailPage() {
  const { teamId } = useParams<{ teamId: string }>()
  const { data: team, isLoading, error } = useTeam(teamId ?? '')

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full rounded-lg" />
      </div>
    )
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
            {error ? 'Failed to load team.' : 'Team not found.'}
          </CardContent>
        </Card>
      </div>
    )
  }

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
          <h1 className="text-3xl font-bold tracking-tight">{team.meta.school}</h1>
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
                {s === 'ncaam_basketball' ? "Men's" : "Women's"}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick predict */}
      <Card>
        <CardContent className="py-6 text-center space-y-3">
          <p className="text-muted-foreground">Want to predict a matchup?</p>
          <Button asChild>
            <Link to={`/predict?home=${team.id}`}>
              Predict with {team.meta.school}
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
