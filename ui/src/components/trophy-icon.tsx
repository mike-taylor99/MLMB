// ============================================================================
// TrophyIcon — NCAA championship trophy silhouette
// ============================================================================

interface TrophyIconProps {
  className?: string
  size?: number
}

export function TrophyIcon({ className, size = 24 }: TrophyIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 310 480"
      width={size}
      height={size}
      fill="currentColor"
      className={className}
    >
      {/* Main trophy body */}
      <polygon points="82.18,2.19 79.27,5.83 72.73,132.56 63.27,147.86 52.36,343.07 46.55,348.16 25.45,350.35 17.45,355.45 15.27,393.32 7.27,403.52 11.64,439.21 2.91,461.79 24,469.07 50.18,472.72 149.82,476.36 152.73,473.44 168.73,476.36 251.64,473.44 297.45,466.16 301.82,461.79 294.55,429.01 298.18,401.34 292.36,398.42 286.55,356.9 280,352.53 256,349.62 251.64,343.79 242.91,144.95 234.18,135.48 231.27,121.64 224.73,2.91" />

      {/* Circle emblem in the top portion */}
      <circle cx="153" cy="80" r="35" fill="var(--background, #fff)" />

      {/* Arch cutout — rounded top, flat bottom at base */}
      <path
        d="M108,350 L108,240 A45,45 0 0,1 198,240 L198,350 Z"
        fill="var(--background, #fff)"
      />

      {/* National Champion plate on the base */}
      <rect x="40" y="410" width="225" height="30" rx="4" fill="var(--background, #fff)" />
    </svg>
  )
}
