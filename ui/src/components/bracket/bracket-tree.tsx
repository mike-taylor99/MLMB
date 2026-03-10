// ============================================================================
// BracketTree — renders a bracket as a tree with connector lines
//
// The classic "spider web" bracket layout: R64 → R32 → S16 → E8
// with branch lines connecting each pair of matchups to their
// downstream game.
//
// Set `mirrored` to render right-to-left (for the right side of the bracket).
// ============================================================================

import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

// ---------------------------------------------------------------------------
// BracketPair — two feeder items + connector → downstream output
//
// Normal (left-to-right):
//   [top]  ──┐
//            ├── [output]
//   [bottom] ──┘
//
// Mirrored (right-to-left):
//            ┌── [top]
//   [output] ┤
//            └── [bottom]
// ---------------------------------------------------------------------------

interface BracketPairProps {
  top: ReactNode
  bottom: ReactNode
  output?: ReactNode
  gap?: string
  mirrored?: boolean
}

export function BracketPair({ top, bottom, output, gap = 'gap-1', mirrored = false }: BracketPairProps) {
  const feeders = (
    <div className={cn('flex flex-col', gap)}>
      {top}
      {bottom}
    </div>
  )

  if (mirrored) {
    return (
      <div className="flex gap-2 items-center">
        {output != null && <div className="self-center">{output}</div>}
        {feeders}
      </div>
    )
  }

  return (
    <div className="flex gap-2 items-center">
      {feeders}
      {output != null && <div className="self-center">{output}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// BracketTree — builds the full 4-round region tree
// ---------------------------------------------------------------------------

interface BracketTreeProps {
  /** 8 elements for Round of 64 */
  r64: ReactNode[]
  /** 4 elements for Round of 32 */
  r32: ReactNode[]
  /** 2 elements for Sweet 16 */
  s16: ReactNode[]
  /** 1 element for Elite 8 */
  e8: ReactNode
  className?: string
  /** Render right-to-left (for right-side regions) */
  mirrored?: boolean
}

export function BracketTree({ r64, r32, s16, e8, className, mirrored = false }: BracketTreeProps) {
  // Level 0: pair R64 matchups → R32 output
  const level0 = Array.from({ length: 4 }, (_, i) => (
    <BracketPair
      key={i}
      top={r64[i * 2]}
      bottom={r64[i * 2 + 1]}
      output={r32[i]}
      mirrored={mirrored}
    />
  ))

  // Level 1: pair level-0 groups → S16 output
  const level1 = Array.from({ length: 2 }, (_, i) => (
    <BracketPair
      key={i}
      top={level0[i * 2]}
      bottom={level0[i * 2 + 1]}
      output={s16[i]}
      gap="gap-3"
      mirrored={mirrored}
    />
  ))

  // Level 2: pair level-1 groups → E8 output
  return (
    <div className={cn('inline-flex', className)}>
      <BracketPair
        top={level1[0]}
        bottom={level1[1]}
        output={e8}
        gap="gap-6"
        mirrored={mirrored}
      />
    </div>
  )
}
