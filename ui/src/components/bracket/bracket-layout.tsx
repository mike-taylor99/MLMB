// ============================================================================
// BracketFullLayout — classic NCAA bracket grid layout
//
// Positions four regions in a 2×2 grid with the Final Four in the center:
//
//   ┌────────────┬─────────┬────────────┐
//   │ TL Region  │         │  TR Region │
//   │   (→ → →)  │   F F   │  (← ← ←)  │
//   ├────────────┤  + NCG  ├────────────┤
//   │ BL Region  │         │  BR Region │
//   │   (→ → →)  │         │  (← ← ←)  │
//   └────────────┴─────────┴────────────┘
// ============================================================================

import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface BracketFullLayoutProps {
  topLeft: ReactNode
  bottomLeft: ReactNode
  topRight: ReactNode
  bottomRight: ReactNode
  center: ReactNode
  /** Content rendered above the grid (e.g. First Four) — scrolls with the bracket */
  header?: ReactNode
  className?: string
}

export function BracketFullLayout({
  topLeft,
  bottomLeft,
  topRight,
  bottomRight,
  center,
  header,
  className,
}: BracketFullLayoutProps) {
  return (
    <div
      className={cn(
        // Full-bleed: break out of any parent max-width container
        'relative left-1/2 w-[100vw] -translate-x-1/2 overflow-x-auto pb-4',
        className,
      )}
    >
      <div className="w-fit mx-auto px-8">
        <div className="bg-muted/40 rounded-2xl py-6 px-6">
          {header && <div className="mb-6">{header}</div>}
          <div className="grid grid-cols-[auto_auto_auto] grid-rows-[auto_auto] items-center gap-x-6 gap-y-8">
            {/* Row 1, Col 1 — top-left region */}
            <div className="col-start-1 row-start-1">{topLeft}</div>
            {/* Center — spans both rows */}
            <div className="col-start-2 row-start-1 row-span-2 self-center px-4">{center}</div>
            {/* Row 1, Col 3 — top-right region */}
            <div className="col-start-3 row-start-1">{topRight}</div>
            {/* Row 2, Col 1 — bottom-left region */}
            <div className="col-start-1 row-start-2">{bottomLeft}</div>
            {/* Row 2, Col 3 — bottom-right region */}
            <div className="col-start-3 row-start-2">{bottomRight}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
