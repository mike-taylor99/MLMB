// ============================================================================
// PredictionCard — reusable prediction result display
// ============================================================================

import { Link } from 'react-router'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TeamLogo } from '@/components/team-logo'
import type { Prediction, Team } from '@/lib/types'

/** Format an ISO date string to a short readable form, e.g. "Feb 4". */
function fmtDate(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

interface PredictionCardProps {
  prediction: Prediction
  teams: Team[]
  /** Compact mode for list views (history). Default false. */
  compact?: boolean
}

export function PredictionCard({ prediction, teams, compact = false }: PredictionCardProps) {
  const homeTeam = teams.find((t) => t.id === prediction.home_team)
  const awayTeam = teams.find((t) => t.id === prediction.away_team)
  const homeLabel = homeTeam?.meta.school ?? prediction.home_team
  const awayLabel = awayTeam?.meta.school ?? prediction.away_team
  const homePct = (prediction.home_win_probability * 100).toFixed(1)
  const awayPct = ((1 - prediction.home_win_probability) * 100).toFixed(1)
  const homeWins = prediction.home_win_probability >= 0.5

  if (compact) {
    return (
      <Card>
        <CardContent className="py-4 space-y-3">
          {/* Teams row */}
          <div className="flex items-center gap-3">
            <div className="flex-1 flex items-center gap-2 min-w-0 justify-end">
              <div className="text-right min-w-0">
                <Link to={`/teams/${prediction.home_team}`} className={`truncate text-sm hover:underline ${homeWins ? 'font-semibold' : ''}`}>
                  {homeLabel}
                </Link>
                <p className="text-[10px] text-muted-foreground">
                  {prediction.neutral ? '' : 'Home'}
                  {fmtDate(prediction.home_last_played) && (
                    <>{prediction.neutral ? '' : ' · '}thru {fmtDate(prediction.home_last_played)}</>
                  )}
                </p>
              </div>
              <Link to={`/teams/${prediction.home_team}`}>
                <TeamLogo
                  ncaaKey={homeTeam?.meta.ncaa_key ?? null}
                  color={homeTeam?.meta.color ?? null}
                  school={homeLabel}
                  size={32}
                />
              </Link>
            </div>

            <div className="text-xs font-bold text-muted-foreground shrink-0">vs</div>

            <div className="flex-1 flex items-center gap-2 min-w-0">
              <Link to={`/teams/${prediction.away_team}`}>
                <TeamLogo
                  ncaaKey={awayTeam?.meta.ncaa_key ?? null}
                  color={awayTeam?.meta.color ?? null}
                  school={awayLabel}
                  size={32}
                />
              </Link>
              <div className="min-w-0">
                <Link to={`/teams/${prediction.away_team}`} className={`truncate text-sm hover:underline ${!homeWins ? 'font-semibold' : ''}`}>
                  {awayLabel}
                </Link>
                <p className="text-[10px] text-muted-foreground">
                  {prediction.neutral ? '' : 'Away'}
                  {fmtDate(prediction.away_last_played) && (
                    <>{prediction.neutral ? '' : ' · '}thru {fmtDate(prediction.away_last_played)}</>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Probability bar */}
          <div className="flex items-center gap-2">
            <Badge variant={homeWins ? 'default' : 'secondary'} className="text-[11px] tabular-nums px-1.5 py-0">
              {homePct}%
            </Badge>
            <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-500"
                style={{ width: `${homePct}%` }}
              />
            </div>
            <Badge variant={!homeWins ? 'default' : 'secondary'} className="text-[11px] tabular-nums px-1.5 py-0">
              {awayPct}%
            </Badge>
          </div>

          {/* Meta */}
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>
              {prediction.neutral ? 'Neutral site' : 'Home/Away'} · {prediction.model} · Span {prediction.span}
            </span>
            {prediction.created_at && (
              <span>{new Date(prediction.created_at).toLocaleDateString()}</span>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  // Full-size result (predict page)
  return (
    <Card className="overflow-hidden">
      <CardContent className="py-6">
        <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-2 min-w-0">
          <div className="flex flex-col items-center space-y-2 min-w-0">
            <p className="text-sm text-muted-foreground">Home</p>
            <Link to={`/teams/${prediction.home_team}`}>
              <TeamLogo
                ncaaKey={homeTeam?.meta.ncaa_key ?? null}
                color={homeTeam?.meta.color ?? null}
                school={homeLabel}
                size={48}
              />
            </Link>
            <div className="text-center w-full px-2">
              <Link to={`/teams/${prediction.home_team}`} className="text-lg font-semibold truncate hover:underline">{homeLabel}</Link>
              <p className="text-xs text-muted-foreground h-4 truncate">
                {homeTeam && homeTeam.meta.name !== homeTeam.meta.school ? homeTeam.meta.name : '\u00A0'}
              </p>
              {fmtDate(prediction.home_last_played) && (
                <p className="text-[11px] text-muted-foreground mt-0.5">thru {fmtDate(prediction.home_last_played)}</p>
              )}
            </div>
            <Badge variant={homeWins ? 'default' : 'secondary'} className="text-lg px-3 py-1">
              {homePct}%
            </Badge>
          </div>
          <div className="text-2xl font-bold text-muted-foreground self-center">vs</div>
          <div className="flex flex-col items-center space-y-2 min-w-0">
            <p className="text-sm text-muted-foreground">Away</p>
            <Link to={`/teams/${prediction.away_team}`}>
              <TeamLogo
                ncaaKey={awayTeam?.meta.ncaa_key ?? null}
                color={awayTeam?.meta.color ?? null}
                school={awayLabel}
                size={48}
              />
            </Link>
            <div className="text-center w-full px-2">
              <Link to={`/teams/${prediction.away_team}`} className="text-lg font-semibold truncate hover:underline">{awayLabel}</Link>
              <p className="text-xs text-muted-foreground h-4 truncate">
                {awayTeam && awayTeam.meta.name !== awayTeam.meta.school ? awayTeam.meta.name : '\u00A0'}
              </p>
              {fmtDate(prediction.away_last_played) && (
                <p className="text-[11px] text-muted-foreground mt-0.5">thru {fmtDate(prediction.away_last_played)}</p>
              )}
            </div>
            <Badge variant={!homeWins ? 'default' : 'secondary'} className="text-lg px-3 py-1">
              {awayPct}%
            </Badge>
          </div>
        </div>

        {/* Win-probability bar */}
        <div className="mt-6 h-3 rounded-full bg-secondary overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${homePct}%` }}
          />
        </div>

        <p className="text-xs text-muted-foreground mt-3 text-center">
          Model: {prediction.model} · Span: {prediction.span} ·{' '}
          {prediction.neutral ? 'Neutral site' : 'Home/away'}
        </p>
      </CardContent>
    </Card>
  )
}
