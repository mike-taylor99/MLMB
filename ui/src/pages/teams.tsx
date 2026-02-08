// ============================================================================
// Teams page — searchable directory of all teams
// ============================================================================

import { useState, useMemo } from 'react'
import { Link } from 'react-router'
import { useSport } from '@/context/sport'
import { useTeams } from '@/lib/hooks'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Search } from 'lucide-react'
import { TeamLogo } from '@/components/team-logo'

export function TeamsPage() {
  const { sport, label } = useSport()
  const { data, isLoading, error } = useTeams({ sport, limit: 500 })
  const [search, setSearch] = useState('')

  const teams = useMemo(() => {
    const all = data?.data ?? []
    if (!search.trim()) return all
    const q = search.toLowerCase()
    return all.filter(
      (t) =>
        t.meta.school.toLowerCase().includes(q) ||
        t.meta.name.toLowerCase().includes(q) ||
        t.meta.location.toLowerCase().includes(q) ||
        t.id.toLowerCase().includes(q) ||
        (t.meta.ncaa_key?.toLowerCase().includes(q) ?? false),
    )
  }, [data, search])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Teams</h1>
        <p className="text-muted-foreground mt-1">
          {label} programs directory
        </p>
      </div>

      {/* Search — sticky below the header so it stays visible while scrolling */}
      <div className="sticky top-14 z-20 py-3 bg-background">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search teams…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {error && (
        <Card>
          <CardContent className="py-8 text-center text-destructive">
            Failed to load teams.
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      )}

      {data && (
        <>
          <p className="text-sm text-muted-foreground">
            {teams.length} team{teams.length !== 1 && 's'}
            {search && ` matching "${search}"`}
          </p>

          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 [&>*]:min-w-0">
            {teams.map((team) => (
              <Link key={team.id} to={`/teams/${team.id}`} className="min-w-0">
                <Card className="hover:border-primary/40 transition-colors h-full overflow-hidden">
                  <CardContent className="flex items-center gap-3 py-4">
                    <TeamLogo
                      ncaaKey={team.meta.ncaa_key}
                      color={team.meta.color}
                      school={team.meta.school}
                      size={40}
                    />
                    <div className="min-w-0">
                      <p className="font-medium truncate">{team.meta.school}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        {team.meta.name} · {team.meta.location}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
