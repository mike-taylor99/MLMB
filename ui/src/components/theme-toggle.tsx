// ============================================================================
// ThemeToggle — cycles through light → dark → system
// ============================================================================

import { useTheme } from '@/context/theme'
import { Button } from '@/components/ui/button'
import { Sun, Moon, Monitor } from 'lucide-react'

const cycle = { light: 'dark', dark: 'system', system: 'light' } as const

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-8 w-8"
      aria-label={`Theme: ${theme}`}
      onClick={() => setTheme(cycle[theme])}
    >
      {theme === 'light' && <Sun className="h-4 w-4" />}
      {theme === 'dark' && <Moon className="h-4 w-4" />}
      {theme === 'system' && <Monitor className="h-4 w-4" />}
    </Button>
  )
}
