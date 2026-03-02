// ============================================================================
// Login page — shown when the user is not authenticated
// ============================================================================

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrophyIcon } from '@/components/trophy-icon'
import { AuthButtons } from '@/components/auth-buttons'

export function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 bg-background">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <TrophyIcon className="h-7 w-7 text-primary" />
          </div>
          <CardTitle className="text-2xl">Sign in to MLMB</CardTitle>
          <p className="text-sm text-muted-foreground">
            Machine Learning March Bracketology
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <AuthButtons redirectUrl={window.location.origin + '/'} />
          <p className="text-center text-xs text-muted-foreground pt-2">
            By signing in you agree to our terms of service.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
