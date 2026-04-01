/**
 * XP and Level utility functions for LearnPathAI.
 *
 * The backend now returns XP (0–1000) and level (1–6) values directly.
 * No ELO conversion is performed here.
 */

/** XP thresholds for each level boundary. Index = level - 1. */
export const LEVEL_THRESHOLDS: number[] = [0, 150, 400, 650, 850, 1000];
// Level 1:    0 XP
// Level 2:  150 XP
// Level 3:  400 XP
// Level 4:  650 XP
// Level 5:  850 XP
// Level 6: 1000 XP (max)

export interface LevelInfo {
  /** Current level, 1–6 */
  level: number;
  /** XP accumulated within the current level band */
  currentXP: number;
  /** XP needed to reach the next level; null when at max level (6) */
  nextLevelXP: number | null;
  /** Progress percentage within the current level band, 0–100 */
  progressPercent: number;
}

/**
 * Derive level info from a raw XP value.
 * XP is clamped to the maximum of 1000.
 */
export function getLevelFromXP(xp: number): LevelInfo {
  const clampedXP = Math.min(xp, 1000);

  // Find which level band the XP falls into
  let level = 1;
  for (let i = LEVEL_THRESHOLDS.length - 1; i >= 0; i--) {
    if (clampedXP >= LEVEL_THRESHOLDS[i]) {
      level = i + 1;
      break;
    }
  }

  const isMaxLevel = level >= LEVEL_THRESHOLDS.length;

  if (isMaxLevel) {
    return {
      level: LEVEL_THRESHOLDS.length,
      currentXP: clampedXP - LEVEL_THRESHOLDS[LEVEL_THRESHOLDS.length - 1],
      nextLevelXP: null,
      progressPercent: 100,
    };
  }

  const levelStartXP = LEVEL_THRESHOLDS[level - 1];
  const levelEndXP = LEVEL_THRESHOLDS[level];
  const bandSize = levelEndXP - levelStartXP;
  const currentXP = clampedXP - levelStartXP;
  const progressPercent = bandSize > 0 ? Math.round((currentXP / bandSize) * 100) : 100;

  return {
    level,
    currentXP,
    nextLevelXP: levelEndXP,
    progressPercent,
  };
}

/**
 * Alias for getLevelFromXP — explicit named export for callers that prefer
 * the `xpToLevel` name.
 */
export function xpToLevel(xp: number): LevelInfo {
  return getLevelFromXP(xp);
}

/** Human-readable label for each level 1–6. */
export const LEVEL_LABELS: Record<number, string> = {
  1: 'Novice',
  2: 'Apprentice',
  3: 'Practitioner',
  4: 'Proficient',
  5: 'Expert',
  6: 'Master',
};

/**
 * Accent color palette for each level 1–6.
 * Matches the colors used in XPLevelBadge.
 */
export const LEVEL_COLORS: Record<number, { accent: string; glow: string; bg: string; border: string }> = {
  1: { accent: '#64748b', glow: 'rgba(100,116,139,0.25)', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.3)' },
  2: { accent: '#6366f1', glow: 'rgba(99,102,241,0.25)', bg: 'rgba(99,102,241,0.08)', border: 'rgba(99,102,241,0.3)' },
  3: { accent: '#0ea5e9', glow: 'rgba(14,165,233,0.25)', bg: 'rgba(14,165,233,0.08)', border: 'rgba(14,165,233,0.3)' },
  4: { accent: '#10b981', glow: 'rgba(16,185,129,0.25)', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.3)' },
  5: { accent: '#f59e0b', glow: 'rgba(245,158,11,0.25)', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.3)' },
  6: { accent: '#00FFB2', glow: 'rgba(0,255,178,0.35)', bg: 'rgba(0,255,178,0.08)', border: 'rgba(0,255,178,0.4)' },
};

/**
 * Derive display info for a course required_level value (integer 1–6).
 * Returns level, label, and accent color for badge rendering.
 */
export function getCourseDifficultyInfo(
  requiredLevel: number | null | undefined
): { level: number; label: string; color: string } {
  if (requiredLevel == null || isNaN(requiredLevel) || requiredLevel === 0) {
    return { level: 1, label: 'Unknown', color: '#666' };
  }
  const level = Math.min(6, Math.max(1, Math.round(requiredLevel)));
  return {
    level,
    label: LEVEL_LABELS[level] ?? 'Master',
    color: (LEVEL_COLORS[level] ?? LEVEL_COLORS[1]).accent,
  };
}
