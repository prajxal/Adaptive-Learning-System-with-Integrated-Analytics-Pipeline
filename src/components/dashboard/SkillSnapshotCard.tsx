import React from "react";

export default function SkillSnapshotCard({
    skills,
    githubAnalysis
}: {
    skills: any[];
    githubAnalysis: any;
}) {
    const safeSkills = Array.isArray(skills) ? skills : [];
    const sortedSkills = [...safeSkills].sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0));
    const topSkill =
        sortedSkills[0]?.skill ||
        sortedSkills[0]?.name ||
        sortedSkills[0]?.roadmap_id ||
        "Unknown";
    const skillCount = safeSkills.length;
    const githubLanguages = githubAnalysis?.languages?.length ?? 0;

    return (
        <div className="dark-card p-6">
            <h2 className="title-font text-xl font-semibold mb-6">AI Skill Snapshot</h2>

            {safeSkills.length === 0 ? (
                <p style={{ color: "var(--text-muted)" }}>No skill profile available yet.</p>
            ) : (
                <div className="grid grid-cols-3 gap-6 text-sm">
                    <div className="space-y-1">
                        <p className="text-gray-400 text-xs">Top Skill</p>
                        <p className="text-white font-medium">{topSkill}</p>
                    </div>

                    <div className="space-y-1">
                        <p className="text-gray-400 text-xs">Skills Detected</p>
                        <p className="text-white font-medium">{skillCount}</p>
                    </div>

                    <div className="space-y-1">
                        <p className="text-gray-400 text-xs">GitHub Languages</p>
                        <p className="text-white font-medium">{githubLanguages}</p>
                    </div>
                </div>
            )}
        </div>
    );
}
