import React, { useMemo } from "react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { eloToXP } from "../../lib/xpUtils";

interface Skill {
  roadmap_id: string;
  trust_score?: number;
}

interface SkillRadarChartProps {
  skills: Skill[];
  loading?: boolean;
}

const formatLabel = (id: string) => {
  const words = id
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .split(" ");
  // Truncate to 2 words max so labels don't overflow the chart
  return words.slice(0, 2).join(" ");
};

const normalizeScore = (score: number): number => {
  const clamped = Math.min(Math.max(score, 800), 2000);
  return Math.round(((clamped - 800) / 1200) * 100);
};

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    // trust_score is a Backend field — displayed as XP
    const xpValue = eloToXP(payload[0]?.payload?.rawTrustScore ?? 1000);
    return (
      <div
        className="rounded-md px-3 py-2 text-xs"
        style={{
          backgroundColor: "#16161f",
          border: "1px solid #1e1e2e",
          color: "#f1f5f9",
        }}
      >
        <p className="font-semibold">{payload[0]?.payload?.subject}</p>
        <p style={{ color: "#6366f1" }}>XP: {xpValue}</p>
      </div>
    );
  }
  return null;
};

export default function SkillRadarChart({ skills, loading = false }: SkillRadarChartProps) {
  const data = useMemo(() => {
    return [...skills]
      .sort((a, b) => (b.trust_score || 800) - (a.trust_score || 800))
      .slice(0, 8)
      .map((s) => ({
        subject: formatLabel(s.roadmap_id),
        score: normalizeScore(s.trust_score || 800),
        // rawTrustScore is a Backend field — used to compute XP for the tooltip
        rawTrustScore: s.trust_score || 800,
        fullMark: 100,
      }));
  }, [skills]);

  const hasEnoughData = data.length >= 3;

  return (
    <div className="dark-card p-6 flex flex-col">
      <h2 className="title-font text-xl font-semibold mb-1">Skill Distribution</h2>
      <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
        Top roadmaps by skill level (0–100 normalized)
      </p>

      {loading ? (
        <div className="flex-1 flex items-center justify-center" style={{ minHeight: 220 }}>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading...</p>
        </div>
      ) : !hasEnoughData ? (
        <div
          className="flex-1 flex flex-col items-center justify-center text-center"
          style={{ minHeight: 220 }}
        >
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center mb-3"
            style={{ backgroundColor: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)" }}
          >
            <span className="text-2xl" style={{ color: "#6366f1" }}>◈</span>
          </div>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Start at least 3 roadmaps to see your skill distribution chart.
          </p>
        </div>
      ) : (
        <div style={{ minHeight: 220 }}>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
              <PolarGrid stroke="#1e1e2e" />
              <PolarAngleAxis
                dataKey="subject"
                tick={{
                  fill: "#64748b",
                  fontSize: 11,
                  fontFamily: "DM Sans, sans-serif",
                }}
              />
              <Radar
                name="Skill Score"
                dataKey="score"
                stroke="#6366f1"
                fill="#6366f1"
                fillOpacity={0.2}
                strokeWidth={2}
              />
              <Tooltip content={<CustomTooltip />} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
