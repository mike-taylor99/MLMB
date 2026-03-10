// ============================================================================
// Tournament logo — official NCAA Final Four event logos
// ============================================================================
//
// Logos live in public/logos/{tournamentId}.png and are served as static assets.
// ============================================================================

interface TournamentLogoProps {
  tournamentId: string
  className?: string
  size?: number
}

const LABELS: Record<string, string> = {
  '2025_ncaam': "2025 Men's Final Four — San Antonio",
  '2025_ncaaw': "2025 Women's Final Four — Tampa",
  '2026_ncaam': "2026 Men's Final Four — Indianapolis",
  '2026_ncaaw': "2026 Women's Final Four — Phoenix",
}

export function TournamentLogo({
  tournamentId,
  className,
  size = 48,
}: TournamentLogoProps) {
  const label = LABELS[tournamentId]
  if (!label) return null

  return (
    <img
      src={`/logos/${tournamentId}.png`}
      alt={label}
      width={size}
      height={size}
      className={className}
      style={{ objectFit: 'contain' }}
    />
  )
}
