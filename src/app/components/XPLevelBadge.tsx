import React from 'react';
import { eloToLevel, eloToXP, LEVEL_THRESHOLDS, LEVEL_LABELS, LEVEL_COLORS } from '../../lib/xpUtils';

interface XPLevelBadgeProps {
  /** Backend ELO value — displayed as XP/Level */
  elo: number;
  /** Show the full progress bar with XP details. Defaults to true. */
  showProgress?: boolean;
  /** Optional extra className on the root wrapper */
  className?: string;
}

// LEVEL_LABELS and LEVEL_COLORS are imported from xpUtils — no local redefinition needed.

export const XPLevelBadge: React.FC<XPLevelBadgeProps> = ({
  elo,
  showProgress = true,
  className = '',
}) => {
  const { level, currentXP, nextLevelXP, progressPercent } = eloToLevel(elo);
  const totalXP = eloToXP(elo);
  const colors = LEVEL_COLORS[level] ?? LEVEL_COLORS[1];
  const label = LEVEL_LABELS[level] ?? 'Master';
  const isMaxLevel = nextLevelXP === null;

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      {/* Badge row */}
      <div className="flex items-center gap-4">
        {/* Level circle */}
        <div
          className="level-badge w-16 h-16 rounded-full flex flex-col items-center justify-center shrink-0 relative"
          style={{
            backgroundColor: colors.bg,
            border: `1px solid ${colors.border}`,
            boxShadow: `0 0 18px ${colors.glow}`,
          }}
        >
          <span
            className="level-font text-xs font-bold tracking-widest uppercase leading-none"
            style={{ color: colors.accent, fontFamily: "'IBM Plex Mono', monospace", opacity: 0.7 }}
          >
            LVL
          </span>
          <span
            className="level-font text-2xl font-bold leading-tight"
            style={{
              color: colors.accent,
              fontFamily: "'IBM Plex Mono', monospace",
              textShadow: `0 0 10px ${colors.glow}`,
            }}
          >
            {level}
          </span>
        </div>

        {/* XP info */}
        <div className="flex flex-col min-w-0">
          <span className="text-xs tracking-widest text-white/40 uppercase leading-none mb-1">
            Skill Level
          </span>
          <span
            className="level-font text-3xl font-bold tracking-tight leading-none"
            style={{
              color: colors.accent,
              fontFamily: "'IBM Plex Mono', monospace",
              textShadow: `0 0 10px ${colors.glow}`,
            }}
          >
            {totalXP} <span className="text-base font-medium" style={{ opacity: 0.6 }}>XP</span>
          </span>
          <span className="text-xs mt-1" style={{ color: colors.accent, opacity: 0.75 }}>
            {label}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      {showProgress && (
        <div className="flex flex-col gap-1">
          <div
            className="w-full h-1.5 rounded-full overflow-hidden"
            style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}
          >
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${progressPercent}%`,
                backgroundColor: colors.accent,
                boxShadow: `0 0 6px ${colors.glow}`,
              }}
            />
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.3)' }}>
              {isMaxLevel ? 'Max Level Reached' : `${currentXP} / ${nextLevelXP !== null ? nextLevelXP - (LEVEL_THRESHOLDS[level - 1]) : 0} XP to Level ${level + 1}`}
            </span>
            {!isMaxLevel && (
              <span className="text-[10px]" style={{ color: colors.accent, opacity: 0.6 }}>
                {progressPercent}%
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
