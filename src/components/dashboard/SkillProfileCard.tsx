import React, { useMemo } from "react";
import { Brain } from "lucide-react";

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const toPercent = (value: number) => {
    if (!Number.isFinite(value)) return 0;
    const normalized = value <= 1 ? value * 100 : value;
    return clamp(normalized, 0, 100);
};

const formatSkillName = (skillId: string) => {
    return skillId
        .replace(/[_-]+/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .replace(/\b\w/g, (char) => char.toUpperCase());
};

type SkillProfileMetric = {
    skill_id?: string;
    skill?: string;
    name?: string;
    roadmap_id?: string;
    proficiency_level?: number;
    confidence?: number;
    weight?: number;
};

const getSkillWeight = (skill: SkillProfileMetric) => {
    if (Number.isFinite(skill.weight)) {
        return toPercent(skill.weight as number);
    }
    if (Number.isFinite(skill.proficiency_level)) {
        return toPercent(skill.proficiency_level as number);
    }
    if (Number.isFinite(skill.confidence)) {
        return toPercent(skill.confidence as number);
    }
    return 0;
};

interface SkillProfileCardProps {
    skills: SkillProfileMetric[];
    loading?: boolean;
}

export default function SkillProfileCard({ skills, loading = false }: SkillProfileCardProps) {
    const safeSkills = Array.isArray(skills) ? skills : [];

    const topSkills = useMemo(() => {
        return [...safeSkills]
            .sort((a, b) => getSkillWeight(b) - getSkillWeight(a))
            .slice(0, 8);
    }, [safeSkills]);

    return (
        <div className="dark-card p-6">
            <h2 className="title-font text-xl font-semibold mb-6">AI Skill Profile</h2>

            {loading ? (
                <p style={{ color: "var(--text-muted)" }}>Loading skill profile...</p>
            ) : topSkills.length === 0 ? (
                <div className="flex items-center gap-3" style={{ color: "var(--text-muted)" }}>
                    <Brain className="w-4 h-4" />
                    <p>No skill profile available yet. Connect GitHub or upload a resume.</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {topSkills.map((skill, index) => {
                        const percentage = getSkillWeight(skill);
                        const skillName =
                            skill.skill_id ||
                            skill.skill ||
                            skill.name ||
                            skill.roadmap_id ||
                            "Unknown";
                        return (
                            <div key={`${skill.skill_id || skill.skill || skill.name || skill.roadmap_id || "unknown"}-${index}`}>
                                <div className="flex justify-between items-center mb-1.5">
                                    <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                                        {formatSkillName(skillName)}
                                    </span>
                                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                                        {Math.round(percentage)}%
                                    </span>
                                </div>
                                <div className="w-full h-[6px] rounded-full overflow-hidden" style={{ backgroundColor: "var(--border)" }}>
                                    <div
                                        className="h-full rounded-full"
                                        style={{
                                            width: `${percentage}%`,
                                            backgroundColor: "var(--accent-primary)",
                                            boxShadow: "0 0 10px rgba(99,102,241,0.35)",
                                        }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                    <p className="text-xs pt-2" style={{ color: "var(--text-muted)" }}>
                        Showing top skills from AI analysis
                    </p>
                </div>
            )}
        </div>
    );
}
