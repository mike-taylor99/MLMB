// ============================================================================
// RequireAuth — layout route that gates child routes behind authentication
//
// Usage in App.tsx:
//   <Route element={<RequireAuth />}>
//     <Route path="predict" element={<PredictPage />} />
//   </Route>
//
// Unauthenticated users see a sign-in prompt. Authenticated users (and local
// dev) see the child route via <Outlet />.
// ============================================================================

import { Outlet, useLocation } from 'react-router'
import { useAuth } from '@/context/auth'
import { AuthButtons } from '@/components/auth-buttons'
import { Lock } from 'lucide-react'

export function RequireAuth() {
  const { user, loading, isLocal } = useAuth()
  const location = useLocation()

  // Still checking /.auth/me
  if (loading) return null

  // Authenticated or local dev — render the child route
  if (user || isLocal) return <Outlet />

  const redirectUrl = window.location.origin + location.pathname + location.search

  // Not signed in — show sign-in prompt
  return (
    <div className="flex flex-col items-center justify-center py-20 space-y-6">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
        <Lock className="h-8 w-8 text-primary" />
      </div>
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold">Sign in required</h2>
        <p className="text-muted-foreground max-w-sm">
          Sign in to access this page.
        </p>
      </div>
      <div className="w-full max-w-xs">
        <AuthButtons redirectUrl={redirectUrl} />
      </div>
    </div>
  )
}
