import React from 'react';
import { getCourseDifficultyInfo } from '../../lib/xpUtils';

interface CourseDifficultyBadgeProps {
  difficultyLevel: number | null | undefined;
  /** When true, signals the course is locked (used as fallback when userLevel is absent). */
  isLocked?: boolean;
  /**
   * The user's current XP level (1–6), derived from their ELO via eloToLevel().
   * When provided, "Requires Level N" is shown only if the user hasn't reached the
   * required level yet; otherwise the badge renders as neutral info.
   */
  userLevel?: number;
  className?: string;
}

/**
 * Compact inline badge that renders a course's difficulty_level (800–2000 ELO scale)
 * as a human-readable required-level string with a colored accent dot.
 *
 * - Not locked:                          "Level Requirement: N — Label"
 * - Locked, user level >= required:      "Level Requirement: N — Label"  (level is not the blocker)
 * - Locked, user level < required:       "Requires Level N — Label"      (level IS the blocker)
 * - Locked, userLevel not provided:      falls back to isLocked flag
 */
export const CourseDifficultyBadge: React.FC<CourseDifficultyBadgeProps> = ({
  difficultyLevel,
  isLocked = false,
  userLevel,
  className = '',
}) => {
  // Treat 0 the same as null/undefined — not a valid difficulty value
  const safeDifficulty = difficultyLevel || null;
  const { level, label, color } = getCourseDifficultyInfo(safeDifficulty);

  // Show "Requires Level" only when the level is genuinely a gating factor.
  const levelIsBlocker =
    userLevel !== undefined
      ? userLevel < level        // precise: user hasn't reached the requirement
      : isLocked;                // fallback when user level is unknown

  const prefix = levelIsBlocker ? 'Requires Level' : 'Level Requirement:';

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-sm font-medium ${className}`}
      style={{ color: 'rgba(255,255,255,0.55)' }}
    >
      <span
        style={{
          display: 'inline-block',
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: color,
          boxShadow: `0 0 4px ${color}`,
          flexShrink: 0,
        }}
      />
      <span>{prefix}</span>
      <span style={{ color }}>{level}</span>
      <span style={{ color: 'rgba(255,255,255,0.35)' }}>—</span>
      <span>{label}</span>
    </span>
  );
};
