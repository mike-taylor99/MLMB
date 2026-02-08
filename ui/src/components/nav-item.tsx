// ============================================================================
// NavLink — active-aware link for the header/bottom nav
// ============================================================================

import { NavLink as RouterNavLink, type NavLinkProps } from 'react-router'
import { cn } from '@/lib/utils'

export function NavItem({ className, ...props }: NavLinkProps) {
  return (
    <RouterNavLink
      className={({ isActive }) =>
        cn(
          'inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md transition-colors',
          isActive
            ? 'bg-accent text-accent-foreground'
            : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
          className as string,
        )
      }
      {...props}
    />
  )
}
