// ============================================================================
// AuthButtons — shared sign-in provider buttons
//
// Used by both the login page and the RequireAuth gate so that adding a new
// provider (e.g. Apple) only requires changing one file.
// ============================================================================

import { Button } from '@/components/ui/button'
import { Github, User } from 'lucide-react'

const PROVIDERS = [
  {
    id: 'github',
    label: 'Continue with GitHub',
    icon: Github,
  },
  {
    id: 'aad',
    label: 'Continue with Microsoft',
    icon: User,
  },
] as const

interface AuthButtonsProps {
  /** URL to redirect to after successful sign-in. Defaults to current page. */
  redirectUrl?: string
}

export function AuthButtons({ redirectUrl }: AuthButtonsProps) {
  const redirect = encodeURIComponent(redirectUrl ?? window.location.href)

  return (
    <div className="flex flex-col gap-2 w-full">
      {PROVIDERS.map(({ id, label, icon: Icon }) => (
        <Button
          key={id}
          variant="outline"
          className="w-full justify-center gap-2"
          onClick={() => {
            window.location.href = `/.auth/login/${id}?post_login_redirect_uri=${redirect}`
          }}
        >
          <Icon className="h-5 w-5" />
          {label}
        </Button>
      ))}
    </div>
  )
}
