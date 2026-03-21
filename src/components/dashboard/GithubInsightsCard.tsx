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

export default function GithubInsightsCard({ githubAnalysis, loading = false }: GithubInsightsCardProps) {

    const languageNames = useMemo(() => {
        return githubAnalysis?.languages
            ?.map((language) => language.skill.replace("-developer", ""))
            ?.slice(0, 5)
            ?.join(" • ") || "None detected";
    }, [githubAnalysis?.languages]);

    const repoCount = githubAnalysis?.repositories?.length ?? githubAnalysis?.repo_count;

    return (
        <div className="dark-card p-6">
            <h2 className="title-font text-xl font-semibold mb-6">GitHub Activity</h2>

            {loading ? (
                <p style={{ color: "var(--text-muted)" }}>Loading GitHub analysis...</p>
            ) : !githubAnalysis?.connected ? (
                <p style={{ color: "var(--text-muted)" }}>Connect GitHub to analyze your repositories.</p>
            ) : (githubAnalysis?.languages?.length ?? 0) === 0 ? (
                <p style={{ color: "var(--text-muted)" }}>No repository language data available yet.</p>
            ) : (
                <div className="space-y-4">
                    <div className="flex items-start justify-between gap-4">
                        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                            Repositories analyzed
                        </p>
                        <p className="text-sm font-medium text-right" style={{ color: "var(--text-primary)" }}>
                            {repoCount ?? "Unknown"}
                        </p>
                    </div>
                    <div className="flex items-start justify-between gap-4">
                        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                            Languages detected
                        </p>
                        <p className="text-sm font-medium text-right" style={{ color: "var(--text-primary)" }}>
                            {languageNames}
                        </p>
                    </div>
                    <div className="flex items-start justify-between gap-4">
                        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                            Last sync
                        </p>
                        <p className="text-sm font-medium text-right" style={{ color: "var(--text-primary)" }}>
                            {githubAnalysis?.last_sync || "Unknown"}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
