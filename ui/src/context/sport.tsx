// ============================================================================
// SportProvider — global Men's / Women's toggle
// ============================================================================

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import type { Sport } from '@/lib/types'

interface SportContextValue {
  /** Currently active sport. */
  sport: Sport
  /** Human-readable label for the current sport. */
  label: string
  /** Toggle between men's and women's basketball. */
  toggle: () => void
  /** Set a specific sport. */
  setSport: (s: Sport) => void
}

const LABELS: Record<Sport, string> = {
  ncaam_basketball: "Men's Basketball",
  ncaaw_basketball: "Women's Basketball",
}

const SportContext = createContext<SportContextValue | null>(null)

export function SportProvider({ children }: { children: ReactNode }) {
  const [sport, setSportState] = useState<Sport>('ncaam_basketball')

  const toggle = useCallback(() => {
    setSportState((prev) =>
      prev === 'ncaam_basketball' ? 'ncaaw_basketball' : 'ncaam_basketball',
    )
  }, [])

  const setSport = useCallback((s: Sport) => {
    setSportState(s)
  }, [])

  return (
    <SportContext.Provider value={{ sport, label: LABELS[sport], toggle, setSport }}>
      {children}
    </SportContext.Provider>
  )
}

export function useSport(): SportContextValue {
  const ctx = useContext(SportContext)
  if (!ctx) throw new Error('useSport must be used within <SportProvider>')
  return ctx
}
