// ============================================================================
// TeamLogo — NCAA school logo with color background + fallback
// ============================================================================

import { useState } from 'react'
import { cn } from '@/lib/utils'

const NCAA_LOGO_URL = 'https://www.ncaa.com/sites/default/files/images/logos/schools/bgd'

interface TeamLogoProps {
  ncaaKey: string | null
  color: string | null
  school: string
  className?: string
  /** Pixel size — applies to both width and height. Default 40. */
  size?: number
}

export function TeamLogo({
  ncaaKey,
  color,
  school,
  className,
  size = 40,
}: TeamLogoProps) {
  const [imgError, setImgError] = useState(false)
  const bg = color ?? '#6b7280'

  return (
    <div
      className={cn(
        'rounded-full flex items-center justify-center shrink-0 overflow-hidden',
        className,
      )}
      style={{ backgroundColor: bg, width: size, height: size }}
    >
      {ncaaKey && !imgError ? (
        <img
          src={`${NCAA_LOGO_URL}/${ncaaKey}.svg`}
          alt={school}
          className="h-[70%] w-[70%] object-contain"
          loading="lazy"
          onError={() => setImgError(true)}
        />
      ) : (
        <span
          className="font-bold text-white select-none"
          style={{ fontSize: size * 0.4 }}
        >
          {school.charAt(0)}
        </span>
      )}
    </div>
  )
}
