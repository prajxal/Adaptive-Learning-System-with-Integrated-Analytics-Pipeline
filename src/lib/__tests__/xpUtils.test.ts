import { describe, it, expect } from 'vitest';
import {
  LEVEL_THRESHOLDS,
  LEVEL_LABELS,
  eloToXP,
  getLevelFromXP,
  eloToLevel,
  getCourseDifficultyInfo,
} from '../xpUtils';

// ─── eloToXP ────────────────────────────────────────────────────────────────

describe('eloToXP', () => {
  it('maps ELO 1000 (baseline) to 0 XP', () => {
    expect(eloToXP(1000)).toBe(0);
  });

  it('maps ELO 1500 to 500 XP', () => {
    expect(eloToXP(1500)).toBe(500);
  });

  it('maps ELO 2000 to 1000 XP (max)', () => {
    expect(eloToXP(2000)).toBe(1000);
  });

  it('clamps ELO below 1000 to 0 XP', () => {
    expect(eloToXP(800)).toBe(0);
    expect(eloToXP(0)).toBe(0);
    expect(eloToXP(-500)).toBe(0);
  });

  it('clamps ELO above 2000 to 1000 XP', () => {
    expect(eloToXP(3000)).toBe(1000);
    expect(eloToXP(9999)).toBe(1000);
  });
});

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

// ─── eloToLevel ─────────────────────────────────────────────────────────────

describe('eloToLevel', () => {
  it('maps ELO 1000 to Level 1', () => {
    expect(eloToLevel(1000).level).toBe(1);
  });

  it('maps ELO 2000 to Level 6', () => {
    expect(eloToLevel(2000).level).toBe(6);
  });

  it('clamps sub-baseline ELO (800) to Level 1', () => {
    expect(eloToLevel(800).level).toBe(1);
  });

  it('maps ELO 1150 to Level 2 (XP=150, threshold boundary)', () => {
    expect(eloToLevel(1150).level).toBe(2);
  });

  it('maps ELO 1400 to Level 3', () => {
    expect(eloToLevel(1400).level).toBe(3);
  });

  it('maps ELO 1650 to Level 4', () => {
    expect(eloToLevel(1650).level).toBe(4);
  });

  it('maps ELO 1850 to Level 5', () => {
    expect(eloToLevel(1850).level).toBe(5);
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

  it('level never decreases as ELO increases (step 10)', () => {
    let prevLevel = 0;
    for (let elo = 800; elo <= 2200; elo += 10) {
      const { level } = eloToLevel(elo);
      expect(level).toBeGreaterThanOrEqual(prevLevel);
      prevLevel = level;
    }
  });

  it('XP never decreases as ELO increases (step 10)', () => {
    let prevXP = 0;
    for (let elo = 800; elo <= 2200; elo += 10) {
      const xp = eloToXP(elo);
      expect(xp).toBeGreaterThanOrEqual(prevXP);
      prevXP = xp;
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

  it('maps ELO 800 to Level 1 / Novice', () => {
    const info = getCourseDifficultyInfo(800);
    expect(info.level).toBe(1);
    expect(info.label).toBe('Novice');
  });

  it('maps ELO 1000 to Level 1 / Novice', () => {
    const info = getCourseDifficultyInfo(1000);
    expect(info.level).toBe(1);
    expect(info.label).toBe('Novice');
  });

  it('maps ELO 1150 to Level 2 / Apprentice', () => {
    const info = getCourseDifficultyInfo(1150);
    expect(info.level).toBe(2);
    expect(info.label).toBe('Apprentice');
  });

  it('maps ELO 1400 to Level 3 / Practitioner', () => {
    const info = getCourseDifficultyInfo(1400);
    expect(info.level).toBe(3);
    expect(info.label).toBe('Practitioner');
  });

  it('maps ELO 1650 to Level 4 / Proficient', () => {
    const info = getCourseDifficultyInfo(1650);
    expect(info.level).toBe(4);
    expect(info.label).toBe('Proficient');
  });

  it('maps ELO 1850 to Level 5 / Expert', () => {
    const info = getCourseDifficultyInfo(1850);
    expect(info.level).toBe(5);
    expect(info.label).toBe('Expert');
  });

  it('maps ELO 2000 to Level 6 / Master', () => {
    const info = getCourseDifficultyInfo(2000);
    expect(info.level).toBe(6);
    expect(info.label).toBe('Master');
  });

  it('returns a non-empty color string for all levels', () => {
    [800, 1150, 1400, 1650, 1850, 2000].forEach((elo) => {
      const { color } = getCourseDifficultyInfo(elo);
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
