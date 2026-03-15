import { useState, useEffect } from "react";

/** Remaining time broken into days / hours / minutes / seconds. */
export interface CountdownValue {
  /** Total milliseconds remaining (≤ 0 means expired). */
  remaining: number;
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  /** Human-readable label, e.g. "2d 5h 12m" or "Locked". */
  label: string;
  expired: boolean;
}

/**
 * Tick-accurate countdown to an ISO date string.
 *
 * Updates every second while there's time left, then stops.
 * Returns `null` when no target is provided.
 */
export function useCountdown(
  isoDate: string | undefined,
): CountdownValue | null {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!isoDate) return;
    const target = new Date(isoDate).getTime();
    if (Date.now() >= target) return; // already expired — no timer needed
    const id = setInterval(() => {
      if (Date.now() >= target) {
        clearInterval(id);
      }
      setNow(Date.now());
    }, 1_000);
    return () => clearInterval(id);
  }, [isoDate]);

  if (!isoDate) return null;

  const target = new Date(isoDate).getTime();
  const remaining = target - now;

  if (remaining <= 0) {
    return {
      remaining: 0,
      days: 0,
      hours: 0,
      minutes: 0,
      seconds: 0,
      label: "Locked",
      expired: true,
    };
  }

  const days = Math.floor(remaining / 86_400_000);
  const hours = Math.floor((remaining % 86_400_000) / 3_600_000);
  const minutes = Math.floor((remaining % 3_600_000) / 60_000);
  const seconds = Math.floor((remaining % 60_000) / 1_000);

  const parts: string[] = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0 || days > 0) parts.push(`${hours}h`);
  parts.push(`${minutes}m`);
  if (days === 0) parts.push(`${seconds}s`);

  return {
    remaining,
    days,
    hours,
    minutes,
    seconds,
    label: parts.join(" "),
    expired: false,
  };
}
