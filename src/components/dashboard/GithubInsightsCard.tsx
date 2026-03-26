import React, { useMemo } from "react";

interface GithubAnalysis {
  connected?: boolean;
  username?: string;
  languages?: { skill: string; weight: number; confidence: number }[];
  last_sync?: string | null;
  repo_count?: number;
  repositories?: unknown[];
}

interface GithubInsightsCardProps {
  githubAnalysis: GithubAnalysis | null;
  loading?: boolean;
}

// Maps a detected language/skill to a suggested learning focus
const LANGUAGE_TO_FOCUS: Record<string, string> = {
  javascript: "Frontend / React",
  typescript: "Frontend / React",
  html: "Frontend",
  css: "Frontend",
  vue: "Frontend",
  react: "Frontend / React",
  python: "Backend / ML",
  django: "Backend",
  flask: "Backend",
  go: "Backend / DevOps",
  rust: "Backend / Systems",
  java: "Backend / Spring",
  kotlin: "Android / Backend",
  swift: "iOS Development",
  "c++": "Systems / Algorithms",
  c: "Systems / Algorithms",
  "c#": "Backend / .NET",
  ruby: "Backend / Rails",
  php: "Backend",
  docker: "DevOps",
  kubernetes: "DevOps",
  terraform: "DevOps / Cloud",
  sql: "Databases",
  postgresql: "Databases",
  mysql: "Databases",
  mongodb: "Databases / NoSQL",
  redis: "Databases / Caching",
  graphql: "Backend / APIs",
  shell: "DevOps / Linux",
  bash: "DevOps / Linux",
};

const LANG_COLORS: Record<string, string> = {
  javascript: "#f7df1e",
  typescript: "#3178c6",
  python: "#3572a5",
  go: "#00add8",
  rust: "#dea584",
  java: "#b07219",
  kotlin: "#a97bff",
  swift: "#f05138",
  "c++": "#f34b7d",
  c: "#555555",
  "c#": "#178600",
  ruby: "#701516",
  php: "#4f5d95",
  html: "#e34c26",
  css: "#563d7c",
  shell: "#89e051",
  docker: "#2496ed",
  sql: "#e38c00",
  default: "#6366f1",
};

function getLangColor(skill: string): string {
  const key = skill.toLowerCase().replace("-developer", "").replace(/\s+/g, "");
  return LANG_COLORS[key] || LANG_COLORS.default;
}

function getSuggestedFocus(languages: { skill: string }[]): string {
  for (const lang of languages) {
    const key = lang.skill.toLowerCase().replace("-developer", "").replace(/\s+/g, "");
    if (LANGUAGE_TO_FOCUS[key]) return LANGUAGE_TO_FOCUS[key];
  }
  return "Full-Stack Development";
}

function getSignalStrength(repoCount: number, langCount: number): {
  label: string;
  color: string;
  bg: string;
  bar: number;
} {
  if (repoCount >= 20 || langCount >= 5) {
    return { label: "Strong", color: "#10b981", bg: "rgba(16,185,129,0.12)", bar: 90 };
  }
  if (repoCount >= 8 || langCount >= 3) {
    return { label: "Moderate", color: "#f59e0b", bg: "rgba(245,158,11,0.12)", bar: 55 };
  }
  return { label: "Getting Started", color: "#6366f1", bg: "rgba(99,102,241,0.12)", bar: 25 };
}

export default function GithubInsightsCard({
  githubAnalysis,
  loading = false,
}: GithubInsightsCardProps) {
  const topLanguages = useMemo(
    () =>
      (githubAnalysis?.languages || [])
        .map((l) => ({ ...l, displayName: l.skill.replace("-developer", "").replace(/\b\w/g, (c) => c.toUpperCase()) }))
        .slice(0, 5),
    [githubAnalysis?.languages]
  );

  const suggestedFocus = useMemo(
    () => getSuggestedFocus(githubAnalysis?.languages || []),
    [githubAnalysis?.languages]
  );

  const repoCount = (githubAnalysis?.repositories?.length ?? githubAnalysis?.repo_count) || 0;
  const signal = getSignalStrength(repoCount, topLanguages.length);

  return (
    <div className="dark-card p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="title-font text-xl font-semibold">Developer Profile Insights</h2>
        {githubAnalysis?.username && (
          <span
            className="text-xs font-medium px-2.5 py-1 rounded-full"
            style={{ backgroundColor: "rgba(34,197,94,0.1)", color: "#22c55e" }}
          >
            @{githubAnalysis.username}
          </span>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-5 rounded animate-pulse" style={{ backgroundColor: "var(--border)" }} />
          ))}
        </div>
      ) : !githubAnalysis?.connected ? (
        <div
          className="rounded-lg p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
          style={{ backgroundColor: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.15)" }}
        >
          <div>
            <p className="text-sm font-medium mb-1" style={{ color: "var(--text-primary)" }}>
              Unlock your Developer Profile
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Connect GitHub to get language detection, signal strength, and personalised learning focus.
            </p>
          </div>
        </div>
      ) : topLanguages.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          No language data yet. Sync your GitHub to analyse repositories.
        </p>
      ) : (
        <div className="space-y-6">

          {/* Primary Languages */}
          <div>
            <p
              className="text-[11px] font-bold tracking-widest uppercase mb-3"
              style={{ color: "var(--text-muted)" }}
            >
              Primary Languages
            </p>
            <div className="flex flex-wrap gap-2">
              {topLanguages.map((lang) => (
                <span
                  key={lang.skill}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full"
                  style={{
                    backgroundColor: `${getLangColor(lang.skill)}18`,
                    color: getLangColor(lang.skill),
                    border: `1px solid ${getLangColor(lang.skill)}30`,
                  }}
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ backgroundColor: getLangColor(lang.skill) }}
                  />
                  {lang.displayName}
                </span>
              ))}
            </div>
          </div>

          {/* Suggested Learning Focus */}
          <div>
            <p
              className="text-[11px] font-bold tracking-widest uppercase mb-2"
              style={{ color: "var(--text-muted)" }}
            >
              Suggested Learning Focus
            </p>
            <div
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold"
              style={{
                backgroundColor: "rgba(99,102,241,0.1)",
                color: "var(--accent-primary)",
                border: "1px solid rgba(99,102,241,0.2)",
              }}
            >
              <span>→</span>
              {suggestedFocus}
            </div>
            <p className="text-xs mt-1.5" style={{ color: "var(--text-muted)" }}>
              Based on your top detected language
            </p>
          </div>

          {/* Activity Signal Strength */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p
                className="text-[11px] font-bold tracking-widest uppercase"
                style={{ color: "var(--text-muted)" }}
              >
                Activity Signal
              </p>
              <span
                className="text-xs font-bold px-2.5 py-0.5 rounded-full"
                style={{ backgroundColor: signal.bg, color: signal.color }}
              >
                {signal.label}
              </span>
            </div>
            <div
              className="w-full h-[6px] rounded-full overflow-hidden"
              style={{ backgroundColor: "var(--border)" }}
            >
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${signal.bar}%`,
                  backgroundColor: signal.color,
                  boxShadow: `0 0 8px ${signal.color}60`,
                }}
              />
            </div>
            <p className="text-xs mt-1.5" style={{ color: "var(--text-muted)" }}>
              {repoCount} repositories · {topLanguages.length} languages detected
            </p>
          </div>

        </div>
      )}
    </div>
  );
}
