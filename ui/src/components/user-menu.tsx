// ============================================================================
// UserMenu — avatar with dropdown for signed-in user
// ============================================================================

import { useAuth } from '@/context/auth'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { LogIn, LogOut } from 'lucide-react'

/** Return up to 2 initials from a username or email. */
function getInitials(name: string): string {
  if (name.includes('@')) {
    // Email — use first letter
    return name[0].toUpperCase()
  }
  const parts = name.split(/[\s._-]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

/** Readable label for the identity provider. */
function providerLabel(id: string): string {
  const map: Record<string, string> = {
    github: 'GitHub',
    aad: 'Microsoft',
    apple: 'Apple',
    google: 'Google',
  }
  return map[id] ?? id
}

export function UserMenu() {
  const { user, logout, isLocal } = useAuth()

  // Not signed in and not local dev — show a simple Sign In button
  if (!user && !isLocal) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className="gap-1.5"
        onClick={() => {
          window.location.href = '/login'
        }}
      >
        <LogIn className="h-4 w-4" />
        <span className="hidden sm:inline">Sign in</span>
      </Button>
    )
  }

  const displayName = user?.userDetails ?? 'Local Dev'
  const initials = user ? getInitials(user.userDetails) : 'D'
  const provider = user ? providerLabel(user.identityProvider) : null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="flex items-center gap-1.5 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="User menu"
        >
          <Avatar className="h-8 w-8 text-xs">
            <AvatarFallback className="bg-primary/15 text-primary font-medium">
              {initials}
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel className="font-normal">
          <p className="text-sm font-medium truncate">{displayName}</p>
          {provider && (
            <p className="text-xs text-muted-foreground">via {provider}</p>
          )}
          {isLocal && !user && (
            <p className="text-xs text-muted-foreground">Auth bypassed (dev)</p>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout} disabled={isLocal && !user}>
          <LogOut className="mr-2 h-4 w-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
