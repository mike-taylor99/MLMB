// ============================================================================
// SportSwitcher — Men's / Women's toggle in the header
// ============================================================================

import { useSport } from '@/context/sport'
import { Button } from '@/components/ui/button'
import type { Sport } from '@/lib/types'

const options: { value: Sport; short: string; long: string }[] = [
  { value: 'ncaam_basketball', short: "Men's", long: "Men's Basketball" },
  { value: 'ncaaw_basketball', short: "Women's", long: "Women's Basketball" },
]

export function SportSwitcher() {
  const { sport, setSport } = useSport()

  return (
    <div className="flex items-center rounded-lg border bg-muted p-0.5">
      {options.map((opt) => (
        <Button
          key={opt.value}
          variant={sport === opt.value ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setSport(opt.value)}
          className="h-7 px-3 text-xs font-medium"
        >
          <span className="hidden sm:inline">{opt.long}</span>
          <span className="sm:hidden">{opt.short}</span>
        </Button>
      ))}
    </div>
  )
}
