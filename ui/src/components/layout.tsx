// ============================================================================
// Layout — responsive shell with header, nav, and page content
// ============================================================================

import { Outlet, Link } from 'react-router'
import { Trophy, Shield, History, Crosshair, Brackets } from 'lucide-react'
import { NavItem } from '@/components/nav-item'
import { SportSwitcher } from '@/components/sport-switcher'
import { ThemeToggle } from '@/components/theme-toggle'
import { TrophyIcon } from '@/components/trophy-icon'
import { UserMenu } from '@/components/user-menu'

const navLinks = [
  { to: '/', label: 'Home', icon: Trophy },
  { to: '/predict', label: 'Predict', icon: Crosshair },
  { to: '/brackets', label: 'Brackets', icon: Brackets },
  { to: '/teams', label: 'Teams', icon: Shield },
  { to: '/history', label: 'History', icon: History },
] as const

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col overflow-x-clip">
      {/* ── Desktop header ───────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b bg-background">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 font-bold tracking-tight">
            <TrophyIcon className="h-6 w-6 text-primary" />
            <span>MLMB</span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map(({ to, label, icon: Icon }) => (
              <NavItem key={to} to={to} end={to === '/'}>
                <Icon className="h-4 w-4" />
                {label}
              </NavItem>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <SportSwitcher />
            <ThemeToggle />
            <UserMenu />
          </div>
        </div>
      </header>

      {/* ── Page content ─────────────────────────────────────── */}
      <main className="flex-1">
        <div className="mx-auto max-w-6xl px-4 py-6">
          <Outlet />
        </div>
      </main>

      {/* Footer (hidden on mobile — bottom nav is there instead) */}
      <footer className="hidden md:block border-t py-6 text-center text-xs text-muted-foreground">
        <div className="mx-auto max-w-6xl px-4">
          Machine Learning March Bracketology &middot; Powered by ensemble ML models
        </div>
      </footer>

      {/* bottom spacer so content isn't hidden behind mobile nav */}
      <div className="h-16 md:hidden" aria-hidden />

      {/* ── Mobile bottom nav ────────────────────────────────── */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 border-t bg-background md:hidden pb-[env(safe-area-inset-bottom)]">
        <div className="flex items-center justify-around py-1">
          {navLinks.map(({ to, label, icon: Icon }) => (
            <NavItem
              key={to}
              to={to}
              end={to === '/'}
              className="flex-col gap-0.5 px-2 py-1.5 text-[10px]"
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavItem>
          ))}
        </div>
      </nav>
    </div>
  )
}
