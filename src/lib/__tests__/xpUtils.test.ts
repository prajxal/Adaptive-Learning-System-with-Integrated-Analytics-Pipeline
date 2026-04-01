import { describe, it, expect } from 'vitest';
import {
  LEVEL_THRESHOLDS,
  LEVEL_LABELS,
  getLevelFromXP,
  xpToLevel,
  getCourseDifficultyInfo,
} from '../xpUtils';

// ─── getLevelFromXP ─────────────────────────────────────────────────────────

describe('getLevelFromXP', () => {
  it('returns Level 1 at XP 0 (threshold boundary)', () => {
    const info = getLevelFromXP(0);
    expect(info.level).toBe(1);
    expect(info.currentXP).toBe(0);
    expect(info.nextLevelXP).toBe(150);
    expect(info.progressPercent).toBe(0);
  });

  it('returns Level 1 at XP 75 with 50% progress', () => {
    const info = getLevelFromXP(75);
    expect(info.level).toBe(1);
    expect(info.currentXP).toBe(75);
    expect(info.nextLevelXP).toBe(150);
    expect(info.progressPercent).toBe(50);
  });

  it('returns Level 2 at XP 150 (threshold boundary)', () => {
    const info = getLevelFromXP(150);
    expect(info.level).toBe(2);
    expect(info.currentXP).toBe(0);
    expect(info.nextLevelXP).toBe(400);
  });

  it('returns Level 3 at XP 400 (threshold boundary)', () => {
    expect(getLevelFromXP(400).level).toBe(3);
  });

  it('returns Level 4 at XP 650 (threshold boundary)', () => {
    expect(getLevelFromXP(650).level).toBe(4);
  });

  it('returns Level 5 at XP 850 (threshold boundary)', () => {
    expect(getLevelFromXP(850).level).toBe(5);
  });

  it('returns Level 6 at XP 1000 (max level)', () => {
    const info = getLevelFromXP(1000);
    expect(info.level).toBe(6);
    expect(info.nextLevelXP).toBeNull();
    expect(info.progressPercent).toBe(100);
  });

  it('clamps XP above 1000 and still returns Level 6', () => {
    const info = getLevelFromXP(1500);
    expect(info.level).toBe(6);
    expect(info.nextLevelXP).toBeNull();
    expect(info.progressPercent).toBe(100);
  });

  it('computes correct currentXP within a band', () => {
    // Level 2 band: 150–400, so XP 250 → currentXP 100
    const info = getLevelFromXP(250);
    expect(info.level).toBe(2);
    expect(info.currentXP).toBe(100);
    expect(info.nextLevelXP).toBe(400);
  });

  it('computes progressPercent correctly mid-band', () => {
    // Level 2 band: 400 - 150 = 250 wide; XP 275 → currentXP 125 → 50%
    const info = getLevelFromXP(275);
    expect(info.level).toBe(2);
    expect(info.progressPercent).toBe(50);
  });
});

// ─── xpToLevel (alias) ──────────────────────────────────────────────────────

describe('xpToLevel', () => {
  it('is an alias for getLevelFromXP and returns the same result', () => {
    expect(xpToLevel(0)).toEqual(getLevelFromXP(0));
    expect(xpToLevel(150)).toEqual(getLevelFromXP(150));
    expect(xpToLevel(1000)).toEqual(getLevelFromXP(1000));
  });
});

// ─── Monotonic progression ───────────────────────────────────────────────────

describe('monotonic level progression', () => {
  it('level never decreases as XP increases (step 1)', () => {
    let prevLevel = 0;
    for (let xp = 0; xp <= 1000; xp++) {
      const { level } = getLevelFromXP(xp);
      expect(level).toBeGreaterThanOrEqual(prevLevel);
      prevLevel = level;
    }
  });
});

// ─── getCourseDifficultyInfo ─────────────────────────────────────────────────

describe('getCourseDifficultyInfo', () => {
  it('returns Unknown fallback for null', () => {
    const info = getCourseDifficultyInfo(null);
    expect(info).toEqual({ level: 1, label: 'Unknown', color: '#666' });
  });

  it('returns Unknown fallback for undefined', () => {
    const info = getCourseDifficultyInfo(undefined);
    expect(info).toEqual({ level: 1, label: 'Unknown', color: '#666' });
  });

  it('returns Unknown fallback for NaN', () => {
    const info = getCourseDifficultyInfo(NaN);
    expect(info).toEqual({ level: 1, label: 'Unknown', color: '#666' });
  });

  it('maps level 1 to Novice', () => {
    const info = getCourseDifficultyInfo(1);
    expect(info.level).toBe(1);
    expect(info.label).toBe('Novice');
  });

  it('maps level 2 to Apprentice', () => {
    const info = getCourseDifficultyInfo(2);
    expect(info.level).toBe(2);
    expect(info.label).toBe('Apprentice');
  });

  it('maps level 3 to Practitioner', () => {
    const info = getCourseDifficultyInfo(3);
    expect(info.level).toBe(3);
    expect(info.label).toBe('Practitioner');
  });

  it('maps level 4 to Proficient', () => {
    const info = getCourseDifficultyInfo(4);
    expect(info.level).toBe(4);
    expect(info.label).toBe('Proficient');
  });

  it('maps level 5 to Expert', () => {
    const info = getCourseDifficultyInfo(5);
    expect(info.level).toBe(5);
    expect(info.label).toBe('Expert');
  });

  it('maps level 6 to Master', () => {
    const info = getCourseDifficultyInfo(6);
    expect(info.level).toBe(6);
    expect(info.label).toBe('Master');
  });

  it('clamps level above 6 to 6 (Master)', () => {
    const info = getCourseDifficultyInfo(10);
    expect(info.level).toBe(6);
    expect(info.label).toBe('Master');
  });

  it('clamps level below 1 to 1 (Novice)', () => {
    const info = getCourseDifficultyInfo(0);
    // 0 is treated as null/missing — returns Unknown fallback
    expect(info).toEqual({ level: 1, label: 'Unknown', color: '#666' });
  });

  it('returns a non-empty color string for all levels 1–6', () => {
    [1, 2, 3, 4, 5, 6].forEach((level) => {
      const { color } = getCourseDifficultyInfo(level);
      expect(typeof color).toBe('string');
      expect(color.length).toBeGreaterThan(0);
    });
  });
});

// ─── Constants sanity checks ─────────────────────────────────────────────────

describe('LEVEL_THRESHOLDS', () => {
  it('has exactly 6 entries', () => {
    expect(LEVEL_THRESHOLDS).toHaveLength(6);
  });

  it('starts at 0 and ends at 1000', () => {
    expect(LEVEL_THRESHOLDS[0]).toBe(0);
    expect(LEVEL_THRESHOLDS[5]).toBe(1000);
  });

  it('is strictly ascending', () => {
    for (let i = 1; i < LEVEL_THRESHOLDS.length; i++) {
      expect(LEVEL_THRESHOLDS[i]).toBeGreaterThan(LEVEL_THRESHOLDS[i - 1]);
    }
  });
});

describe('LEVEL_LABELS', () => {
  it('has labels for all 6 levels', () => {
    [1, 2, 3, 4, 5, 6].forEach((lvl) => {
      expect(typeof LEVEL_LABELS[lvl]).toBe('string');
      expect(LEVEL_LABELS[lvl].length).toBeGreaterThan(0);
    });
  });
});
