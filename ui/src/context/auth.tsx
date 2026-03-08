// ============================================================================
// AuthProvider — Azure Static Web Apps built-in auth context
//
// Calls /.auth/me to get the logged-in user's clientPrincipal.
// During local dev (Vite), /.auth/me won't exist, so unauthenticated users
// are never blocked — the login gate only activates when deployed to SWA.
// ============================================================================

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import Clarity from '@microsoft/clarity'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ClientPrincipal {
  identityProvider: string
  userId: string
  userDetails: string
  userRoles: string[]
}

interface AuthContextValue {
  /** The signed-in user, or null if not signed in. */
  user: ClientPrincipal | null
  /** True while we're still fetching /.auth/me. */
  loading: boolean
  /** Whether we're running locally (Vite dev) vs. deployed on SWA. */
  isLocal: boolean
  /** Sign-out by navigating to the SWA logout route. */
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<ClientPrincipal | null>(null)
  const [loading, setLoading] = useState(true)

  // In local dev the /.auth/me endpoint doesn't exist.
  const isLocal = import.meta.env.DEV

  useEffect(() => {
    async function fetchUser() {
      try {
        const res = await fetch('/.auth/me')
        if (res.ok) {
          const data = await res.json()
          const principal: ClientPrincipal | null =
            data.clientPrincipal ?? null
          setUser(principal)

          if (principal) {
            Clarity.identify(principal.userId, undefined, undefined, principal.userDetails)
          }
        }
      } catch {
        // Network error — almost certainly local dev; leave user null.
      } finally {
        setLoading(false)
      }
    }
    fetchUser()
  }, [])

  function logout() {
    window.location.href = '/logout'
  }

  return (
    <AuthContext.Provider value={{ user, loading, isLocal, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
